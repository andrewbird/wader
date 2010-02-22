# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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

from wader.common.hardware.ericsson import EricssonDevicePlugin


class EricssonD5530(EricssonDevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Ericsson's Dell D5530"""
    name = "Dell D5530"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = "D5530"

    __properties__ = {
        'ID_VENDOR_ID': [0x413c],
        'ID_MODEL_ID': [0x8147],
    }

ericssonD5530 = EricssonD5530()
