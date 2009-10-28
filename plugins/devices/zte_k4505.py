# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
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

from wader.common.hardware.zte import ZTEWCDMADevicePlugin


class ZTEK4505(ZTEWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for ZTE's K4505
    """
    name = "ZTE K4505-Z"
    version = "0.1"
    author = "Andrew Bird"

    __remote_name__ = "K4505-Z"

    __properties__ = {
        'usb_device.vendor_id': [0x19d2],
        'usb_device.product_id': [0x0016],
    }

    # K4505-Z uses ttyUSB2(data) and ttyUSB1(status)
    hardcoded_ports = (2, 1)

zte_k4505 = ZTEK4505()
