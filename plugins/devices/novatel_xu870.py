# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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
from core.hardware.novatel import (NovatelWCDMADevicePlugin,
                                           NovatelWCDMACustomizer,
                                           NOVATEL_BAND_DICT)
from core.hardware.base import build_band_dict


class NovatelXU870Customizer(NovatelWCDMACustomizer):
    """
    :class:`~core.hardware.novatel.NovatelWCDMACustomizer` for XU870
    """

    # Supported bands (from Novatel docs)
    # GSM/GPRS
    #    GSM 850             824 -894MHz
    #    EGSM 900            880-960MHz
    #    DCS 1800            1710-1880MHz
    #    PCS 1900            1850-1990MHz
    # WCDMA
    #    UMTS 850 (Band V)   824 -894MHz
    #    UMTS 1900 (Band II) 1850-1990MHz
    #    UMTS 2100 (Band I)  1920-2170MHz

    band_dict = build_band_dict(
                  NOVATEL_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,
                   consts.MM_NETWORK_BAND_EGSM,
                   consts.MM_NETWORK_BAND_DCS,
                   consts.MM_NETWORK_BAND_PCS,

                   consts.MM_NETWORK_BAND_U850,
                   # XXX: Novatel docs show UMTS 1900 (Band II)
                   # but consts.py has this as UMTS 1900 Class IX
                   consts.MM_NETWORK_BAND_U1900,
                   consts.MM_NETWORK_BAND_U2100])


class NovatelXU870(NovatelWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Novatel's XU870"""
    name = "Novatel XU870"
    version = "0.1"
    author = u"Pablo Martí"
    custom = NovatelXU870Customizer()

    __remote_name__ = "Merlin XU870 ExpressCard"

    __properties__ = {
        'ID_VENDOR_ID': [0x1410],
        'ID_MODEL_ID': [0x1430],
    }

    conntype = consts.WADER_CONNTYPE_PCMCIA

    def preprobe_init(self, ports, info):
        # Novatel secondary port needs to be flipped from DM to AT mode
        # before it will answer our AT queries. So the primary port
        # needs this string first or auto detection of ctrl port fails.
        # Note: Early models/firmware were DM only
        ser = serial.Serial(ports[0], timeout=1)
        ser.write('AT$NWDMAT=1\r\n')
        ser.close()

novatelxu870 = NovatelXU870()
