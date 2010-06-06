# -*- coding: utf-8 -*-
# Copyright (C) 2006-2010  Vodafone España, S.A.
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

from wader.common.encoding import unpack_ucs2_bytes, check_if_ucs2
import wader.common.exceptions as E
from wader.common.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper)
from wader.common.middleware import WCDMAWrapper


class ZTEK3570Wrapper(ZTEWrapper):

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K3570-Z / K3571-Z want request in ascii chars even though current
        # set might be ucs2

        def convert_response(response):
            resp = response[0].group('resp')
            if 'UCS2' in self.device.sim.charset:
                if check_if_ucs2(resp):
                    try:
                        return unpack_ucs2_bytes(resp)
                    except (TypeError, UnicodeDecodeError):
                        raise E.MalformedUssdPduError(resp)

                raise E.MalformedUssdPduError(resp)

            return resp

        d = super(WCDMAWrapper, self).send_ussd(str(ussd))
        d.addCallback(convert_response)
        return d


class ZTEK3570Customizer(ZTEWCDMACustomizer):
    wrapper_klass = ZTEK3570Wrapper


class ZTEK3570(ZTEWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for ZTE's K3570-Z"""
    name = "Vodafone K3570-Z"
    version = "0.1"
    author = "Andrew Bird"
    custom = ZTEK3570Customizer()

    __remote_name__ = "K3570-Z"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x1008],
    }


zte_k3570 = ZTEK3570()
