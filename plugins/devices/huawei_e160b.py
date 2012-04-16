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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.huawei import HuaweiWCDMADevicePlugin


class HuaweiE160B(HuaweiWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Huawei's E160B"""
    name = "Huawei E160B"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = "E160B"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1001, 0x1003],
    }

    conntype = WADER_CONNTYPE_USB
