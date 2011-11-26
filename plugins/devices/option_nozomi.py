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

from core.hardware.option import OptionWCDMADevicePlugin


class OptionNozomi(OptionWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Option's Nozomi"""
    name = "Option GlobeTrotter 3G+"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = "GlobeTrotter 3G+"

    __properties__ = {
        'ID_VENDOR_ID': [0x1931],
        'ID_MODEL_ID': [0xc],
    }

# device disabled in the udev transition as we couldn't find
# a way to obtain its vendor and product ids cleanly. I'll
# leave it commented in case someone decides to set up and
# make it work.
# option_nozomi = OptionNozomi()
