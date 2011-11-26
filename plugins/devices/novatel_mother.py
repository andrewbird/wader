# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
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

from core.hardware.novatel import NovatelWCDMADevicePlugin

from plugins.novatel_mc990d import NovatelMC990D
from plugins.novatel_mifi2352 import NovatelMiFi2352


class NovatelMother(NovatelWCDMADevicePlugin):
    """
    :class:`~core.plugin.DevicePlugin` Novatel's Ovation/MiFi
    devices that share a common PID
    """
    name = "Novatel Mother"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x1410],
        'ID_MODEL_ID': [0x7001],
    }

    def __init__(self):
        super(NovatelMother, self).__init__()

        self.mapping = {
            'Ovation MC990D Card': NovatelMC990D,
            'MiFi2352 ': NovatelMiFi2352,

            'default': NovatelMiFi2352,
        }

novatelmother = NovatelMother()
