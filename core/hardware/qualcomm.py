# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone España, S.A.
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
"""Common stuff for all Qualcomm's cards"""

from twisted.internet import defer, reactor
from twisted.internet.task import deferLater

from wader.common import consts
from core.command import get_cmd_dict_copy
from core.hardware.base import WCDMACustomizer
from core.middleware import WCDMAWrapper
from core.plugin import DevicePlugin
from core.sim import SIMBaseClass

# Gobi 2000 notes:
#   Unfortunately there is only one tty port available so it has to be
# shared between data and status functions.
#   There also doesn't seem to be any way of specifying the bearer
# preference for 3G only, 3G preferred, or 2G only.

QUALCOMM_CMD_DICT = get_cmd_dict_copy()


class QualcommSIMClass(SIMBaseClass):
    """Qualcomm SIM Class"""

    def __init__(self, sconn):
        super(QualcommSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):

        def init_callback(size):
            # make sure we are in most promiscuous mode before registration
            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            # set SMS storage default
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return(size)

        d = super(QualcommSIMClass, self).initialize(set_encoding)
        d.addCallback(init_callback)
        return d


class QualcommWCDMAWrapper(WCDMAWrapper):
    """Wrapper for all Qualcomm cards"""

    def enable_radio(self, enable):
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                self.send_at('AT+CFUN=1')
                # delay here to give the device chance to wake up
                return deferLater(reactor, 2, lambda: None)

            elif status == 1 and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_band(self):
        """Returns the current used band"""
        return defer.succeed(consts.MM_NETWORK_BAND_ANY)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if band == consts.MM_NETWORK_BAND_ANY:
            return defer.succeed('OK')
        else:
            raise KeyError("Unsupported band %d" % band)

    def get_network_mode(self):
        """Returns the current network mode"""
        return defer.succeed(consts.MM_NETWORK_MODE_ANY)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode == consts.MM_NETWORK_MODE_ANY:
            return defer.succeed('OK')
        else:
            raise KeyError("Unknown network mode %d" % mode)

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode == consts.MM_ALLOWED_MODE_ANY:
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return defer.succeed('OK')
        else:
            raise KeyError("Unknown allowed mode %d" % mode)


class QualcommWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for Qualcomm devices"""
    cmd_dict = QUALCOMM_CMD_DICT
    wrapper_klass = QualcommWCDMAWrapper


class QualcommWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for Qualcomm devices"""
    sim_klass = QualcommSIMClass
    custom = QualcommWCDMACustomizer()
