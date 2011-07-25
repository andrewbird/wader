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


from wader.common.encoding import unpack_ucs2_bytes, check_if_ucs2
from wader.common.exceptions import MalformedUssdPduError
from wader.common.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper)
from wader.common.middleware import WCDMAWrapper


class ZTEK4505Wrapper(ZTEWrapper):

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K4505-Z wants request in ascii chars even though current
        # set might be ucs2

        def convert_response(response):
            resp = response[0].group('resp')
            if 'UCS2' in self.device.sim.charset:
                if check_if_ucs2(resp):
                    try:
                        return unpack_ucs2_bytes(resp)
                    except (TypeError, UnicodeDecodeError):
                        raise MalformedUssdPduError(resp)

                raise MalformedUssdPduError(resp)

            return resp

        d = super(WCDMAWrapper, self).send_ussd(str(ussd))
        d.addCallback(convert_response)
        return d


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
