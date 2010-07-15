# -*- coding: utf-8 -*-
# Copyright (C) 2009-2010  Vodafone España, S.A.
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
from wader.common.command import ATCmd
from wader.common.encoding import pack_ucs2_bytes
from wader.common.hardware.base import build_band_dict
from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper,
                                          HUAWEI_BAND_DICT)


class HuaweiK2540Wrapper(HuaweiWCDMAWrapper):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMAWrapper` for the K2540
    """

    def _add_contact(self, name, number, index):
        """
        Adds a contact to the SIM card
        """
        raw = 0
        try:     # are all ascii chars
            name.encode('ascii')
        except:  # write in TS31.101 type 80 raw format
            # K2540 doesn't need the "FF" suffix
            # AT^CPBW=1,"28780808",129,"80534E4E3A",1
            name = '80%s' % pack_ucs2_bytes(name)
            raw = 1

        category = 145 if number.startswith('+') else 129
        args = (index, number, category, name, raw)
        cmd = ATCmd('AT^CPBW=%d,"%s",%d,"%s",%d' % args, name='add_contact')

        return self.queue_at_cmd(cmd)


class HuaweiK2540Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the K2540
    """
    wrapper_klass = HuaweiK2540Wrapper

    # GSM/GPRS/EDGE 850/900/1800/1900 MHz
    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,#  850
                   consts.MM_NETWORK_BAND_EGSM,#  900
                   consts.MM_NETWORK_BAND_DCS, # 1800
                   consts.MM_NETWORK_BAND_PCS])# 1900

    conn_dict = {}


class HuaweiK2540(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's K2540"""
    name = "Huawei K2540"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiK2540Customizer

    __remote_name__ = "K2540"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1001],
    }
