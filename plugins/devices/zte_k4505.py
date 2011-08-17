# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
# Author:  Andrew Bird, inspired by Pablo Martí
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

from wader.common.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper)


class ZTEK4505Wrapper(ZTEWrapper):

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K4505-Z wants request in ascii chars even though current
        # set might be ucs2
        return super(ZTEK4505Wrapper, self).send_ussd(ussd, force_ascii=True)


class ZTEK4505Customizer(ZTEWCDMACustomizer):
    wrapper_klass = ZTEK4505Wrapper


class ZTEK4505(ZTEWCDMADevicePlugin):
    """
    :class:`~wader.common.plugin.DevicePlugin` for ZTE's K4505-Z
    """
    name = "ZTE K4505-Z"
    version = "0.1"
    author = "Andrew Bird"
    custom = ZTEK4505Customizer()

    __remote_name__ = "K4505-Z"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0016, 0x0104],
    }


zte_k4505 = ZTEK4505()
