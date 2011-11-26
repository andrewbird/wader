# -*- coding: utf-8 -*-
# Copyright (C) 2008-2010  Vodafone España, S.A.
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

from wader.common import consts
from core.hardware.base import build_band_dict
from core.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMAWrapper,
                                          HuaweiWCDMACustomizer,
                                          HUAWEI_BAND_DICT)


class HuaweiE1550Wrapper(HuaweiWCDMAWrapper):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMAWrapper` for the E1550
    """

    def send_ussd(self, ussd):
        return self._send_ussd_old_mode(ussd)


class HuaweiE1550Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMACustomizer` for the E1550
    """
    wrapper_klass = HuaweiE1550Wrapper

    # GSM/GPRS/EDGE 850/900/1800/1900 MHz
    # HSDPA/UMTS 900/1900/2100 MHz
    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,#  850
                   consts.MM_NETWORK_BAND_EGSM,#  900
                   consts.MM_NETWORK_BAND_DCS, # 1800
                   consts.MM_NETWORK_BAND_PCS, # 1900

#                   consts.MM_NETWORK_BAND_U900,
                   consts.MM_NETWORK_BAND_U1900,
                   consts.MM_NETWORK_BAND_U2100])


class HuaweiE1550(HuaweiWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Huawei's E1550"""
    name = "Huawei E1550"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiE1550Customizer()

    __remote_name__ = "E1550"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x140c],
    }
