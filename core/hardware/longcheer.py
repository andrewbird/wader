# -*- coding: utf-8 -*-
# Copyright (C) 2012  Sphere Systems Ltd
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
"""Common stuff for all Longcheer cards and rebranded variants"""

import re

from twisted.internet import defer

# also registers gsm0338 codec
from messaging.sms import is_gsm_text
from messaging.utils import unpack_msg

from wader.common import consts
from wader.common.aterrors import MalformedUssdPduError
from wader.common.encoding import pack_ucs2_bytes
from wader.common.utils import revert_dict

from core.command import get_cmd_dict_copy, build_cmd_dict
from core.hardware.base import WCDMACustomizer
from core.middleware import WCDMAWrapper
from core.plugin import DevicePlugin
from core.sim import SIMBaseClass

LONGCHEER_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: '2',  # 3g preferred
    consts.MM_ALLOWED_MODE_3G_ONLY: '1',
    consts.MM_ALLOWED_MODE_3G_PREFERRED: '2',
    consts.MM_ALLOWED_MODE_2G_ONLY: '3',
    consts.MM_ALLOWED_MODE_2G_PREFERRED: '4',
}

LONGCHEER_CONN_DICT = {
    consts.MM_NETWORK_MODE_ANY: '2',  # 3g preferred
    consts.MM_NETWORK_MODE_3G_ONLY: '1',
    consts.MM_NETWORK_MODE_3G_PREFERRED: '2',
    consts.MM_NETWORK_MODE_2G_ONLY: '3',
    consts.MM_NETWORK_MODE_2G_PREFERRED: '4',
}

LONGCHEER_CMD_DICT = get_cmd_dict_copy()

# +CPBR: 1,"+4917XXXXXX",145,"005400650073007400200053007400720069","",129,""
LONGCHEER_CMD_DICT['get_contact'] = build_cmd_dict(re.compile(r"""
    \r\n
    \+CPBR:\s(?P<id>\d+),
    "(?P<number>[+0-9a-fA-F*#]+)",
    (?P<cat>\d+),
    "(?P<name>.*?)"
    (?P<ignored>,\S*)?
    \r\n""", re.X))

LONGCHEER_CMD_DICT['list_contacts'] = build_cmd_dict(
    end=re.compile('(\r\n)?\r\n(OK)\r\n'), extract=re.compile(r"""
    \r\n
    \+CPBR:\s(?P<id>\d+),
    "(?P<number>[+0-9a-fA-F*#]+)",
    (?P<cat>\d+),
    "(?P<name>.*?)"
    (?P<ignored>,\S*)?
    """, re.X))

LONGCHEER_CMD_DICT['get_network_mode'] = build_cmd_dict(
    re.compile("\r\n\+MODODR:\s?(?P<mode>\d+)\r\n"))


class LongcheerSIMClass(SIMBaseClass):
    """Longcheer SIM Class"""

    def __init__(self, sconn):
        super(LongcheerSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):

        def init_callback(size):
            # make sure we are in most promiscuous mode before registration
            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            # set SMS storage default
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return(size)

        d = super(LongcheerSIMClass, self).initialize(set_encoding)
        d.addCallback(init_callback)
        return d


class LongcheerWCDMAWrapper(WCDMAWrapper):
    """Wrapper for all Longcheer cards"""

    def enable_radio(self, enable):
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                return self.send_at('AT+CFUN=1')

            elif status in [1] and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_band(self):
        """Returns the current used band"""
        return defer.succeed(consts.MM_NETWORK_BAND_ANY)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if band == consts.MM_NETWORK_BAND_ANY:
            return defer.succeed('OK')
        else:
            raise KeyError("Unsupported band %d" % band)

    def get_network_mode(self):
        """Returns the current network mode"""

        def cb(resp):
            mode = resp[0].group('mode')
            return revert_dict(self.custom.conn_dict)[mode]

        return self.send_at("AT+MODODR?", name='get_network_mode', callback=cb)

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode not in self.custom.allowed_dict:
            raise KeyError("Unknown network mode %d" % mode)

        def cb(ign=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return ign

        return self.send_at("AT+MODODR=%s" % self.custom.allowed_dict[mode],
                            callback=cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in self.custom.conn_dict:
            raise KeyError("Unknown network mode %d" % mode)

        return self.send_at("AT+MODODR=%s" % self.custom.conn_dict[mode])

    def send_ussd(self, ussd):
        """
        Sends the USSD command ``ussd``

        Sends plain or UCS2 encoded text
        Receives GSM 7bit compressed text
        """
        # AT+CUSD=1,"*100#",15
        # (*100#)
        # or
        # AT+CUSD=1,"002A0031003000300023",15
        # (*100#)

        # +CUSD: 1,"5079191E4E935BCDB2DBAF88818E753A3A2C2EBBD76F37FDAD90818E7"
        #          "53A3A2C2EBB5BD6B2DCEC3F8BC3F275394D57CC40C1BA991D26D7DD67"
        #          "D0B14E4787C565F70B1A1EAF5BF477EBF856D040D0F0780D6A86DDE17"
        #          "359AEB881A86179DA9C769BDF0A1C0899669BCB",15
        # Prepaid-Menü\n
        # 1 Guthabenkonto\n
        # 2 Guthaben-Verfügbarkeit\n
        # 3 Aufladung Guthaben/Pack-to-Go\n
        # 4 Pack Manager\n
        # 7 Tarifinfo\n
        # 8 Hilfe

        def convert_response(response):
            index = response[0].group('index')
            if index == '1':
                self.device.set_property(
                    consts.USD_INTFACE, 'State', 'user-response')
            else:
                self.device.set_property(consts.USD_INTFACE, 'State', 'idle')

            resp = response[0].group('resp')
            if resp is None:
                return ""   # returning the Empty string is valid

            try:
                ret = unpack_msg(resp).decode("gsm0338")
                if is_gsm_text(ret):
                    return ret
            except UnicodeError:
                pass

            try:
                return resp.decode('hex')
            except TypeError:
                raise MalformedUssdPduError(resp)

        def reset_state(failure):
            if self.device.get_property(consts.USD_INTFACE, 'State') != 'idle':
                self.device.set_property(consts.USD_INTFACE, 'State', 'idle')
            failure.raiseException()  # re-raise

        if 'UCS2' in self.device.sim.charset:
            ussd = pack_ucs2_bytes(ussd)

        d = super(WCDMAWrapper, self).send_ussd(str(ussd))
        d.addCallback(convert_response)
        d.addErrback(reset_state)
        return d


class LongcheerWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for Longcheer devices"""
    allowed_dict = LONGCHEER_ALLOWED_DICT
    cmd_dict = LONGCHEER_CMD_DICT
    conn_dict = LONGCHEER_CONN_DICT

    wrapper_klass = LongcheerWCDMAWrapper


class LongcheerWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for Longcheer devices"""
    sim_klass = LongcheerSIMClass
    custom = LongcheerWCDMACustomizer()
