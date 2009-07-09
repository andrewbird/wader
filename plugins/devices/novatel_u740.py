# -*- coding: utf-8 -*-
# Author:  Adam King - heavily based on Pablo Marti's U630 plugin
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

from wader.common.hardware.novatel import NovatelWCDMADevicePlugin

class NovatelU740(NovatelWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Novatel's U740"""
    name = "Novatel U740"
    version = "0.1"
    author = "Adam King"

    __remote_name__ = "Merlin U740 (HW REV [0:33])"

    __properties__ = {
        'usb_device.vendor_id' : [0x1410],
        'usb_device.product_id' : [0x1400, 0x1410]
    }

novatelu740 = NovatelU740()
