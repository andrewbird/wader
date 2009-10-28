# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

from wader.common.hardware.huawei import (HuaweiWCDMACustomizer,
                                          HuaweiWCDMADevicePlugin)


class HuaweiE510(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's E510"""
    name = "Huawei E510"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiWCDMACustomizer

    __remote_name__ = "E510"

    __properties__ = {
        'usb_device.vendor_id': [0x12d1],
        'usb_device.product_id': [0x1411],
    }

    def preprobe_init(self, ports, info):
        # This device might be found by means of the mother plugin too
        if info['usb_device.product_id'] == 0x1001:
            self.__properties__['usb_device.product_id'][0] = 0x1001

    hardcoded_ports = (0, 2)

huaweie510 = HuaweiE510()
