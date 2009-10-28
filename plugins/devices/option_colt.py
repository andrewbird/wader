# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Pablo Martí
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
"""
DevicePlugin for Option Colt

(end of life reached)
"""

from twisted.python import log
from epsilon.modal import mode

from wader.common.hardware.option import (OptionWCDMADevicePlugin,
                                        OptionWCDMACustomizer)
from wader.common.sim import SIMBaseClass
from wader.common.statem.auth import AuthStateMachine


class OptionColtAuthStateMachine(AuthStateMachine):
    """
    Custom AuthStateMachine for Option Colt

    This device has a rather buggy firmware that yields all sort of
    weird errors. For example, if PIN authentication is disabled on the SIM
    and you issue an AT+CPIN? command, it will reply with a +CPIN: SIM PUK2
    """
    pin_needed_status = AuthStateMachine.pin_needed_status
    puk_needed_status = AuthStateMachine.puk_needed_status
    puk2_needed_status = AuthStateMachine.puk2_needed_status

    class get_pin_status(mode):
        """
        Returns the authentication status

        The SIM can be in one of the following states:

        - SIM is ready (already authenticated, or PIN disabled)
        - PIN is needed
        - PIN2 is needed (not handled)
        - PUK is needed
        - PUK2 is needed
        - SIM is not inserted
        - SIM's firmware error
        """

        def __enter__(self):
            pass

        def __exit__(self):
            pass

        def do_next(self):
            log.msg("Instantiating get_pin_status mode....")
            d = self.device.sconn.get_pin_status()
            d.addCallback(self.get_pin_status_cb)
            d.addErrback(self.sim_failure_eb)
            d.addErrback(self.sim_busy_eb)
            d.addErrback(self.sim_no_present_eb)
            d.addErrback(log.err)


class OptionColtSIMClass(SIMBaseClass):
    """Option Colt SIM Class"""

    def __init__(self, sconn):
        super(OptionColtSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=False):
        self.charset = 'IRA'
        d = super(OptionColtSIMClass, self).initialize(set_encoding)
        d.addCallback(self.set_size)
        return d


class OptionColtCustomizer(OptionWCDMACustomizer):
    """:class:`~wader.common.hardware.Customizer` for Option Colt"""
    auth_klass = OptionColtAuthStateMachine


class OptionColt(OptionWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Option Colt"""
    name = "Option Colt"
    version = "0.1"
    author = u"Pablo Martí"
    custom = OptionColtCustomizer()
    sim_klass = OptionColtSIMClass

    __remote_name__ = "129"

    __properties__ = {
        'usb_device.vendor_id' : [0x0af0],
        'usb_device.product_id' : [0x5000],
    }


optioncolt = OptionColt()
