# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper)


class HuaweiE272Wrapper(HuaweiWCDMAWrapper):

    def send_ussd(self, ussd):
        return self._send_ussd_ucs2_mode(ussd)


class HuaweiE272Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMACustomizer` for the E272
    """
    wrapper_klass = HuaweiE272Wrapper


class HuaweiE272(HuaweiWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Huawei's E272"""
    name = "Huawei E272"
    version = "0.1"
    author = u"Pablo Martí"
    custom = HuaweiE272Customizer()

    __remote_name__ = "E272"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1003],
    }

    conntype = WADER_CONNTYPE_USB
