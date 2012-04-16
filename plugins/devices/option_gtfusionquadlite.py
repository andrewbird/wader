# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Stefano Rivera
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

from wader.common.consts import WADER_CONNTYPE_PCMCIA
from core.hardware.option import OptionWCDMADevicePlugin


class OptionGTFusionQuadLite(OptionWCDMADevicePlugin):
    """
    :class:`~core.plugin.DevicePlugin` for Option's GT Fusion Quad Lite
    """
    name = "Option GT Fusion Quad Lite"
    version = "0.1"
    author = "Stefano Rivera"

    __remote_name__ = 'GlobeTrotter Fusion Quad Lite'

    __properties__ = {
        'ID_VENDOR_ID': [0x0af0],
        'ID_MODEL_ID': [0x6300],
    }

    conntype = WADER_CONNTYPE_PCMCIA

optiongtfusionquadlite = OptionGTFusionQuadLite()
