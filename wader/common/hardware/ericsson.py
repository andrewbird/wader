# -*- coding: utf-8 -*-
# Copyright (C) 2009-2011  Vodafone España, S.A.
# Author:  Andrew Bird
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
"""Common stuff for all Ericsson's cards"""

import re

from twisted.internet import defer, reactor
from twisted.python import log

import wader.common.aterrors as E
from wader.common.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from wader.common import consts
from wader.common.contact import Contact
from wader.common.encoding import (pack_ucs2_bytes, from_u, check_if_ucs2,
                                   from_ucs2, from_8bit_in_gsm_or_ts31101)
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.sim import SIMBaseClass
from wader.common.statem.simple import SimpleStateMachine
from wader.common.utils import revert_dict
from wader.contrib.modal import mode as Mode
import wader.common.signals as S
from wader.common.sim import COM_READ_BINARY, EF_AD, EF_ICCID, EF_SPN, SW_OK

MAX_RETRIES = 6
RETRY_TIMEOUT = 4

ERICSSON_BAND_DICT = {
    consts.MM_NETWORK_BAND_UNKNOWN: None,
    consts.MM_NETWORK_BAND_ANY: None,
}

ERICSSON_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: 1,
    consts.MM_ALLOWED_MODE_2G_ONLY: 5,
    consts.MM_ALLOWED_MODE_3G_ONLY: 6,
}

ERICSSON_CONN_DICT = {
    consts.MM_NETWORK_MODE_ANY: 1,
    consts.MM_NETWORK_MODE_2G_ONLY: 5,
    consts.MM_NETWORK_MODE_3G_ONLY: 6,
}

ERINFO_2G_GPRS, ERINFO_2G_EGPRS = 1, 2
ERINFO_3G_UMTS, ERINFO_3G_HSDPA = 1, 2

E2NAP_DISCONNECTED, E2NAP_CONNECTED, E2NAP_CONNECTING = 0, 1, 2

ERICSSON_CMD_DICT = get_cmd_dict_copy()

ERICSSON_CMD_DICT['get_card_model'] = build_cmd_dict('\s*(?P<model>\S*)\r\n')

# +CIND: 5,5,0,0,1,0,1,0,1,1,0,0
ERICSSON_CMD_DICT['get_signal_quality'] = build_cmd_dict(
                '\s*\+CIND:\s+[0-9]*,(?P<sig>[0-9]*),.*')

ERICSSON_CMD_DICT['get_network_info'] = build_cmd_dict(re.compile(r"""
                \r\n
                \+COPS:\s+
                (
                (?P<error>\d) |
                \d,\d,             # or followed by num,num,str,num
                "(?P<netname>[^"]*)",
                (?P<status>\d)
                )                  # end of group
                \s*\r\n
                """, re.VERBOSE))

# +CPBR: (1-200),80,14,20,80,128
ERICSSON_CMD_DICT['get_phonebook_size'] = build_cmd_dict(re.compile(r"""
                \r\n
                \+CPBR:\s
                \(\d\-(?P<size>\d+)\)
                (?P<ignored>,.*)?
                \r\n
                """, re.VERBOSE))


class EricssonSIMClass(SIMBaseClass):
    """Ericsson SIM Class"""

    def __init__(self, sconn):
        super(EricssonSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        self.sconn.reset_settings()
        self.sconn.disable_echo()

        # So that phonebook size is returned
        self.sconn.send_at('AT+CPBS="SM"')

        def init_callback(size):
            # setup SIM storage defaults
            d = self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            d.addCallback(lambda _: self.sconn.send_at('AT+CMER=3,0,0,1'))
            d.addCallback(lambda _: size)
            return d

        d = super(EricssonSIMClass, self).initialize(set_encoding=set_encoding)
        d.addCallback(init_callback)
        return d


class EricssonWrapper(WCDMAWrapper):
    """Wrapper for all Ericsson cards"""

    def __init__(self, device):
        super(EricssonWrapper, self).__init__(device)

    def add_contact(self, contact):
        name = from_u(contact.name)
        number = from_u(contact.number)

        if 'UCS2' in self.device.sim.charset:
            name = pack_ucs2_bytes(name)
            number = pack_ucs2_bytes(number)

        # common arguments for both operations (name and number)
        args = [name, number]

        if contact.index:
            # contact.index is set, user probably wants to overwrite an
            # existing contact
            args.append(contact.index)
            d = super(WCDMAWrapper, self).add_contact(*args)
            d.addCallback(lambda _: contact.index)
            return d

        # contact.index is not set, this means that we need to obtain the
        # first slot free on the phonebook and then add the contact

        def get_next_id_cb(index):
            args.append(index)
            d2 = super(WCDMAWrapper, self).add_contact(*args)
            # now we just fake add_contact's response and we return the index
            d2.addCallback(lambda _: index)
            return d2

        d = self._get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

    def change_pin(self, oldpin, newpin):
        where = "SC"
        if 'UCS2' in self.device.sim.charset:
            where = pack_ucs2_bytes("SC")
            oldpin = pack_ucs2_bytes(oldpin)
            newpin = pack_ucs2_bytes(newpin)

        atstr = 'AT+CPWD="%s","%s","%s"' % (where, oldpin, newpin)
        d = self.queue_at_cmd(ATCmd(atstr, name='change_pin'))
        d.addCallback(lambda result: result[0].group('resp'))
        return d

    def disconnect_from_internet(self):
        self.device.set_status(consts.MM_MODEM_STATE_DISCONNECTING)

        def disconnect_cb(ignored):
            # XXX: perhaps we should check the registration status here
            if self.device.status > consts.MM_MODEM_STATE_REGISTERED:
                self.device.set_status(consts.MM_MODEM_STATE_REGISTERED)

        d = self.send_at('AT*ENAP=0')
        d.addCallback(disconnect_cb)
        return d

    def enable_pin(self, pin, enable):
        where = "SC"
        if 'UCS2' in self.device.sim.charset:
            where = pack_ucs2_bytes("SC")
            pin = pack_ucs2_bytes(pin)

        at_str = 'AT+CLCK="%s",%d,"%s"' % (where, int(enable), pin)
        d = self.queue_at_cmd(ATCmd(at_str, name='enable_pin'))
        d.addCallback(lambda result: result[0].group('resp'))
        return d

    def enable_radio(self, enable):
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                return self.send_at('AT+CFUN=1')

            elif status in [1, 5, 6] and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_apns(self):
        if self.device.sim.charset != 'UCS2':
            return super(EricssonWrapper, self).get_apns()

        cmd = ATCmd("AT+CGDCONT?", name='get_apns')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda resp:
            [(int(r.group('index')), from_ucs2(r.group('apn'))) for r in resp])
        return d

    def get_band(self):
        return defer.succeed(consts.MM_NETWORK_BAND_ANY)

    def get_charset(self):
        d = super(EricssonWrapper, self).get_charset()
        d.addCallback(from_ucs2)
        return d

    def get_charsets(self):
        d = super(EricssonWrapper, self).get_charsets()

        def get_charsets_cb(charsets):
            ret = []
            for charset in charsets:
                if check_if_ucs2(charset):
                    charset = from_ucs2(charset)
                ret.append(charset)

            return ret

        d.addCallback(get_charsets_cb)
        return d

    def get_iccid(self):
        """Returns ICC identification number"""
        d = super(WCDMAWrapper, self).sim_access_restricted(
            COM_READ_BINARY, EF_ICCID, 0, 0, 10)

        def get_iccid_cb(response):
            data = response[0].group('response')
            if data is None:
                return ''
            if self.device.sim.charset == 'UCS2':
                data = from_ucs2(data)

            sw1 = int(response[0].group('sw1'))
            if sw1 not in SW_OK:
                # Command has not exec correctly.
                return ''

            # Parse BCD F padded string.
            result = ''
            i = 0
            while (i + 1 < len(data)):
                msd = data[i]
                lsd = data[i + 1]
                i += 2
                if lsd in ['f', 'F']:
                    break
                result += lsd
                if msd in ['f', 'F']:
                    break
                result += msd

            return result

        d.addCallback(get_iccid_cb)
        return d

    def get_network_mode(self):
        ERICSSON_CONN_DICT_REV = revert_dict(ERICSSON_CONN_DICT)

        def get_network_mode_cb(mode):
            if mode in ERICSSON_CONN_DICT_REV:
                return ERICSSON_CONN_DICT_REV[mode]

            raise E.General("unknown network mode: %d" % mode)

        d = self.get_radio_status()
        d.addCallback(get_network_mode_cb)
        return d

    def get_netreg_status(self):
        deferred = defer.Deferred()
        self.state_dict['creg_retries'] = 0

        def get_it(auxdef=None):

            def get_netreg_status_cb((mode, status)):
                self.state_dict['creg_retries'] += 1
                if self.state_dict['creg_retries'] > MAX_RETRIES:
                    return auxdef.callback((mode, status))

                if status == 4:
                    reactor.callLater(RETRY_TIMEOUT, get_it, auxdef)
                else:
                    return auxdef.callback((mode, status))

            d = super(EricssonWrapper, self).get_netreg_status()
            d.addCallback(get_netreg_status_cb)
            return auxdef

        return get_it(deferred)

    def get_operator_id(self):
        """
        Returns the ID of the network operator that issued the SIM card,
        formatted as a 5 or 6-digit MCC/MNC code (ex "310410").

        :raise General: When MCC+MNC cannot be retrieved.
        """

        d = defer.Deferred()

        # Another way to handle global variables.
        d.imsi = None
        d.mnc_length = None

        def get_op_id_eb(failure):
            log.msg("get_operator_id FAILURE: %s" % repr(failure.value))
            failure.raiseException()

        d.addErrback(get_op_id_eb)

        d_mnc = super(WCDMAWrapper, self).sim_access_restricted(
            COM_READ_BINARY, EF_AD, 0, 0, 4)

        def get_op_id_mnc_digits_cb(response):
            number = response[0].group('response')
            if number is None:
                raise E.General()
            if self.device.sim.charset == 'UCS2':
                number = from_ucs2(number)
            if len(number) < 8:
                raise E.General()
            number = int(number[6:8], 16)

            sw1 = int(response[0].group('sw1'))
            sw2 = int(response[0].group('sw2'))
            if sw1 not in SW_OK:
                # Command has not exec correctly.
                raise E.General()
            elif sw1 == 0x90 and sw2 != 0:
                raise E.General()
            elif number in range(2, 5):
                # We got MNC number of digits right.
                return number
            else:
                raise E.General()

        def get_op_id_mnc_digits_eb(failure):
            log.msg("get_operator_id mnc_digits FAILURE %s" % failure.value)
            failure.raiseException()

        d_mnc.addCallback(get_op_id_mnc_digits_cb)
        d_mnc.addCallback(d.callback)
        d_mnc.addErrback(get_op_id_mnc_digits_eb)
        d_mnc.addErrback(d.errback)

        def store_mnc_length(mnc_length):
            self.mnc_length = mnc_length

            d_imsi = self.get_imsi()
            d_imsi.addErrback(get_op_id_imsi_eb)
            d_imsi.addErrback(d.errback)
            return d_imsi

        d.addCallback(store_mnc_length)

        def get_op_id_imsi_eb(failure):
            log.msg("get_operator_id imsi FAILURE %s" % failure.value)
            failure.raiseException()

        def store_imsi(imsi):
            self.imsi = imsi
            return None

        d.addCallback(store_imsi)

        def get_op_id_cb(response):
            number = self.mnc_length  # An integer.
            imsi = self.imsi
            if number is None or imsi is None:
                raise E.General()
            length = number + 3
            if len(imsi) < length:
                raise E.General()
            return imsi[0:length]

        d.addCallback(get_op_id_cb)

        return d

    def get_signal_quality(self):
        # On Ericsson, AT+CSQ only returns valid data in GPRS mode
        # So we need to override and provide an alternative. +CIND
        # returns an indication between 0-5 so let's just multiply
        # that by 20 to get a RSSI between 0-100%

        def get_signal_quality_cb(response):
            try:
                return int(response[0].group('sig')) * 20
            except IndexError:
                # Sometimes it won't reply to a +CIND? command
                # we'll assume that we don't have RSSI right now
                return 0

        cmd = ATCmd('AT+CIND?', name='get_signal_quality')
        d = self.queue_at_cmd(cmd)
        d.addCallback(get_signal_quality_cb)
        return d

    def get_spn(self):
        """
        Returns SPN Service Provider Name from SIM.
        """
        #  AT+CRSM=176,28486,0,1,16
        d = super(WCDMAWrapper, self).sim_access_restricted(
            COM_READ_BINARY, EF_SPN, 0, 1, 16)

        def get_spn_cb(response):
            spn = response[0].group('response')
            if spn:
                if self.device.sim.charset == 'UCS2':
                    spn = from_ucs2(spn)
                spn = from_8bit_in_gsm_or_ts31101(spn)
            return spn or ''

        d.addCallback(get_spn_cb)
        return d

    def get_pin_status(self):

        def ericsson_get_pin_status(facility):
            """
            Checks whether the pin is enabled or disabled
            """
            cmd = ATCmd('AT+CLCK="%s",2' % facility, name='get_pin_status')
            return self.queue_at_cmd(cmd)

        def pinreq_errback(failure):
            failure.trap(E.SimPinRequired)
            return 1

        def aterror_eb(failure):
            failure.trap(E.General)
            # return the failure or wont work
            return failure

        facility = 'SC'
        if self.device.sim.charset == 'UCS2':
            facility = pack_ucs2_bytes('SC')

        d = ericsson_get_pin_status(facility)  # call the local one
        d.addCallback(lambda response: int(response[0].group('status')))
        d.addErrback(pinreq_errback)
        d.addErrback(aterror_eb)
        return d

    def _regexp_to_contact(self, match):
        """
        Returns a :class:`wader.common.contact.Contact` out of ``match``

        :type match: ``re.MatchObject``
        """
        name = match.group('name')
        number = match.group('number')
        if self.device.sim.charset == 'UCS2':
            name = from_ucs2(name)
            number = from_ucs2(number)

        index = int(match.group('id'))
        return Contact(name, number, index=index)

    def mbm_authenticate(self, user, passwd):
        conn_id = self.state_dict.get('conn_id')
        if conn_id is None:
            raise E.CallIndexError("conn_id is None")

        if self.device.sim.charset == 'UCS2':
            args = (conn_id, pack_ucs2_bytes(user), pack_ucs2_bytes(passwd))
        else:
            args = (conn_id, user, passwd)

        return self.send_at('AT*EIAAUW=%d,1,"%s","%s"' % args)

    def set_apn(self, apn):
        if self.device.sim.charset != 'UCS2':
            # no need to encode params in UCS2
            return super(EricssonWrapper, self).set_apn(apn)

        def process_apns(apns, the_apn):
            for _index, _apn in apns:
                if _apn == the_apn:
                    self.state_dict['conn_id'] = _index
                    return defer.succeed('OK')

            try:
                conn_id = max([idx for idx, _ in apns]) + 1
            except (ValueError, TypeError):
                conn_id = 1

            self.state_dict['conn_id'] = conn_id
            args = tuple([conn_id] + map(pack_ucs2_bytes, ["IP", the_apn]))
            cmd = ATCmd('AT+CGDCONT=%d,"%s","%s"' % args, name='set_apn')
            d = self.queue_at_cmd(cmd)
            d.addCallback(lambda response: response[0].group('resp'))
            return d

        d = self.get_apns()
        d.addCallback(process_apns, apn)
        d.addErrback(log.err)
        return d

    def set_band(self, band):
        if band == consts.MM_NETWORK_BAND_ANY:
            return defer.succeed('OK')

        raise KeyError("Unsupported band %d" % band)

    def set_charset(self, charset):
        # The oddity here is that the set command needs to have its charset
        # value encoded in the current character set
        if self.device.sim.charset == 'UCS2':
            charset = pack_ucs2_bytes(charset)

        d = super(EricssonWrapper, self).set_charset(charset)
        return d

    def set_allowed_mode(self, mode):
        if mode not in self.custom.allowed_dict:
            raise KeyError("Mode %d not found" % mode)

        if self.device.get_property(consts.NET_INTFACE, "AllowedMode") == mode:
            # NOOP
            return defer.succeed("OK")

        def set_allowed_mode_cb(ign=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return ign

        return self.send_at("AT+CFUN=%d" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %d not found" % mode)

        return self.send_at("AT+CFUN=%d" % self.custom.conn_dict[mode])

    def reset_settings(self):
        cmd = ATCmd('AT&F', name='reset_settings')
        return self.queue_at_cmd(cmd)


class EricssonF3607gwWrapper(EricssonWrapper):
    """Wrapper for F3307 / F3607gw Ericsson cards"""

    def find_contacts(self, pattern):
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                [c for c in contacts
                       if c.name.lower().startswith(pattern.lower())])
        return d


class EricssonSimpleStateMachine(SimpleStateMachine):
    begin = SimpleStateMachine.begin
    check_pin = SimpleStateMachine.check_pin
    register = SimpleStateMachine.register
    wait_for_registration = SimpleStateMachine.wait_for_registration

    class set_apn(Mode):

        def __enter__(self):
            log.msg("EricssonSimpleStateMachine: set_apn entered")
            self.sconn.set_charset("GSM")

        def __exit__(self):
            log.msg("EricssonSimpleStateMachine: set_apn exited")

        def do_next(self):
            if 'apn' in self.settings:
                d = self.sconn.set_apn(self.settings['apn'])
                d.addCallback(lambda _:
                                self.transition_to('wait_for_registration'))
            else:
                self.transition_to('wait_for_registration')

    class connect(Mode):

        def __enter__(self):
            log.msg("EricssonSimpleStateMachine: connect entered")

        def __exit__(self):
            log.msg("EricssonSimpleStateMachine: connect exited")
            # restore charset after being connected
            self.sconn.set_charset("UCS2")

        def do_next(self):

            def on_e2nap_done(_):
                conn_id = self.sconn.state_dict.get('conn_id')
                if conn_id is None:
                    raise E.CallIndexError("conn_id is None")

                return self.sconn.send_at("AT*ENAP=1,%d" % conn_id)

            def on_mbm_authenticated(_):
                self.device.set_status(consts.MM_MODEM_STATE_CONNECTING)
                return self.sconn.send_at("AT*E2NAP=1")

            username = self.settings.get('username', '')
            password = self.settings.get('password', '')

            d = self.sconn.mbm_authenticate(username, password)
            d.addErrback(log.err)
            d.addCallback(on_mbm_authenticated)
            d.addCallback(on_e2nap_done)
            d.addCallback(lambda _:
                    self.device.set_status(consts.MM_MODEM_STATE_CONNECTED))
            d.addCallback(lambda _: self.transition_to('done'))

    class done(Mode):

        def __enter__(self):
            log.msg("EricssonSimpleStateMachine: done entered")

        def __exit__(self):
            log.msg("EricssonSimpleStateMachine: done exited")

        def do_next(self):
            # give it some time to connect
            reactor.callLater(5, self.notify_success)


class EricssonCustomizer(WCDMACustomizer):
    """Base customizer class for Ericsson cards"""
    # Multiline so we catch and remove the ESTKSMENU
    async_regexp = re.compile("\r\n(?P<signal>[*+][A-Z]{3,}):(?P<args>.*)\r\n",
                              re.MULTILINE)
    allowed_dict = ERICSSON_ALLOWED_DICT
    band_dict = ERICSSON_BAND_DICT
    cmd_dict = ERICSSON_CMD_DICT
    conn_dict = ERICSSON_CONN_DICT
    device_capabilities = [S.SIG_SMS_NOTIFY_ONLINE]

    signal_translations = {
        '*ESTKDISP': (None, None),
        '*ESTKSMENU': (None, None),
        '*EMWI': (None, None),
        '*E2NAP': (None, None),
        '+CIEV': (None, None),
        '+PACSP0': (None, None)}

    wrapper_klass = EricssonWrapper
    simp_klass = EricssonSimpleStateMachine


class EricssonF3607gwCustomizer(EricssonCustomizer):
    wrapper_klass = EricssonF3607gwWrapper


class EricssonDevicePlugin(DevicePlugin):
    """DevicePlugin for Ericsson"""

    sim_klass = EricssonSIMClass
    custom = EricssonCustomizer()

    def __init__(self):
        super(EricssonDevicePlugin, self).__init__()
