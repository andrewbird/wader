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
Common stuff for all ZTE's Icera based cards
"""

import re
from twisted.internet import defer

from wader.common import consts
from wader.common.command import get_cmd_dict_copy, build_cmd_dict
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.sim import SIMBaseClass
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict
import wader.common.signals as S

ICERA_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY: 5,
    consts.MM_NETWORK_MODE_2G_ONLY: 0,
    consts.MM_NETWORK_MODE_3G_ONLY: 1,
    consts.MM_NETWORK_MODE_2G_PREFERRED: 2,
    consts.MM_NETWORK_MODE_3G_PREFERRED: 3,
}

ICERA_BAND_DICT = {
}

ICERA_CMD_DICT = get_cmd_dict_copy()

# \r\n+CPBR: (1-200),80,14,0,0,0\r\n\r\nOK\r\n
ICERA_CMD_DICT['get_phonebook_size'] = build_cmd_dict(
    re.compile(r"""
        \r\n
        \+CPBR:\s
        \(\d+-(?P<size>\d+)\).*
        \r\n
    """, re.VERBOSE))

# \r\n+CMGL: 1,1,"616E64726577",23\r\n
# 0791447758100650040C9144977162470100009011503195310004D436390C\r\n
ICERA_CMD_DICT['list_sms'] = build_cmd_dict(
    re.compile(r"""
        \r\n
        \+CMGL:\s
        (?P<id>\d+),
        (?P<where>\d),
        (?P<alpha>"\w*?")?,
        \d+
        \r\n(?P<pdu>\w+)
    """, re.VERBOSE))

# \r\n%IPSYS: 1,2\r\n
ICERA_CMD_DICT['get_network_mode'] = build_cmd_dict(
    re.compile(r"""
        %IPSYS:\s
        (?P<mode>\d+),
        (?P<domain>\d+)
    """, re.VERBOSE))

ICERA_CONN_DICT_REV = {
    '2G-GPRS': consts.MM_NETWORK_MODE_GPRS,
    '2G-EDGE': consts.MM_NETWORK_MODE_EDGE,
    '3G': consts.MM_NETWORK_MODE_UMTS,
    '3G-HSDPA': consts.MM_NETWORK_MODE_HSDPA,
    '3G-HSUPA': consts.MM_NETWORK_MODE_HSUPA,
    '3G-HSDPA-HSUPA': consts.MM_NETWORK_MODE_HSPA,
}


def icera_new_conn_mode(args):
    if not args:
        return consts.MM_NETWORK_MODE_UNKNOWN

    # ['4', '23415', '3G-HSDPA', '-', '0']
    rssi, network, tech, connected, regulation = args.split(',')

    if tech in ICERA_CONN_DICT_REV:
        return ICERA_CONN_DICT_REV[tech]
    else:
        # ['0', '2g', '3g'] '*g' == only C/S attached
        return consts.MM_NETWORK_MODE_UNKNOWN


class IceraSIMClass(SIMBaseClass):
    """
    Icera SIM Class

    I perform an initial setup in the device
    """

    def __init__(self, sconn):
        super(IceraSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        self.sconn.reset_settings()
        self.sconn.disable_echo()

        d = super(IceraSIMClass, self).initialize(set_encoding=set_encoding)

        def init_callback(size):
            # setup SIM storage defaults
            d = self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            # turn on unsolicited network notifications
            d.addCallback(lambda _: self.sconn.send_at('AT%NWSTATE=1'))
            d.addCallback(lambda _: size)
            return d

        d.addCallback(init_callback)
        return d


class IceraWrapper(WCDMAWrapper):
    """Wrapper for all ZTE Icera based cards"""

    def enable_radio(self, enable):
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                return self.send_at('AT+CFUN=1')

            elif status in [1, 5, 6] and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_band(self):
        return defer.succeed(consts.MM_NETWORK_BAND_ANY)

    def get_network_mode(self):
        """Returns the current network mode"""

        def get_network_mode_cb(resp):
            _mode = int(resp[0].group('mode'))
            ICERA_MODE_DICT_REV = revert_dict(ICERA_MODE_DICT)
            if _mode in ICERA_MODE_DICT_REV:
                return ICERA_MODE_DICT_REV[_mode]

            raise KeyError("Unknown network mode %s" % tech)

        d = self.send_at('AT%IPSYS?', name='get_network_mode',
                         callback=get_network_mode_cb)
        return d

    def set_band(self, band):
        if band == consts.MM_NETWORK_BAND_ANY:
            return defer.succeed('OK')

        raise KeyError("Unsupported band %d" % band)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %s not found" % mode)

        return self.send_at("AT%%IPSYS=%d" % self.custom.conn_dict[mode])


class IceraWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for ZTE Icera based devices"""
    async_regexp = re.compile("""
                    \r\n
                    (?P<signal>%[A-Z]{3,}):\s*(?P<args>.*)
                    \r\n""", re.VERBOSE)
    band_dict = ICERA_BAND_DICT
    conn_dict = ICERA_MODE_DICT
    cmd_dict = ICERA_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE]
    signal_translations = {
        '%NWSTATE': (S.SIG_NETWORK_MODE, icera_new_conn_mode),
    }
    wrapper_klass = IceraWrapper


class IceraWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for ZTE Icera based devices"""
    sim_klass = IceraSIMClass
    custom = IceraWCDMACustomizer()
