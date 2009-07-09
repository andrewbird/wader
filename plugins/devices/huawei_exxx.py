# -*- coding: utf-8 -*-
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

from wader.common.hardware.huawei import HuaweiWCDMADevicePlugin

from wader.plugins.huawei_e169 import HuaweiE169
from wader.plugins.huawei_e17X import HuaweiE17X
from wader.plugins.huawei_e180 import HuaweiE180
from wader.plugins.huawei_e220 import HuaweiE220
from wader.plugins.huawei_e270 import HuaweiE270
from wader.plugins.huawei_e272 import HuaweiE272
from wader.plugins.huawei_e620 import HuaweiE620
from wader.plugins.huawei_e660 import HuaweiE660
from wader.plugins.huawei_e660a import HuaweiE660A
from wader.plugins.huawei_e870 import HuaweiE870
from wader.plugins.huawei_k3520 import HuaweiK3520
from wader.plugins.huawei_em730v import HuaweiEM730V


class HuaweiEXXX1003(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's 1003 family"""
    name = "Huawei EXXX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'usb_device.vendor_id': [0x12d1],
        'usb_device.product_id': [0x1003, 0x1004],
    }

    def __init__(self):
        super(HuaweiEXXX1003, self).__init__()

        self.mapping = {
            'E17X' : HuaweiE17X,
            'E180' : HuaweiE180,
            'E220' : HuaweiE220,
            'E270' : HuaweiE270,
            'E272' : HuaweiE272,
            'E870' : HuaweiE870,

            'default' : HuaweiE220,
        }


class HuaweiEXXX1001(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's 1001 family"""
    name = "Huawei EXXX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'usb_device.vendor_id': [0x12d1],
        'usb_device.product_id': [0x1001],
    }

    def __init__(self):
        super(HuaweiEXXX1001, self).__init__()

        self.mapping = {
            'E169'  : HuaweiE169,
            'E660'  : HuaweiE660,
            'E660A' : HuaweiE660A,
            'E620'  : HuaweiE620,
            'K3520' : HuaweiK3520,
            'EM730V' : HuaweiEM730V,

            'default' : HuaweiE660,
        }


huaweiexxx1003 = HuaweiEXXX1003()
huaweiexxx1001 = HuaweiEXXX1001()

