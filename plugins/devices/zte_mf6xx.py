# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Copyright (C) 2011       Vodafone España, S.A.
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

from core.hardware.zte import ZTEWCDMADevicePlugin

from plugins.zte_mf620 import ZTEMF620
from plugins.zte_mf632 import ZTEMF632
from plugins.zte_mf628 import ZTEMF628
from plugins.onda_mt503hs import ONDAMT503HS


class ZTEMF6XX(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's MF6XX Family"""
    name = "ZTE MF6XX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0001],
    }

    def __init__(self):
        super(ZTEMF6XX, self).__init__()

        self.mapping = {
            'MF620': ZTEMF620,
            'MF632': ZTEMF632,

            'default': ZTEMF620,
        }

zte_mf6xx = ZTEMF6XX()


class ZTEMF628X(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's MF628 Family"""
    name = "ZTE MF628X"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0002],
    }

    def __init__(self):
        super(ZTEMF628X, self).__init__()

        self.mapping = {
            'MF628': ZTEMF628,
            'MT503HS': ONDAMT503HS,

            'default': ZTEMF628,
        }

zte_mf628x = ZTEMF628X()
