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

from twisted.internet import reactor
from twisted.internet.task import deferLater

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper)


class ZTEK3765Wrapper(ZTEWrapper):

    def check_pin(self):
        """
        Returns the SIM's auth state

        :raise SimPinRequired: Raised if SIM PIN is required
        :raise SimPukRequired: Raised if SIM PUK is required
        :raise SimPuk2Required: Raised if SIM PUK2 is required
        """
        # XXX: this device needs to be enabled before pin can be checked

        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status != 1:
                self.send_at('AT+CFUN=1')

                # delay here 2 secs
                return deferLater(reactor, 2, lambda: None)

        d.addCallback(get_radio_status_cb)
        d.addCallback(lambda x: super(ZTEK3765Wrapper, self).check_pin())

        return d

    def send_ussd(self, ussd):
        """Sends the ussd command ``ussd``"""
        # K3765-Z wants request in ascii chars even though current
        # set might be ucs2
        return super(ZTEK3765Wrapper, self).send_ussd(ussd, force_ascii=True)


class ZTEK3765Customizer(ZTEWCDMACustomizer):
    wrapper_klass = ZTEK3765Wrapper


class ZTEK3765(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's K3765-Z"""
    name = "Vodafone K3765-Z"
    version = "0.1"
    author = "Andrew Bird"
    custom = ZTEK3765Customizer()

    __remote_name__ = "K3765-Z"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x2002],
    }

    conntype = WADER_CONNTYPE_USB

zte_k3765 = ZTEK3765()
