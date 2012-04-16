# -*- coding: utf-8 -*-
# Author:  Pablo Martí Gamboa
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

from wader.common.consts import WADER_CONNTYPE_EMBEDDED
from core.hardware.novatel import NovatelWCDMADevicePlugin


class NovatelEU740(NovatelWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Novatel's EU740"""
    name = "Novatel EU740"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = "Expedite EU740"

    __properties__ = {
        'ID_VENDOR_ID': [0x930],
        'ID_MODEL_ID': [0x1303],
    }

    conntype = WADER_CONNTYPE_EMBEDDED

novateleu740 = NovatelEU740()
