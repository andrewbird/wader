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

from wader.common.hardware.ericsson import (EricssonDevicePlugin,
                                            EricssonF3607gwCustomizer)

#
# Note F3307 is a F3607gw without GPS and only 2 bands - same firmware
#
class EricssonF3307(EricssonDevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Ericsson's F3307"""
    name = "Ericsson F3307"
    version = "0.1"
    author = u"Andrew Bird"
    custom = EricssonF3607gwCustomizer()

    __remote_name__ = "F3307"

    __properties__ = {
        'ID_VENDOR_ID': [0x0bdb],
        'ID_MODEL_ID': [0x1909, 0x190a],
    }


ericssonF3307 = EricssonF3307()
