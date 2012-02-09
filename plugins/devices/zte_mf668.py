# -*- coding: utf-8 -*-
# Copyright (C) 2007-2012  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

from core.hardware.icera import IceraWCDMADevicePlugin


class ZTEMF668(IceraWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's MF668"""
    name = "ZTE MF668"
    version = "0.1"
    author = "Andrew Bird"

    __remote_name__ = "MF668A"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0017],
    }


zte_mf668 = ZTEMF668()