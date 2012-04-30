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

from twisted.internet import defer

from wader.common import consts
from core.command import get_cmd_dict_copy, build_cmd_dict
from core.hardware.base import WCDMACustomizer
from core.middleware import WCDMAWrapper
from core.plugin import DevicePlugin
from wader.common.utils import revert_dict

SIERRA_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: '00',
    consts.MM_ALLOWED_MODE_3G_ONLY: '01',
    consts.MM_ALLOWED_MODE_2G_ONLY: '02',
    consts.MM_ALLOWED_MODE_3G_PREFERRED: '03',
    consts.MM_ALLOWED_MODE_2G_PREFERRED: '04',
}

SIERRA_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY: '00',
    consts.MM_NETWORK_MODE_3G_ONLY: '01',
    consts.MM_NETWORK_MODE_2G_ONLY: '02',
    consts.MM_NETWORK_MODE_3G_PREFERRED: '03',
    consts.MM_NETWORK_MODE_2G_PREFERRED: '04',
}

SIERRA_BAND_DICT = {
    consts.MM_NETWORK_BAND_EGSM: '03',   # EGSM (900MHz)
    consts.MM_NETWORK_BAND_DCS: '03',    # DCS (1800MHz)
    consts.MM_NETWORK_BAND_PCS: '04',    # PCS (1900MHz)
    consts.MM_NETWORK_BAND_G850: '04',   # GSM (850 MHz)
    consts.MM_NETWORK_BAND_U2100: '02',  # WCDMA 2100Mhz         (Class I)
    consts.MM_NETWORK_BAND_U800: '02',   # WCDMA 3GPP UMTS800   (Class VI)
    consts.MM_NETWORK_BAND_ANY: '00',    # any band
}

SIERRA_CMD_DICT = get_cmd_dict_copy()

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
            return revert_dict(self.custom.band_dict)[band]

        return self.send_at("AT!BAND?", name='get_band',
                            callback=get_band_cb)

    def get_network_mode(self):
        """Returns the current used network mode"""

        def get_network_mode_cb(resp):
            mode = resp[0].group('mode')
            return revert_dict(self.custom.conn_dict)[mode]

        return self.send_at("AT!SELRAT?", name='get_network_mode',
                            callback=get_network_mode_cb)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if band not in self.custom.band_dict:
            raise KeyError("Unknown band %d" % band)

        return self.send_at("AT!BAND=%s" % self.custom.band_dict[band])

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode not in self.custom.allowed_dict:
            raise KeyError("Unknown mode %d" % mode)

        def set_allowed_mode_cb(ign=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return ign

        return self.send_at("AT!SELRAT=%s" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in self.custom.conn_dict:
            raise KeyError("Unknown mode %d" % mode)

        return self.send_at("AT!SELRAT=%s" % self.custom.conn_dict[mode])


class SierraWirelessWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for sierra wireless cards"""

    async_regexp = None
    allowed_dict = SIERRA_ALLOWED_DICT
    band_dict = SIERRA_BAND_DICT
    conn_dict = SIERRA_MODE_DICT
    cmd_dict = SIERRA_CMD_DICT
    wrapper_klass = SierraWrapper


class SierraWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for sierra wireless cards"""

    custom = SierraWirelessWCDMACustomizer()
