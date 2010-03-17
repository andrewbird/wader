# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
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
"""Common stuff for all SonyEricsson's cards"""

from wader.common.hardware.base import WCDMACustomizer

SONYERICSSON_ALLOWED_DICT = {}
SONYERICSSON_CONN_DICT = {}
SONYERICSSON_BAND_DICT = {}


class SonyEricssonCustomizer(WCDMACustomizer):
    """WCDMA customizer for sonny ericsson devices"""
    async_regexp = None
    allowed_dict = SONYERICSSON_ALLOWED_DICT
    conn_dict = SONYERICSSON_CONN_DICT
    band_dict = SONYERICSSON_BAND_DICT
