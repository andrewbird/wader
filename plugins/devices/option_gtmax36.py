# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  kgb0y
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

from core.hardware.option import OptionWCDMADevicePlugin


class OptionGTMax36(OptionWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Option's GT Max 36"""
    name = "Option GT Max 36"
    version = "0.1"
    author = "kgb0y"

    __remote_name__ = "GlobeTrotter HSDPA Modem"

    __properties__ = {
        'ID_VENDOR_ID': [0x0af0],
        'ID_MODEL_ID': [0x6701],
    }

optiongtmax36 = OptionGTMax36()
