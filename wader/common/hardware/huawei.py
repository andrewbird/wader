# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Pablo Martí
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""Common stuff for all Huawei cards"""

import re

from twisted.python import log
from twisted.internet import defer

from messaging.sms import is_gsm_text
from messaging.utils import encode_str, unpack_msg

from wader.common.middleware import WCDMAWrapper
from wader.common.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from wader.common.contact import Contact
from wader.common import consts
from wader.common.encoding import (from_u, pack_ucs2_bytes,
                                   unpack_ucs2_bytes_in_ts31101_80,
                                   unpack_ucs2_bytes_in_ts31101_81,
                                   unpack_ucs2_bytes_in_ts31101_82)

from wader.common.hardware.base import WCDMACustomizer
from wader.common.plugin import DevicePlugin
from wader.common.sim import SIMBaseClass
from wader.common.utils import rssi_to_percentage
import wader.common.signals as S
import wader.common.aterrors as E

NETINFO_REGEXP = re.compile('[^a-zA-Z0-9.\-\s]*')
BADOPER_REGEXP = re.compile('FFF*')

HUAWEI_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: (2, 0),
    consts.MM_ALLOWED_MODE_2G_ONLY: (13, 1),
    consts.MM_ALLOWED_MODE_3G_ONLY: (14, 2),
    consts.MM_ALLOWED_MODE_2G_PREFERRED: (2, 1),
    consts.MM_ALLOWED_MODE_3G_PREFERRED: (2, 2),
}

HUAWEI_CONN_DICT = {
    consts.MM_NETWORK_MODE_ANY: (2, 0),
    consts.MM_NETWORK_MODE_2G_ONLY: (13, 1),
    consts.MM_NETWORK_MODE_3G_ONLY: (14, 2),
    consts.MM_NETWORK_MODE_2G_PREFERRED: (2, 1),
    consts.MM_NETWORK_MODE_3G_PREFERRED: (2, 2),
}

HUAWEI_BAND_DICT = {
    consts.MM_NETWORK_BAND_ANY: 0x3FFFFFFF,

    consts.MM_NETWORK_BAND_DCS: 0x00000080,
    consts.MM_NETWORK_BAND_EGSM: 0x00000100,
    consts.MM_NETWORK_BAND_PCS: 0x00200000,
    consts.MM_NETWORK_BAND_G850: 0x00080000,

    consts.MM_NETWORK_BAND_U2100: 0x00400000,
    consts.MM_NETWORK_BAND_U1900: 0x00800000,
    consts.MM_NETWORK_BAND_U850: 0x04000000,
# XXX: check this works with bit operations and all cards before enabling
#    consts.MM_NETWORK_BAND_U900: 0x0002000000000000,
}


# Hopefully this function will be exported from python-messaging in the future
def compress_7_to_8_bit(txt):
    txt += '\x00'
    msgl = int(len(txt) * 7 / 8)
    op = [-1] * msgl
    c = shift = 0

    for n in range(msgl):
        if shift == 6:
            c += 1

        shift = n % 7
        lb = ord(txt[c]) >> shift
        hb = (ord(txt[c + 1]) << (7 - shift) & 255)
        op[n] = lb + hb
        c += 1

    return ''.join(map(chr, op))


def huawei_new_conn_mode(args, device):
    """Translates `args` to Wader's internal representation"""
    mode_args_dict = {
        '3,0': consts.MM_NETWORK_MODE_GPRS,
        '3,1': consts.MM_NETWORK_MODE_GPRS,
        '3,2': consts.MM_NETWORK_MODE_GPRS,
        '3,3': consts.MM_NETWORK_MODE_GPRS,
        '5,4': consts.MM_NETWORK_MODE_UMTS,
        '5,5': consts.MM_NETWORK_MODE_HSDPA,
        '5,6': consts.MM_NETWORK_MODE_HSUPA,
        '5,7': consts.MM_NETWORK_MODE_HSPA,
        '5,9': consts.MM_NETWORK_MODE_HSPA,  # doc says HSPA+
    }
    try:
        return mode_args_dict[args]
    except KeyError:
        return consts.MM_NETWORK_MODE_UNKNOWN


HUAWEI_CMD_DICT = get_cmd_dict_copy()
HUAWEI_CMD_DICT['get_syscfg'] = build_cmd_dict(re.compile(r"""
                                     \r\n
                                     \^SYSCFG:
                                     (?P<modea>\d+),
                                     (?P<modeb>\d+),
                                     (?P<theband>[0-9A-F]*),
                                     (?P<roam>\d),
                                     (?P<srv>\d)
                                     \r\n
                                     """, re.VERBOSE))

HUAWEI_CMD_DICT['get_radio_status'] = build_cmd_dict(
                       end=re.compile('\r\n\+CFUN:\s?\d\r\n'),
                       extract=re.compile('\r\n\+CFUN:\s?(?P<status>\d)\r\n'))

HUAWEI_CMD_DICT['check_pin'] = build_cmd_dict(re.compile(r"""
                        \r\n
                        \+CPIN:\s*
                        (?P<resp>
                        READY      |
                        SIM\sPIN2? |
                        SIM\sPUK2?
                        )
                        \r\n
                        """, re.VERBOSE))

#+CPBR: (1-200),80,14,0,0,0
HUAWEI_CMD_DICT['get_phonebook_size'] = build_cmd_dict(re.compile(r"""
                        \r\n
                        \+CPBR:\s
                        \(\d+-(?P<size>\d+)\).*
                        \r\n
                        """, re.VERBOSE))

HUAWEI_CMD_DICT['get_contact'] = build_cmd_dict(re.compile(r"""
                       \r\n
                       \^CPBR:\s(?P<id>\d+),
                       "(?P<number>\+?\d+)",
                       (?P<cat>\d+),
                       "(?P<name>.*)",
                       (?P<raw>\d+)
                       \r\n
                       """, re.VERBOSE))

HUAWEI_CMD_DICT['list_contacts'] = build_cmd_dict(
                       end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                       extract=re.compile(r"""
                         \r\n
                         \^CPBR:\s(?P<id>\d+),
                         "(?P<number>\+?\d+)",
                         (?P<cat>\d+),
                         "(?P<name>.*)",
                         (?P<raw>\d+)
                       """, re.VERBOSE))


class HuaweiWCDMAWrapper(WCDMAWrapper):
    """Wrapper for all Huawei cards"""

    def _get_syscfg(self):

        def parse_syscfg(resp):
            ret = {}
            mode_a = int(resp[0].group('modea'))
            mode_b = int(resp[0].group('modeb'))
            band = int(resp[0].group('theband'), 16)

            # keep original values
            ret['roam'] = int(resp[0].group('roam'))
            ret['srv'] = int(resp[0].group('srv'))
            ret['modea'] = mode_a
            ret['modeb'] = mode_b
            ret['theband'] = band
            ret['band'] = 0  # populated later on

            # network mode
            if mode_a == 2 and mode_b == 1:
                ret['mode'] = consts.MM_NETWORK_MODE_2G_PREFERRED
            elif mode_a == 2 and mode_b == 2:
                ret['mode'] = consts.MM_NETWORK_MODE_3G_PREFERRED
            elif mode_a == 13:
                ret['mode'] = consts.MM_NETWORK_MODE_2G_ONLY
            elif mode_a == 14:
                ret['mode'] = consts.MM_NETWORK_MODE_3G_ONLY
            elif mode_a == 2 and mode_b == 0:
                ret['mode'] = consts.MM_NETWORK_MODE_ANY

            # band
            if band == 0x3FFFFFFF:
                ret['band'] = consts.MM_NETWORK_BAND_ANY
                # this band is not combinable by firmware spec
                return ret

            for key, value in self.custom.band_dict.items():
                if key == consts.MM_NETWORK_BAND_ANY:
                    # ANY can't be combined
                    continue

                if value & band:
                    ret['band'] |= key

            return ret

        d = self.send_at('AT^SYSCFG?', name='get_syscfg',
                         callback=parse_syscfg)
        return d

    def add_contact(self, contact):
        """
        Adds ``contact`` to the SIM and returns the index where was stored

        :rtype: int
        """
        name = from_u(contact.name)

        # common arguments for both operations (name and number)
        args = [name, from_u(contact.number)]

        if contact.index:
            # contact.index is set, user probably wants to overwrite an
            # existing contact
            args.append(contact.index)
            d = self._add_contact(*args)
            d.addCallback(lambda _: contact.index)
            return d

        # contact.index is not set, this means that we need to obtain the
        # first slot free on the phonebook and then add the contact

        def get_next_id_cb(index):
            args.append(index)
            d2 = self._add_contact(*args)
            # now we just fake add_contact's response and we return the index
            d2.addCallback(lambda _: index)
            return d2

        d = self._get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

    def _add_contact(self, name, number, index):
        """
        Adds a contact to the SIM card
        """
        raw = 0
        try:     # are all ascii chars
            name.encode('ascii')
        except:  # write in TS31.101 type 80 raw format
            name = '80%sFF' % pack_ucs2_bytes(name)
            raw = 1

        category = 145 if number.startswith('+') else 129
        args = (index, number, category, name, raw)
        cmd = ATCmd('AT^CPBW=%d,"%s",%d,"%s",%d' % args, name='add_contact')
        return self.queue_at_cmd(cmd)

    def find_contacts(self, pattern):
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                [c for c in contacts
                       if c.name.lower().startswith(pattern.lower())])
        return d

    def get_band(self):
        """Returns the current used band"""
        d = self._get_syscfg()
        d.addCallback(lambda ret: ret['band'])
        d.addErrback(log.err)
        return d

    def list_contacts(self):
        """
        Returns all the contacts in the SIM

        :rtype: list
        """

        def not_found_eb(failure):
            failure.trap(E.NotFound, E.InvalidIndex, E.General)
            return []

        def get_them(ignored=None):
            cmd = ATCmd('AT^CPBR=1,%d' % self.device.sim.size,
                        name='list_contacts')
            d = self.queue_at_cmd(cmd)
            d.addCallback(
                lambda matches: map(self._regexp_to_contact, matches))
            d.addErrback(not_found_eb)
            return d

        if self.device.sim.size:
            return get_them()
        else:
            d = self._get_next_contact_id()
            d.addCallback(get_them)
            return d

    def _regexp_to_contact(self, match):
        """
        I process a contact match and return a `Contact` object out of it
        """
        if int(match.group('raw')) == 0:
            # some buggy firmware appends this
            name = match.group('name').rstrip('\xff')
        else:
            encoding = match.group('name')[:2]
            hexbytes = match.group('name')[2:]
            if encoding != '82':
                # E220 pads  '534E4E3AFFFFFFFFFFFFFFFFFF'
                # K2540 pads '534E4E3AFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
                #            'FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'
                significant = hexbytes.find('FF')
                if significant != -1:
                    hexbytes = hexbytes[:significant + 2]

            if encoding == '80':   # example '80058300440586FF'
                name = unpack_ucs2_bytes_in_ts31101_80(hexbytes)
            elif encoding == '81':  # example '810602A46563746F72FF'
                name = unpack_ucs2_bytes_in_ts31101_81(hexbytes)
            elif encoding == '82':  # example '820505302D82D32D31'
                name = unpack_ucs2_bytes_in_ts31101_82(hexbytes)
            else:
                name = "Unsupported encoding"

        number = match.group('number')
        index = int(match.group('id'))

        return Contact(name, number, index=index)

    def get_contact(self, index):
        cmd = ATCmd('AT^CPBR=%d' % index, name='get_contact')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda match: self._regexp_to_contact(match[0]))
        return d

    def get_network_info(self, _type=None):

        # Some E220 firmwares will append an extra char to AT+COPS?
        # (off-by-one) or reply as 'FFFFFFFFFF+'. The following callback
        # will handle this errors.

        def process_netinfo_cb(info):
            operator, tech = info
            m = BADOPER_REGEXP.match(operator)
            # sometimes the operator will come as a FFFFFFF+
            if m:
                return "Unknown Network", tech

            # clean extra '@', 'x1a', etc
            return NETINFO_REGEXP.sub('', operator), tech

        d = super(HuaweiWCDMAWrapper, self).get_network_info(_type)
        d.addCallback(process_netinfo_cb)
        return d

    def get_network_mode(self):
        """Returns the current used network mode"""
        d = self._get_syscfg()
        d.addCallback(lambda ret: ret['mode'])
        d.addErrback(log.err)
        return d

    def set_band(self, band):
        """Sets the band to ``band``"""

        def get_syscfg_cb(info):
            mode_a, mode_b = info['modea'], info['modeb']
            roam, srv = info['roam'], info['srv']

            _band = 0
            if band == consts.MM_NETWORK_BAND_ANY:
                # ANY cannot be combined by design
                _band = 0x3FFFFFFF
            else:
                # the rest can be combined
                for key, value in self.custom.band_dict.items():
                    if key == consts.MM_NETWORK_BAND_ANY:
                        continue

                    if key & band:
                        _band |= value

            if _band == 0:
                raise KeyError("Unsupported band %d" % band)

            gsm_bands = (consts.MM_NETWORK_BAND_DCS |
                         consts.MM_NETWORK_BAND_PCS |
                         consts.MM_NETWORK_BAND_EGSM |
                         consts.MM_NETWORK_BAND_G850)

            umts_bands = (consts.MM_NETWORK_BAND_U800 |
                          consts.MM_NETWORK_BAND_U850 |
                          consts.MM_NETWORK_BAND_U900 |
                          consts.MM_NETWORK_BAND_U1900)

            if band & gsm_bands:
                mode_a, mode_b = 13, 1
            elif band & umts_bands:
                mode_a, mode_b = 14, 2
            else:
                # ANY and the rest
                mode_a, mode_b = 2, 0

            at_str = 'AT^SYSCFG=%d,%d,%X,%d,%d'
            return self.send_at(at_str % (mode_a, mode_b, _band, roam, srv))

        d = self._get_syscfg()
        d.addCallback(get_syscfg_cb)
        return d

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""

        def get_syscfg_cb(info):
            if mode not in self.custom.allowed_dict:
                # NOOP
                return "OK"

            _mode = self.device.get_property(consts.NET_INTFACE, "AllowedMode")
            if _mode == mode:
                # NOOP
                return "OK"

            _mode, acqorder = self.custom.allowed_dict[mode]
            band, roam, srv = info['theband'], info['roam'], info['srv']
            band = 0x3FFFFFFF
            at_str = 'AT^SYSCFG=%d,%d,%X,%d,%d'

            def set_allowed_mode_cb(ign=None):
                self.device.set_property(consts.NET_INTFACE, "AllowedMode",
                                         mode)
                return ign

            return self.send_at(at_str % (_mode, acqorder, band, roam, srv),
                                callback=set_allowed_mode_cb)

        d = self._get_syscfg()
        d.addCallback(get_syscfg_cb)
        d.addErrback(log.err)
        return d

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""

        def get_syscfg_cb(info):
            _mode, acqorder = info['modea'], info['modeb']
            band, roam, srv = info['theband'], info['roam'], info['srv']

            if mode not in self.custom.conn_dict:
                # NOOP
                return "OK"

            _mode, acqorder = self.custom.conn_dict[mode]
            band = 0x3FFFFFFF
            at_str = 'AT^SYSCFG=%d,%d,%X,%d,%d'

            return self.send_at(at_str % (_mode, acqorder, band, roam, srv))

        d = self._get_syscfg()
        d.addCallback(get_syscfg_cb)
        d.addErrback(log.err)
        return d

    def set_smsc(self, smsc):
        """
        Sets the SIM's smsc to `smsc`

        We wrap the operation with set_charset('IRA') and set_charset('UCS2')
        """
        d = self.set_charset('IRA')
        d.addCallback(lambda _: super(HuaweiWCDMAWrapper, self).set_smsc(smsc))
        d.addCallback(lambda _: self.set_charset('UCS2'))
        return d

    def _send_ussd_old_mode(self, ussd):
        """
        Sends the USSD command ``ussd`` in Huawei old mode (^USSDMODE=0)

        Sends GSM 7bit compressed text
        Receives Hex encoded or GSM 7bit compressed text
        """
        # AT+CUSD=1,"AA510C061B01",15
        # (*#100#)

        # +CUSD: 0,"3037373935353033333035",0
        # (07795503305)

        # +CUSD: 0,"C2303BEC1E97413D90140473C162A0221E9E96E741E430BD0CD452816"
        #          "2B4574CF692C162301748F876D7E7A069737A9A837A20980B04",15

        # +CUSD: 0,"D95399CD7EB340F9771D840EDBCB0AA9CD25CB81C269393DDD2E83143"
        #          "0D0B43945CD53A0B09BACA0B964305053082287E9619722FBAE83C2F2"
        #          "32E8ED0635A94E90F6ED2EBB405076393C2F83C8E9301BA48AD162AAD"
        #          "808647ECB41E4323D9C6697C92071981D768FCB739742287FD7CF683A"
        #          "88FE06E5DF7590380F6A529D2E",0

        def send_request(ussd):
            if not is_gsm_text(ussd):
                raise ValueError

            gsm = ussd.encode("gsm0338")
            ussd_enc = encode_str(compress_7_to_8_bit(gsm))

            cmd = ATCmd('AT+CUSD=1,"%s",15' % ussd_enc, name='send_ussd')
            return self.queue_at_cmd(cmd)

        def convert_response(response):
            index = response[0].group('index')
            if index == '1':
                self.device.set_property(
                                consts.USD_INTFACE, 'State', 'user-response')
            else:
                self.device.set_property(consts.USD_INTFACE, 'State', 'idle')

            resp = response[0].group('resp')
            code = response[0].group('code')

            if code is not None:
                code = int(code)

                if ((code & 0x10) == 0x10):
                    log.err("We don't yet handle ISO 639 encoded USSD"
                            " - please report")
                    raise E.MalformedUssdPduError(resp)

                if ((code & 0xf4) == 0xf4):
                    log.err("We don't yet handle 8 bit encoded USSD"
                            " - please report")
                    raise E.MalformedUssdPduError(resp)

            ret = unpack_msg(resp)
            if is_gsm_text(ret):
                return ret

            try:
                return resp.decode('hex')
            except TypeError:
                raise E.MalformedUssdPduError(resp)

        def reset_state(failure):
            if self.device.get_property(consts.USD_INTFACE, 'State') != 'idle':
                self.device.set_property(consts.USD_INTFACE, 'State', 'idle')
            failure.raiseException()  # re-raise

        self.device.set_property(consts.USD_INTFACE, 'State', 'active')

        d = send_request(str(ussd))
        d.addCallback(convert_response)
        d.addErrback(reset_state)
        return d

    def _send_ussd_ucs2_mode(self, ussd, loose_charset_check=False):
        """
        Sends the USSD command ``ussd`` in UCS2 mode regardless of the current
        setting.

        Many Huawei devices that implement Vodafone specified USSD translation
        only function correctly in the UCS2 character set, so save the current
        charset, flip to UCS2, call the ancestor, restore the charset and then
        return the result
        """

        def save_set_charset(old):
            if old == 'UCS2':
                if hasattr(self, 'old_charset'):
                    del self.old_charset
                return defer.succeed('OK')
            self.old_charset = old
            return self.set_charset('UCS2')

        def restore_charset(result):
            if hasattr(self, 'old_charset'):
                self.set_charset(self.old_charset)
                del self.old_charset
            return result

        def restore_charset_eb(failure):
            if hasattr(self, 'old_charset'):
                self.set_charset(self.old_charset)
                del self.old_charset
            failure.raiseException()  # re-raise

        d = defer.Deferred()
        d.addCallback(lambda _: self.get_charset())
        d.addCallback(save_set_charset)
        d.addErrback(restore_charset_eb)
        d.addCallback(lambda _: super(HuaweiWCDMAWrapper, self).send_ussd(ussd,
                                    loose_charset_check=loose_charset_check))
        d.addCallback(restore_charset)

        d.callback(True)
        return d


class HuaweiWCDMACustomizer(WCDMACustomizer):
    """WCDMA Customizer class for Huawei cards"""
    wrapper_klass = HuaweiWCDMAWrapper
    async_regexp = re.compile(
                        '\r\n(?P<signal>\^[A-Z]{3,9}):\s*(?P<args>.*?)\r\n')
    allowed_dict = HUAWEI_ALLOWED_DICT
    band_dict = HUAWEI_BAND_DICT
    conn_dict = HUAWEI_CONN_DICT
    cmd_dict = HUAWEI_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE,
                           S.SIG_SMS_NOTIFY_ONLINE,
                           S.SIG_RSSI]

    signal_translations = {
        '^MODE': (S.SIG_NETWORK_MODE, huawei_new_conn_mode),
        '^RSSI': (S.SIG_RSSI,
                    lambda rssi, device: rssi_to_percentage(int(rssi))),
        '^DSFLOWRPT': (None, None),
        '^BOOT': (None, None),
        '^SRVST': (None, None),
        '^SIMST': (None, None),
        '^CEND': (None, None),
        '^EARST': (None, None),
        '^STIN': (None, None),
        '^SMMEMFULL': (None, None),
        '^CSNR': (None, None),
    }


class HuaweiSIMClass(SIMBaseClass):
    """Huawei SIM Class"""

    def __init__(self, sconn):
        super(HuaweiSIMClass, self).__init__(sconn)

    def setup_sms(self):
        # Select SIM storage
        self.sconn.send_at('AT+CPMS="SM","SM","SM"')

        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(1, 1, 0, 1, 0)

        # set PDU mode
        self.sconn.set_sms_format(0)

    def initialize(self, set_encoding=True):

        def at_curc_eb(failure):
            failure.trap(E.General)

        def init_cb(size):
            # enable unsolicited control commands
            d = self.sconn.send_at('AT^CURC=1')
            d.addErrback(at_curc_eb)

            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            self.sconn.send_at('AT+COPS=3,0')
            return size

        d = super(HuaweiSIMClass, self).initialize(set_encoding=set_encoding)
        d.addCallback(init_cb)
        return d


class HuaweiWCDMADevicePlugin(DevicePlugin):
    """DevicePlugin for Huawei"""
    sim_klass = HuaweiSIMClass
    custom = HuaweiWCDMACustomizer()
