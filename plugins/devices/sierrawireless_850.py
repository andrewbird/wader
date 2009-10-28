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
"""DevicePlugin for the Sierra Wireless 850 datacard"""

from wader.common.hardware.sierra import SierraWCDMADevicePlugin


class SierraWireless850(SierraWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for SierraWireless 850"""
    name = "SierraWireless 850"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = "AC850"   #response from AT+CGMM

    __properties__ = {
        'pcmcia.manf_id' : [0x192],
        'pcmcia.card_id': [0x710],
    }

sierrawireless850 = SierraWireless850()
