# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
# Author:  Pablo Martí
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


class HuaweiK3715Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the K3715
    """

    # GSM/GPRS/EDGE 850/900/1800/1900 MHz
    # HSDPA/UMTS 2100/900 MHz

    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,
                   consts.MM_NETWORK_BAND_EGSM,
                   consts.MM_NETWORK_BAND_DCS,
                   consts.MM_NETWORK_BAND_PCS,

#                   consts.MM_NETWORK_BAND_U900, # waiting for docs
                   consts.MM_NETWORK_BAND_U2100])


class HuaweiK3715(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's K3715"""
    name = "Huawei K3715"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiK3715Customizer()

    __remote_name__ = "K3715"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1001],
    }
