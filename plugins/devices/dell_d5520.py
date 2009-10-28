# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author: Pablo Martí
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

from wader.common import consts
from wader.common.hardware.base import build_band_dict
from wader.common.hardware.novatel import (NovatelWCDMADevicePlugin,
                                           NovatelWCDMACustomizer,
                                           NOVATEL_BAND_DICT)


class NovatelD5520Customizer(NovatelWCDMACustomizer):
    """
    :class:`~wader.common.hardware.novatel.NovatelWCDMACustomizer` for D5520
    """
    # Quad-Band 850/900/1800/1900 MHz GPRS/EDGE
    # Tri-Band 850/1900/2100 MHz HSUPA/HSDPA/UMTS

    band_dict = build_band_dict(
                  NOVATEL_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,
                   consts.MM_NETWORK_BAND_EGSM,
                   consts.MM_NETWORK_BAND_DCS,
                   consts.MM_NETWORK_BAND_PCS,

                   consts.MM_NETWORK_BAND_U850,
                   consts.MM_NETWORK_BAND_U1900,
                   consts.MM_NETWORK_BAND_U2100])


class NovatelD5520(NovatelWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Novatel's Dell D5520"""
    name = "Dell D5520"
    version = "0.1"
    author = u"Pablo Martí"
    custom = NovatelD5520Customizer()

    __remote_name__ = "Expedite EU870D MiniCard"

    __properties__ = {
        'usb_device.vendor_id' : [0x413c],
        'usb_device.product_id' : [0x8137],
    }

    def preprobe_init(self, ports, info):
        # Novatel secondary port needs to be flipped from DM to AT mode
        # before it will answer our AT queries. So the primary port
        # needs this string first or auto detection of ctrl port fails.
        # Note: Early models/firmware were DM only
        ser = serial.Serial(ports[0], timeout=1)
        ser.write('AT$NWDMAT=1\r\n')
        ser.close()

novateld5520 = NovatelD5520()
