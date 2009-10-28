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

from wader.common.hardware.zte import ZTEWCDMADevicePlugin

from wader.plugins.zte_mf620 import ZTEMF620
from wader.plugins.zte_mf632 import ZTEMF632


class ZTEMF6XX(ZTEWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for ZTE's MF6XX Family"""
    name = "ZTE MF6XX"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = None

    __properties__ = {
        'usb_device.vendor_id': [0x19d2],
        'usb_device.product_id': [0x0001],
    }

    def __init__(self):
        super(ZTEMF6XX, self).__init__()

        self.mapping = {
            'MF620' : ZTEMF620,
            'MF632' : ZTEMF632,

            'default' : ZTEMF620,
        }

zte_mf6xx = ZTEMF6XX()
