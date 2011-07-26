# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
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

from twisted.internet import defer
from wader.common import consts
from wader.common.hardware.base import build_band_dict
from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper,
                                          HUAWEI_BAND_DICT)


class HuaweiE173Wrapper(HuaweiWCDMAWrapper):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMAWrapper` for the E173
    """

    def get_manufacturer_name(self):
        """Returns the manufacturer name"""
        # Seems Huawei didn't implement +GMI
        return defer.succeed('Huawei')


class HuaweiE173Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the E173
    """
    wrapper_klass = HuaweiE173Wrapper

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


class HuaweiE173(HuaweiWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for Huawei's E173
    """
    name = "Huawei E173"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiE173Customizer()

    __remote_name__ = "E173"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x14a5],
    }

    def preprobe_init(self, ports, info):
        if info['ID_MODEL_ID'] == 0x1436:
            self.__properties__['ID_MODEL_ID'][0] = 0x1436

huaweie173 = HuaweiE173()
