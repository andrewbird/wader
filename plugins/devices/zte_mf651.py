# -*- coding: utf-8 -*-
# Copyright (C) 2007-2009  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

from wader.common.hardware.icera import IceraWCDMADevicePlugin


class ZTEMF651(IceraWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for ZTE's MF651"""
    name = "ZTE MF651"
    version = "0.1"
    author = "Andrew Bird"

    __remote_name__ = "HSDPA mobile station"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0116],
    }

#    def preprobe_init(self, ports, info):
#        if info['ID_MODEL_ID'] == 0x0016:
#            self.hardcoded_ports = (2, 1)
#        elif info['ID_MODEL_ID'] == 0x0104:
#            self.hardcoded_ports = (3, 1)
#        else: # let probing occur
#            log.msg("Unknown K4505-Z product ID, falling through to probing")


zte_mf651 = ZTEMF651()
