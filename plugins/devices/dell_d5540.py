# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone España, S.A.
# Author: Andrew Bird
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

from wader.common.consts import WADER_CONNTYPE_EMBEDDED
from core.hardware.ericsson import (EricssonDevicePlugin,
                                            EricssonF3607gwCustomizer)


class EricssonD5540(EricssonDevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Ericsson's Dell D5540"""
    name = "Dell D5540"
    version = "0.1"
    author = u"Andrew Bird"
    custom = EricssonF3607gwCustomizer()

    __remote_name__ = "D5540"

    __properties__ = {
        'ID_VENDOR_ID': [0x413c],
        'ID_MODEL_ID': [0x8183, 0x8184],
    }

    conntype = WADER_CONNTYPE_EMBEDDED

ericssonD5540 = EricssonD5540()
