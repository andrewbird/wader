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
"""Common stuff for all Novatel's cards"""

import re

from wader.common import consts
from wader.common.command import get_cmd_dict_copy, build_cmd_dict
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict

NOVATEL_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY          : '0,2',
    consts.MM_NETWORK_MODE_2G_ONLY      : '1,1',
    consts.MM_NETWORK_MODE_3G_ONLY      : '2,1',
    consts.MM_NETWORK_MODE_2G_PREFERRED : '1,2',
    consts.MM_NETWORK_MODE_3G_PREFERRED : '2,2',
}

NOVATEL_BAND_DICT = {}
NOVATEL_CMD_DICT = get_cmd_dict_copy()

NOVATEL_CMD_DICT['get_network_mode'] = build_cmd_dict(
                            re.compile("\r\n\$NWRAT:\s?(?P<mode>\d,\d)\r\n"))

class NovatelWrapper(WCDMAWrapper):
    """Wrapper for all Novatel cards"""

    def get_network_mode(self):
        """Returns the current network mode"""
        def get_network_mode_cb(resp):
            mode = resp[0].group('mode')
            return revert_dict(NOVATEL_MODE_DICT)[mode]

        return self.send_at("AT$NWRAT?", name='get_network_mode',
                            callback=get_network_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in NOVATEL_MODE_DICT:
            raise KeyError("Unknown network mode %d" % mode)

        return self.send_at("AT$NWRAT=%s" % NOVATEL_MODE_DICT[mode])


class NovatelWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for Novatel cards"""
    async_regexp = None
    conn_dict = NOVATEL_MODE_DICT
    band_dict = NOVATEL_BAND_DICT
    cmd_dict = NOVATEL_CMD_DICT
    wrapper_klass = NovatelWrapper


class NovatelWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for Novatel cards"""
    custom = NovatelWCDMACustomizer()

