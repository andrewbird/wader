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
"""
Common stuff for all Ericsson's cards
"""

import re

from wader.common.command import (get_cmd_dict_copy, build_cmd_dict,
                                  ATCmd)
from wader.common import consts
import wader.common.aterrors as E
from wader.common.encoding import pack_ucs2_bytes, from_u
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.sim import SIMBaseClass

ERICSSON_BAND_DICT = {
}

ERICSSON_CONN_DICT = {
    consts.MM_NETWORK_MODE_GPRS : 5,
    consts.MM_NETWORK_MODE_EDGE : 5,
    consts.MM_NETWORK_MODE_2G_ONLY : 5,
    consts.MM_NETWORK_MODE_2G_PREFERRED: 5,

    consts.MM_NETWORK_MODE_UMTS : 6,
    consts.MM_NETWORK_MODE_HSDPA : 6,
    consts.MM_NETWORK_MODE_HSUPA : 6,
    consts.MM_NETWORK_MODE_HSPA : 6,
    consts.MM_NETWORK_MODE_3G_ONLY : 6,

    consts.MM_NETWORK_MODE_3G_PREFERRED: 1,
}

ERICSSON_CONN_DICT_REV = {
    1 : consts.MM_NETWORK_MODE_3G_PREFERRED,
    5 : consts.MM_NETWORK_MODE_2G_PREFERRED,
    6 : consts.MM_NETWORK_MODE_3G_ONLY,
}

ERICSSON_CMD_DICT = get_cmd_dict_copy()

ERICSSON_CMD_DICT['get_card_model'] = build_cmd_dict('\s*(?P<model>\S*)\r\n')

# +CIND: 5,5,0,0,1,0,1,0,1,1,0,0
ERICSSON_CMD_DICT['get_signal_quality'] = build_cmd_dict(
                '\s*\+CIND:\s+[0-9]*,(?P<sig>[0-9]*),.*')

ERICSSON_CMD_DICT['get_network_info'] =  build_cmd_dict(r"""
                \r\n
                \+COPS:\s+
                (
                (?P<error>\d) |
                \d,\d,             # or followed by num,num,str,num
                "(?P<netname>[^"]*)",
                (?P<status>\d)
                )                  # end of group
                \s*\r\n
                """, re.VERBOSE)

# +CPBR: 1,"002B003500350035",145,"0041004A0042"\r\n'
ERICSSON_CMD_DICT['get_contacts'] = build_cmd_dict(r"""
                \r\n
                \+CPBR:\s(?P<id>\d+),
                "(?P<number>\+?[0-9A-Fa-f]+)",
                (?P<cat>\d+),
                "(?P<name>.*)"
                """, re.VERBOSE)


class EricssonSIMClass(SIMBaseClass):
    """
    Ericsson SIM Class
    """
    def __init__(self, sconn):
        super(EricssonSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        self.sconn.reset_settings()
        self.sconn.disable_echo()

        d = super(EricssonSIMClass, self).initialize(set_encoding=set_encoding)
        def init_callback(size):
            # setup SIM storage defaults
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return size

        d.addCallback(init_callback)
        return d


class EricssonWrapper(WCDMAWrapper):
    """
    Wrapper for all Ericsson cards
    """
    def __init__(self, device):
        super(EricssonWrapper, self).__init__(device)

    def add_contact(self, contact):
        name = from_u(contact.name)
        number =  from_u(contact.number)

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

        d = super(WCDMAWrapper, self).get_next_contact_id()
        d.addCallback(get_next_id_cb)
        return d

    def get_band(self):
        raise NotImplementedError()

    def get_network_mode(self):
        def get_radio_status_cb(mode):
            if mode in ERICSSON_CONN_DICT_REV:
                return ERICSSON_CONN_DICT_REV[mode]

            raise KeyError("Unknown network mode %d" % mode)

        d = self.get_radio_status()
        d.addCallback(get_radio_status_cb)
        return d

    def get_signal_quality(self):
        # On Ericsson, AT+CSQ only returns valid data in GPRS mode
        # So we need to override and provide an alternative. +CIND
        # returns an indication between 0-5 so let's just multiply
        # that by 20 to get a normalized RSSI
        cmd = ATCmd('AT+CIND?',name='get_signal_quality')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda response: int(response[0].group('sig')) * 20)
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

        facility = pack_ucs2_bytes('SC') if self.device.sim.charset == 'UCS2' else 'SC'

        d = ericsson_get_pin_status(facility)                    # call the local one
        d.addCallback(lambda response: int(response[0].group('status')))
        d.addErrback(pinreq_errback)
        d.addErrback(aterror_eb)
        return d

    def set_band(self, band):
        if band not in self.custom.band_dict:
            raise KeyError("Band %d not found" % band)

        raise NotImplementedError()

    def set_charset(self, charset):
        # The oddity here is that the set command needs to have its charset value
        # encoded in the current character set
        if self.device.sim.charset == 'UCS2':
            charset = pack_ucs2_bytes(charset)

        d = super(EricssonWrapper, self).set_charset(charset)
        return d

    def set_network_mode(self, mode):
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %d not found" % mode)

        return self.send_at("AT+CFUN=%d" % mode)

    def reset_settings(self):
        cmd = ATCmd('AT&F', name='reset_settings')
        return self.queue_at_cmd(cmd)


class EricssonCustomizer(WCDMACustomizer):
    """
    Base Customizer class for Ericsson cards
    """

    wrapper_klass = EricssonWrapper

    # Multiline so we catch and remove the ESTKSMENU
    async_regexp = re.compile("\r\n(?P<signal>[*+][A-Z]{3,}):(?P<args>.*)\r\n",
                              re.MULTILINE)

    band_dict = ERICSSON_BAND_DICT
    cmd_dict = ERICSSON_CMD_DICT
    conn_dict = ERICSSON_CONN_DICT

    signal_translations = {
        '*ESTKSMENU': (None, None),
        '*EMWI' : (None, None),
        '+PACSP0' : (None, None),
    }

class EricssonDevicePlugin(DevicePlugin):
    """DevicePlugin for Ericsson"""
    sim_klass = EricssonSIMClass
    custom = EricssonCustomizer()

    def __init__(self):
        super(EricssonDevicePlugin, self).__init__()

