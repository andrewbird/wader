# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

from wader.common.hardware.zte import ZTEWCDMADevicePlugin

class ONDAMSA405HS(ZTEWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for ONDA's MSA405HS"""
    name = "ONDA MSA405HS"
    version = "0.1"
    author = "Igor Moura"

    __remote_name__ = "MSA405"

    __properties__ = {
        'usb_device.vendor_id': [0x19d2],
        'usb_device.product_id': [0x0037],
    }

    # Onda MSA405HS uses ttyUSB2(data) and ttyUSB1(status)
    hardcoded_ports = (2, 1)

onda_msa405hs = ONDAMSA405HS()
