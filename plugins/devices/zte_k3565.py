# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

__version__ = "$Rev: 1209 $"

from wader.common.hardware.zte import ZTEWCDMADevicePlugin
from twisted.python import log

class ZTEK3565(ZTEWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for ZTE K3565-Z
    """
    name = "ZTE K3565-Z"
    version = "0.1"
    author = "Andrew Bird"

    __remote_name__ = "K3565-Z"

    __properties__ = {
        'usb_device.vendor_id': [0x19d2],
        'usb_device.product_id': [0x0049, 0x0052, 0x0063], # depends on firmware version
    }

    def preprobe_init(self, ports, info):
        if info['usb_device.product_id'] == 0x0052:
            self.hardcoded_ports = (2,1) # K3565-Z (0x0052) uses ttyUSB2(data) and ttyUSB1(status)
        elif info['usb_device.product_id'] == 0x0063:
            self.hardcoded_ports = (3,1) # K3565-Z (0x0063) uses ttyUSB3(data) and ttyUSB1(status)
        else: # let probing occur
            log.msg("Unknown K3565-Z product ID, falling through to probing")

zte_k3565 = ZTEK3565()

