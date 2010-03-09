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

from wader.common.middleware import WCDMAWrapper
from wader.common.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from wader.common.contact import Contact
from wader.common import consts
from wader.common.encoding import (from_ucs2, from_u,
                                   unpack_ucs2_bytes_in_ts31101_80,
                                   unpack_ucs2_bytes_in_ts31101_81,
                                   unpack_ucs2_bytes_in_ts31101_82,
                                   pack_ucs2_bytes)

from wader.common.hardware.base import WCDMACustomizer
from wader.common.plugin import DevicePlugin
from wader.common.sim import SIMBaseClass
from wader.common.utils import rssi_to_percentage
import wader.common.signals as S
import wader.common.aterrors as E

NETINFO_REGEXP = re.compile('[^a-zA-Z0-9.\-\s]*')
BADOPER_REGEXP = re.compile('FFF*')

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
}


def huawei_new_conn_mode(args):
    """Translates `args` to Wader's internal representation"""
    mode_args_dict = {
        '0,0': consts.MM_NETWORK_MODE_UNKNOWN,
        '0,2': consts.MM_NETWORK_MODE_UNKNOWN,
        '3,0': consts.MM_NETWORK_MODE_GPRS,
        '3,1': consts.MM_NETWORK_MODE_GPRS,
        '3,2': consts.MM_NETWORK_MODE_GPRS,
        '3,3': consts.MM_NETWORK_MODE_GPRS,
        '5,0': consts.MM_NETWORK_MODE_UNKNOWN,
        '5,4': consts.MM_NETWORK_MODE_UMTS,
        '5,5': consts.MM_NETWORK_MODE_HSDPA,
        '5,6': consts.MM_NETWORK_MODE_HSUPA,
        '5,7': consts.MM_NETWORK_MODE_HSPA,
        '5,9': consts.MM_NETWORK_MODE_HSPA, # doc says HSPA+
    }
    return mode_args_dict[args]

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
            ret['band'] = 0 # populated later on

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
                # bands are not combinable by firmware spec
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

        def hw_add_contact(name, number, index):
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
            cmd = ATCmd('AT^CPBW=%d,"%s",%d,"%s",%d' % args,
                        name='add_contact')
            return self.queue_at_cmd(cmd)

        name = from_u(contact.name)

        # common arguments for both operations (name and number)
        args = [name, from_u(contact.number)]

        if contact.index:
            # contact.index is set, user probably wants to overwrite an
            # existing contact
            args.append(contact.index)
            d = hw_add_contact(*args)
            d.addCallback(lambda _: contact.index)
            return d

        # contact.index is not set, this means that we need to obtain the
        # first slot free on the phonebook and then add the contact
        def get_next_id_cb(index):
            args.append(index)
            d2 = hw_add_contact(*args)
            # now we just fake add_contact's response and we return the index
            d2.addCallback(lambda _: index)
            return d2

        d = self._get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

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
        """Returns a list with all the contacts in the SIM"""
        cmd = ATCmd('AT^CPBR=1,%d' % self.device.sim.size,
                    name='list_contacts')
        d = self.queue_at_cmd(cmd)

        def not_found_eb(failure):
            failure.trap(E.NotFound, E.GenericError)
            return []

        d.addCallback(lambda matches:
                        [self._hw_process_contact_match(m) for m in matches])
        d.addErrback(not_found_eb)
        return d

    def _hw_process_contact_match(self, match):
        """
        I process a contact match and return a `Contact` object out of it
        """
        if int(match.group('raw')) == 0:
            # some buggy firmware appends this
            name = match.group('name').rstrip('\xff')
        else:
            encoding = match.group('name')[:2]
            hexbytes = match.group('name')[2:]
            if encoding == '80':   # example '80058300440586FF'
                name = unpack_ucs2_bytes_in_ts31101_80(hexbytes)
            elif encoding == '81': # example '810602A46563746F72FF'
                name = unpack_ucs2_bytes_in_ts31101_81(hexbytes)
            elif encoding == '82': # example '820505302D82D32D31'
                name = unpack_ucs2_bytes_in_ts31101_82(hexbytes)
            else:
                name = "Unsupported encoding"

        number = from_ucs2(match.group('number'))
        index = int(match.group('id'))

        return Contact(name, number, index=index)

    def get_contact(self, index):
        cmd = ATCmd('AT^CPBR=%d' % index, name='get_contact')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda match: self._hw_process_contact_match(match[0]))
        return d

    def get_network_info(self):

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

        d = super(HuaweiWCDMAWrapper, self).get_network_info()
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

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""

        def get_syscfg_cb(info):
            _mode, acqorder = info['modea'], info['modeb']
            band, roam, srv = info['theband'], info['roam'], info['srv']

            if mode in HUAWEI_CONN_DICT:
                _mode, acqorder = HUAWEI_CONN_DICT[mode]

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


class HuaweiWCDMACustomizer(WCDMACustomizer):
    """WCDMA Customizer class for Huawei cards"""
    wrapper_klass = HuaweiWCDMAWrapper
    async_regexp = re.compile('\r\n(?P<signal>\^[A-Z]{3,9}):(?P<args>.*)\r\n')
    band_dict = HUAWEI_BAND_DICT
    conn_dict = HUAWEI_CONN_DICT
    cmd_dict = HUAWEI_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE,
                           S.SIG_RSSI]

    signal_translations = {
        '^MODE': (S.SIG_NETWORK_MODE, huawei_new_conn_mode),
        '^RSSI': (S.SIG_RSSI, lambda rssi: rssi_to_percentage(int(rssi))),
        '^DSFLOWRPT': (None, None),
        '^BOOT': (None, None),
        '^SRVST': (None, None),
        '^SIMST': (None, None),
        '^CEND': (None, None),
        '^EARST': (None, None),
        '^STIN': (None, None),
        '^SMMEMFULL': (None, None),
    }


class HuaweiSIMClass(SIMBaseClass):
    """Huawei SIM Class"""

    def __init__(self, sconn):
        super(HuaweiSIMClass, self).__init__(sconn)

    def setup_sms(self):
        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(1, 1, 0, 1, 0)
        # set PDU mode
        self.sconn.set_sms_format(0)

    def initialize(self, set_encoding=True):

        def at_curc_eb(failure):
            failure.trap(E.GenericError)

        def init_cb(size):
            # enable unsolicited control commands
            d = self.sconn.send_at('AT^CURC=1')
            d.addErrback(at_curc_eb)

            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            self.sconn.send_at('AT+COPS=3,0')
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d = super(HuaweiSIMClass, self).initialize(set_encoding=set_encoding)
        d.addCallback(init_cb)
        return d


class HuaweiEMXXWrapper(HuaweiWCDMAWrapper):         # Modules have RFSWITCH
    """
    Wrapper for all Huawei embedded modules
    """

    def __init__(self, device):
        super(HuaweiEMXXWrapper, self).__init__(device)

    def get_signal_level(self):
        """
        Returns the signal level

        Overloaded to poll the RFSWITCH status

        :rtype: `Deferred`
        """

        cmd = ATCmd('AT^RFSWITCH?', name='get_radio')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda _:
                        super(HuaweiEMXXWrapper, self).get_signal_level())
        return d


class HuaweiEMXXCustomizer(HuaweiWCDMACustomizer):
    """
    Customizer for all Huawei embedded modules
    """
    adapter = HuaweiEMXXWrapper


class HuaweiWCDMADevicePlugin(DevicePlugin):
    """DevicePlugin for Huawei"""
    sim_klass = HuaweiSIMClass
    custom = HuaweiWCDMACustomizer()
