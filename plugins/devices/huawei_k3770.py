# -*- coding: utf-8 -*-
# Copyright (C) 2011 Canonical, Ltd.
# Author:  Alex Chiang
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

from twisted.internet import defer
from wader.common import consts
from wader.common.encoding import unpack_ucs2_bytes, check_if_ucs2
from wader.common.exceptions import MalformedUssdPduError
from wader.common.hardware.base import build_band_dict
from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper,
                                          HUAWEI_BAND_DICT)
from wader.common.middleware import WCDMAWrapper


class HuaweiK3770Wrapper(HuaweiWCDMAWrapper):

    def get_manufacturer_name(self):
        """Returns the manufacturer name"""
        # Seems Huawei didn't implement +GMI
        return defer.succeed('Huawei')

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K3770 want request in ascii chars even though current
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


class HuaweiK3770Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~wader.common.hardware.huawei.HuaweiWCDMACustomizer` for the K3770
    """
    wrapper_klass = HuaweiK3770Wrapper

    # GSM/GPRS/EDGE 850/900/1800/1900 MHz
    # HSDPA/UMTS 2100 MHz

    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,
                   consts.MM_NETWORK_BAND_EGSM,
                   consts.MM_NETWORK_BAND_DCS,
                   consts.MM_NETWORK_BAND_PCS,

                   consts.MM_NETWORK_BAND_U2100])


class HuaweiK3770(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's K3770"""
    name = "Huawei K3770"
    version = "0.1"
    author = u"Alex Chiang"
    custom = HuaweiK3770Customizer()

    __remote_name__ = "K3770"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x14c9],
    }


huaweik3770 = HuaweiK3770()
