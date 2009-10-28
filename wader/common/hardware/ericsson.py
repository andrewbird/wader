# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
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

from epsilon.modal import mode
from twisted.internet import defer, reactor
from twisted.python import log

import wader.common.aterrors as E
from wader.common.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from wader.common import consts
from wader.common.encoding import (pack_ucs2_bytes, from_u, check_if_ucs2,
                                   from_ucs2)
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.sim import SIMBaseClass
from wader.common.statem.simple import SimpleStateMachine

MAX_RETRIES = 6
RETRY_TIMEOUT = 4

ERICSSON_BAND_DICT = {
    consts.MM_NETWORK_BAND_UNKNOWN : None,
    consts.MM_NETWORK_BAND_ANY : None,
}

ERICSSON_CONN_DICT = {
    consts.MM_NETWORK_MODE_ANY : 1,
    consts.MM_NETWORK_MODE_2G_ONLY : 5,
    consts.MM_NETWORK_MODE_3G_ONLY : 6,
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
# *ERINFO: 0,0,2
ERICSSON_CMD_DICT['get_network_mode'] = build_cmd_dict(
                '\r\n\*ERINFO:\s(?P<mode>\d),(?P<gsm>\d),(?P<umts>\d)\r\n')


class EricssonSIMClass(SIMBaseClass):
    """Ericsson SIM Class"""

    def __init__(self, sconn):
        super(EricssonSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        self.sconn.reset_settings()
        self.sconn.disable_echo()

        d = super(EricssonSIMClass, self).initialize(set_encoding=set_encoding)

        def init_callback(size):
            # setup SIM storage defaults
            d = self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            d.addCallback(lambda _: self.sconn.send_at('AT+CMER=3,0,0,1'))
            d.addCallback(lambda _: size)
            return d

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
        d = self.send_at('AT*ENAP=0')
        d.addCallback(lambda _: self.device.set_status(consts.DEV_ENABLED))
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

        def get_charset_cb(charset):
            if check_if_ucs2(charset):
                charset = from_ucs2(charset)
            return charset

        d.addCallback(get_charset_cb)
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

    def get_network_mode(self):

        def get_network_mode_cb(resp):
            gsm = int(resp[0].group('gsm'))
            umts = int(resp[0].group('umts'))

            if gsm == ERINFO_2G_GPRS:
                return consts.MM_NETWORK_MODE_GPRS
            elif gsm == ERINFO_2G_EGPRS:
                return consts.MM_NETWORK_MODE_EDGE
            elif umts == ERINFO_3G_UMTS:
                return consts.MM_NETWORK_MODE_UMTS
            elif umts == ERINFO_3G_HSDPA:
                return consts.MM_NETWORK_MODE_HSDPA

            raise E.GenericError("unknown network mode: %d, %d" % (gsm, umts))

        cmd = ATCmd('AT*ERINFO?', name='get_network_mode')
        d = self.queue_at_cmd(cmd)
        d.addCallback(get_network_mode_cb)
        return d

    def get_netreg_status(self):
        deferred = defer.Deferred()
        self.state_dict['creg_retries'] = 0

        def get_it(auxdef=None):

            def get_netreg_status_cb((_mode, status)):
                self.state_dict['creg_retries'] += 1
                if self.state_dict['creg_retries'] > MAX_RETRIES:
                    return auxdef.callback((_mode, status))

                if status == 4:
                    reactor.callLater(RETRY_TIMEOUT, get_it, auxdef)
                else:
                    return auxdef.callback((_mode, status))

            d = super(EricssonWrapper, self).get_netreg_status()
            d.addCallback(get_netreg_status_cb)
            return auxdef

        return get_it(deferred)

    def get_signal_quality(self):
        # On Ericsson, AT+CSQ only returns valid data in GPRS mode
        # So we need to override and provide an alternative. +CIND
        # returns an indication between 0-5 so let's just multiply
        # that by 6 to get a RSSI between 0-30
        cmd = ATCmd('AT+CIND?', name='get_signal_quality')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda response: int(response[0].group('sig')) * 6)
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
            failure.trap(E.GenericError)
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

    def mbm_authenticate(self, user, passwd):
        conn_id = self.state_dict['conn_id']
        if self.device.sim.charset == 'UCS2':
            args = (conn_id, pack_ucs2_bytes(user), pack_ucs2_bytes(passwd))
        else:
            args = (conn_id, user, passwd)

        return self.send_at('AT*EIAAUW=%d,1,"%s","%s"' % args)

    def set_apn(self, apn):
        if self.device.sim.charset != 'UCS2':
            # no need to encode params in UCS2
            return super(EricssonWrapper, self).set_apn(apn)

        def process_apns(apns):
            state = self.state_dict
            for _index, _apn in apns:
                if apn == _apn:
                    state['conn_id'] = _index
                    return

            conn_id = state['conn_id'] = len(apns) + 1
            args = tuple([conn_id] + map(pack_ucs2_bytes, ["IP", apn]))
            cmd = ATCmd('AT+CGDCONT=%d,"%s","%s"' % args, name='set_apn')
            d = self.queue_at_cmd(cmd)
            d.addCallback(lambda response: response[0].group('resp'))
            return d

        d = self.get_apns()
        d.addCallback(process_apns)
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

    def set_network_mode(self, mode):
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %d not found" % mode)

        return self.send_at("AT+CFUN=%d" % self.custom.conn_dict[mode])

    def reset_settings(self):
        cmd = ATCmd('AT&F', name='reset_settings')
        return self.queue_at_cmd(cmd)


class EricssonSimpleStateMachine(SimpleStateMachine):
    begin = SimpleStateMachine.begin
    check_pin = SimpleStateMachine.check_pin
    register = SimpleStateMachine.register

    class set_apn(mode):

        def __enter__(self):
            log.msg("EricssonSimpleStateMachine: set_apn entered")
            self.sconn.set_charset("GSM")

        def __exit__(self):
            log.msg("EricssonSimpleStateMachine: set_apn exited")

        def do_next(self):
            if 'apn' in self.settings:
                d = self.sconn.set_apn(self.settings['apn'])
                d.addCallback(lambda _: self.transition_to('connect'))
            else:
                self.transition_to('connect')

    class connect(mode):

        def __enter__(self):
            log.msg("EricssonSimpleStateMachine: connect entered")

        def __exit__(self):
            log.msg("EricssonSimpleStateMachine: connect exited")
            # restore charset after being connected
            self.sconn.set_charset("UCS2")

        def do_next(self):

            def on_e2nap_done(_):
                conn_id = self.sconn.state_dict['conn_id']
                return self.sconn.send_at("AT*ENAP=1,%d" % conn_id)

            def on_mbm_authenticated(_):
                return self.sconn.send_at("AT*E2NAP=1")

            username = str(self.settings['username'])
            password = str(self.settings['password'])

            d = self.sconn.mbm_authenticate(username, password)
            d.addErrback(log.err)
            d.addCallback(on_mbm_authenticated)
            d.addCallback(on_e2nap_done)
            d.addCallback(lambda _:
                    self.device.set_status(consts.DEV_CONNECTED))
            d.addCallback(lambda _: self.transition_to('done'))

    class done(mode):

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

    band_dict = ERICSSON_BAND_DICT
    cmd_dict = ERICSSON_CMD_DICT
    conn_dict = ERICSSON_CONN_DICT

    signal_translations = {
        '*ESTKDISP' : (None, None),
        '*ESTKSMENU': (None, None),
        '*EMWI' : (None, None),
        '*E2NAP' : (None, None),
        '+CIEV' : (None, None),
        '+PACSP0' : (None, None),
    }

    wrapper_klass = EricssonWrapper
    simp_klass = EricssonSimpleStateMachine


class EricssonDevicePlugin(DevicePlugin):
    """DevicePlugin for Ericsson"""

    sim_klass = EricssonSIMClass
    custom = EricssonCustomizer()

    def __init__(self):
        super(EricssonDevicePlugin, self).__init__()
