# -*- coding: utf-8 -*-
# Copyright (C) 2009 Vodafone España, S.A.
# Author: Andrew Bird
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

# Note: For this device to be identified by the OS the following two
# prerequisties must be statisfied:
# Kernel module 'hso' must be installed
# Option storage flipping and package 'ozerocdoff' must be installed
from wader.common.hardware.option import OptionHSOWCDMADevicePlugin


class OptionE3730(OptionHSOWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for Option's E3730
    """
    name = "Option E3730"
    version = "0.1"
    author = "Andrew Bird"
    dialer = 'hso'

    __remote_name__ = 'GlobeTrotter HSUPA Modem'

    __properties__ = {
        'usb_device.vendor_id' : [0x0af0],
        'usb_device.product_id': [0x7301],
    }

optione3730 = OptionE3730()
