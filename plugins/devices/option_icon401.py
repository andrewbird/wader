# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Pablo Marti
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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.option import OptionHSOWCDMADevicePlugin


class OptionIcon401(OptionHSOWCDMADevicePlugin):
    """:class:`core.plugin.DevicePlugin` for Options's Icon 401"""
    name = "Option Icon 401"
    version = "0.1"
    author = "Pablo Marti"

    __remote_name__ = "GlobeTrotter HSUPA Modem"

    __properties__ = {
          'ID_VENDOR_ID': [0x0af0],
          'ID_MODEL_ID': [0x7401],
    }

    conntype = WADER_CONNTYPE_USB

optionicon401 = OptionIcon401()
