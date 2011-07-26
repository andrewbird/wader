# -*- coding: utf-8 -*-
# Copyright (C) 2006-2010  Vodafone España, S.A.
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

from wader.plugins.huawei_e160 import HuaweiE160
from wader.plugins.huawei_e160b import HuaweiE160B
from wader.plugins.huawei_e169 import HuaweiE169
from wader.plugins.huawei_e17X import HuaweiE17X
from wader.plugins.huawei_e180 import HuaweiE180
from wader.plugins.huawei_e220 import HuaweiE220
from wader.plugins.huawei_e270 import HuaweiE270
from wader.plugins.huawei_e272 import HuaweiE272
from wader.plugins.huawei_e510 import HuaweiE510
from wader.plugins.huawei_e620 import HuaweiE620
from wader.plugins.huawei_e660 import HuaweiE660
from wader.plugins.huawei_e660a import HuaweiE660A
from wader.plugins.huawei_e870 import HuaweiE870
from wader.plugins.huawei_e1550 import HuaweiE1550
from wader.plugins.huawei_e1692 import HuaweiE1692
from wader.plugins.huawei_e1750 import HuaweiE1750
from wader.plugins.huawei_e3735 import HuaweiE3735

from wader.plugins.huawei_k2540 import HuaweiK2540
from wader.plugins.huawei_k3520 import HuaweiK3520
from wader.plugins.huawei_k3565 import HuaweiK3565
from wader.plugins.huawei_k3715 import HuaweiK3715

from wader.plugins.huawei_em730v import HuaweiEM730V
from wader.plugins.huawei_em770 import HuaweiEM770

from wader.plugins.huawei_b970 import HuaweiB970


class HuaweiEXXX140c(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's 140c family"""
    name = "Huawei EXXX"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x140c],
    }

    def __init__(self):
        super(HuaweiEXXX140c, self).__init__()

        self.mapping = {
            'E1550': HuaweiE1550,
            'E1692': HuaweiE1692,
            'E1750': HuaweiE1750,

            'default': HuaweiE1550,
        }


class HuaweiEXXX1003(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's 1003 family"""
    name = "Huawei EXXX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1003, 0x1004],
    }

    def __init__(self):
        super(HuaweiEXXX1003, self).__init__()

        self.mapping = {
            'E870': HuaweiE870,      # Expresscards

            'E220': HuaweiE220,      # USB dongles
            'E270': HuaweiE270,
            'E272': HuaweiE272,

            'E160': HuaweiE160,      # USB Sticks
            'E160B': HuaweiE160B,
            'E17X': HuaweiE17X,
            'E180': HuaweiE180,
            'K3565': HuaweiK3565,

            'B970': HuaweiB970,      # Routers

            'default': HuaweiE220,
        }


class HuaweiEXXX1001(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's 1001 family"""
    name = "Huawei EXXX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1001, 0x1003],
    }

    def __init__(self):
        super(HuaweiEXXX1001, self).__init__()

        self.mapping = {
            'E620': HuaweiE620,      # Cardbus
            'E660': HuaweiE660,
            'E660A': HuaweiE660A,

            'E3735': HuaweiE3735,    # Expresscards

            'E510': HuaweiE510,      # USB dongles

            'E169': HuaweiE169,      # USB Sticks
            'E1550': HuaweiE1550,
            'K2540': HuaweiK2540,
            'K3520': HuaweiK3520,
            'K3565': HuaweiK3565,
            'K3715': HuaweiK3715,

            'EM730V': HuaweiEM730V,  # Embedded Modules
            'EM770': HuaweiEM770,

            'default': HuaweiE660,
        }


huaweiexxx140c = HuaweiEXXX140c()
huaweiexxx1003 = HuaweiEXXX1003()
huaweiexxx1001 = HuaweiEXXX1001()
