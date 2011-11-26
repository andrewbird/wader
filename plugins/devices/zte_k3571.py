# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
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

from core.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper)


class ZTEK3571Wrapper(ZTEWrapper):

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K3570-Z / K3571-Z want requests in ASCII chars even though the
        # current character set might be UCS2. Some versions of firmware
        # reply in UCS2 or ASCII at different times, so we need a loose check
        return super(ZTEK3571Wrapper, self).send_ussd(ussd, force_ascii=True,
                                                    loose_charset_check=True)


class ZTEK3571Customizer(ZTEWCDMACustomizer):
    wrapper_klass = ZTEK3571Wrapper


class ZTEK3571(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's K3571-Z"""
    name = "Vodafone K3571-Z"
    version = "0.1"
    author = "Andrew Bird"
    custom = ZTEK3571Customizer()

    __remote_name__ = "K3571-Z"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x1010],
    }


zte_k3571 = ZTEK3571()
