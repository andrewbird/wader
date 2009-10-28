# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
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

import serial

from wader.common.hardware.novatel import NovatelWCDMADevicePlugin


class NovatelMiFi2352(NovatelWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for Novatel's MiFi 2352
    """
    name = "Novatel MiFi2352"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = "MiFi2352 "

    __properties__ = {
        'usb_device.vendor_id' : [0x1410],
        'usb_device.product_id' : [0x7003],
    }

    def preprobe_init(self, ports, info):
        # This device might be found by means of the mother plugin too
        if info['usb_device.product_id'] == 0x7001:
            self.__properties__['usb_device.product_id'][0] = 0x7001

        # Novatel secondary port needs to be flipped from DM to AT mode
        # before it will answer our AT queries. So the primary port
        # needs this string first or auto detection of ctrl port fails.
        # Note: Early models/firmware were DM only
        ser = serial.Serial(ports[0], timeout=1)
        ser.write('AT$NWDMAT=1\r\n')
        ser.close()

novatelmifi2352 = NovatelMiFi2352()
