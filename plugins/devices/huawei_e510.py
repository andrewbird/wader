# -*- coding: utf-8 -*-
# Copyright (C) 2006-2010  Vodafone España, S.A.
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

from wader.common import consts
from wader.common.hardware.base import build_band_dict
from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HUAWEI_BAND_DICT)


class HuaweiE510Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the E510
    """

    # GSM/GPRS/EDGE 900/1800/1900 MHz
    # HSDPA/UMTS 2100/900 MHz
    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_EGSM,#  900
                   consts.MM_NETWORK_BAND_DCS, # 1800
                   consts.MM_NETWORK_BAND_PCS, # 1900

# XXX: const needs to be enabled in family first
#                   consts.MM_NETWORK_BAND_U900,
                   consts.MM_NETWORK_BAND_U2100])


class HuaweiE510(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's E510"""
    name = "Huawei E510"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiE510Customizer()

    __remote_name__ = "E510"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1411],
    }

    def preprobe_init(self, ports, info):
        # This device might be found by means of the mother plugin too
        if info['ID_MODEL_ID'] == 0x1001:
            self.__properties__['ID_MODEL_ID'][0] = 0x1001


huaweie510 = HuaweiE510()
