# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMAWrapper,
                                          HuaweiWCDMACustomizer,
                                          HUAWEI_BAND_DICT)
from wader.common.hardware.base import build_band_dict
from wader.common import consts


class HuaweiK3520Wrapper(HuaweiWCDMAWrapper):

    def list_contacts(self):

        def list_contacts_cb(contacts):
            d = self.set_charset("UCS2")
            d.addCallback(lambda _: contacts)
            return d

        d = self.set_charset("IRA")
        d.addCallback(lambda ign:
                super(HuaweiK3520Wrapper, self).list_contacts())
        d.addCallback(list_contacts_cb)
        return d

    def find_contacts(self, pattern):
        d = self.list_contacts()
        d.addCallback(lambda contacts: [c for c in contacts
                            if c.name.lower().startswith(pattern.lower())])
        return d


class HuaweiK3520Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the K3520
    """
    wrapper_klass = HuaweiK3520Wrapper

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


class HuaweiK3520(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's K3520"""
    name = "Huawei K3520"
    version = "0.1"
    author = u"Pablo Martí"
    custom = HuaweiK3520Customizer()

    __remote_name__ = "K3520"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1001],
    }
