# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone España, S.A.
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

from core.hardware.ericsson import (EricssonDevicePlugin,
                                            EricssonF3607gwCustomizer)


class ToshibaF3607gw(EricssonDevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Ericsson's Toshiba F3607gw"""
    name = "Toshiba F3607gw"
    version = "0.1"
    author = u"Andrew Bird"
    custom = EricssonF3607gwCustomizer()

    __remote_name__ = "F3607gw"

    __properties__ = {
        'ID_VENDOR_ID': [0x0930],
        'ID_MODEL_ID': [0x130c, 0x1311],
    }


toshibaF3607gw = ToshibaF3607gw()
