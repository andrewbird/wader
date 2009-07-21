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
DevicePlugin for the HP branded Sierra Wireless MC8755 embedded device
"""

from wader.common.hardware.sierra import SierraWCDMADevicePlugin

# Community developed plugin
class SierraWirelessMC8755(SierraWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for SierraWireless MC 8755"""
    name = "SierraWireless MC8755"
    version = "0.1"
    author = "John J Doe"

    __remote_name__ = "MC8755"

    __properties__ = {
        'usb_device.vendor_id' : [0x03f0],
        'usb_device.product_id': [0x1e1d],
    }

sierrawirelessmc8755 = SierraWirelessMC8755()

