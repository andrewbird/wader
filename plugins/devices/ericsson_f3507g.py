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

from wader.common.consts import WADER_CONNTYPE_EMBEDDED
from core.hardware.ericsson import EricssonDevicePlugin


class EricssonF3507G(EricssonDevicePlugin):
    """:class:`~core.plugin.DevicePlugin} for Ericsson's F3507G"""
    name = "Ericsson F3507G"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = "F3507g"

    __properties__ = {
        'ID_VENDOR_ID': [0x0bdb],
        'ID_MODEL_ID': [0x1900, 0x1902],
    }

    conntype = WADER_CONNTYPE_EMBEDDED

ericssonF3507G = EricssonF3507G()
