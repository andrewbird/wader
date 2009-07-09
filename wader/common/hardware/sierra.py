# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
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
"""Common stuff for all SierraWireless cards"""

import re

from wader.common import consts
from wader.common.command import get_cmd_dict_copy, build_cmd_dict
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict

SIERRA_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY          : '00',
    consts.MM_NETWORK_MODE_3G_ONLY      : '01',
    consts.MM_NETWORK_MODE_2G_ONLY      : '02',
    consts.MM_NETWORK_MODE_3G_PREFERRED : '03',
    consts.MM_NETWORK_MODE_2G_PREFERRED : '04',
}

SIERRA_BAND_DICT = {
    consts.MM_NETWORK_BAND_EGSM  : '03',   # EGSM (900MHz)
    consts.MM_NETWORK_BAND_DCS   : '03',   # DCS (1800MHz)
    consts.MM_NETWORK_BAND_PCS   : '04',   # PCS (1900MHz)
    consts.MM_NETWORK_BAND_G850  : '04',   # GSM (850 MHz)
    consts.MM_NETWORK_BAND_U2100 : '02',   # WCDMA 2100Mhz         (Class I)
    consts.MM_NETWORK_BAND_U800  : '02',   # WCDMA 3GPP UMTS800   (Class VI)
    consts.MM_NETWORK_BAND_ANY   : '00',   # any band
}

SIERRA_CMD_DICT = get_cmd_dict_copy()

SIERRA_CMD_DICT['get_netreg_status'] = build_cmd_dict(re.compile(
                    r"""
                    \r\n
                    \+CREG:\s
                    (?P<mode>\d),(?P<status>\d+)(,[0-9a-fA-F]*,[0-9a-fA-F]*)?
                    \r\n""", re.VERBOSE))

SIERRA_CMD_DICT['get_band'] = build_cmd_dict(re.compile(
                    "\r\n\!BAND:\s?(?P<band>\d+)"))

SIERRA_CMD_DICT['get_network_mode'] = build_cmd_dict(re.compile(
                    "\r\n\!SELRAT:\s?(?P<mode>\d+)"))


class SierraWrapper(WCDMAWrapper):
    """Wrapper for all Sierra cards"""

    def get_band(self):
        """Returns the current used band"""
        def get_band_cb(resp):
            band = resp[0].group('band')
            return revert_dict(SIERRA_BAND_DICT)[band]

        return self.send_at("AT!BAND?", name='get_band',
                            callback=get_band_cb)

    def get_network_mode(self):
        """Returns the current used network mode"""
        def get_network_mode_cb(resp):
            mode = resp[0].group('mode')
            return revert_dict(SIERRA_MODE_DICT)[mode]

        return self.send_at("AT!SELRAT?", name='get_network_mode',
                            callback=get_network_mode_cb)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if band not in SIERRA_BAND_DICT:
            raise KeyError("Unknown band %d" % band)

        return self.send_at("AT!BAND=%s" % SIERRA_BAND_DICT[band])

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in SIERRA_MODE_DICT:
            raise KeyError("Unknown mode %d" % mode)

        return self.send_at("AT!SELRAT=%s" % SIERRA_MODE_DICT[mode])


class SierraWirelessWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for sierra wireless cards"""
    async_regexp = None
    band_dict = SIERRA_BAND_DICT
    conn_dict = SIERRA_MODE_DICT
    cmd_dict = SIERRA_CMD_DICT
    wrapper_klass = SierraWrapper


class SierraWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for sierra wireless cards"""
    custom = SierraWirelessWCDMACustomizer()

