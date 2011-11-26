# -*- coding: utf-8 -*-
# Copyright (C) 2011       Vodafone España, S.A.
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

from core.hardware.zte import ZTEWCDMADevicePlugin

from plugins.zte_mf637u import ZTEMF637U


class ZTEMother0031(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's PID 0x031 Family"""
    name = "ZTE Mother 0x0031"
    version = "0.1"
    author = u"Andrew Bird"

    __remote_name__ = None

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0031],
    }

    def __init__(self):
        super(ZTEMother0031, self).__init__()

        self.mapping = {
            'MF620': ZTEMF637U,  # Just MF637U now but usb-modeswitch-data suggests
                                 # that M110 / MF112 are candidates also

            'default': ZTEMF637U,
        }

zte_mother0031 = ZTEMother0031()
