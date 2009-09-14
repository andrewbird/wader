# -*- coding: utf-8 -*-
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
"""Dialer module that wraps NetworkManager's dialer"""

import dbus

from twisted.python import log
from twisted.internet.defer import Deferred
from wader.common.dialer import Dialer
from wader.common.consts import (NM_SERVICE, NM_INTFACE, NM_OBJPATH,
                                 NM_GSM_INTFACE, NM_USER_SETTINGS,
                                 NM_CONNECTED, NM_DISCONNECTED,
                                 NM_DEVICE, WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH)
from wader.common.runtime import nm08_present

CONNECTED, DISCONNECTED = 1, 2

class NMDialer(Dialer):
    """I wrap NetworkManager's dialer"""
    def __init__(self, device, opath, **kwds):
        super(NMDialer, self).__init__(device, opath, **kwds)

        self.int = None
        self.conn_obj = None
        self.iface = 'ppp0'
        self.state = DISCONNECTED

        self.nm_opath = None
        self.connect_deferred = None
        self.disconnect_deferred = None
        self.sm = None

    def _cleanup(self):
        # enable +CREG notifications afterwards
        self.device.sconn.set_netreg_notification(1)
        self.sm.remove()
        self.sm = None

    def _get_device_opath(self):
        """
        Returns the object path to use in the connection / signal
        """
        if not nm08_present:
            return self.device.udi
        else:
            obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
            interface = dbus.Interface(obj, NM_INTFACE)
            for opath in interface.GetDevices():
                device = self.bus.get_object(NM_SERVICE, opath)
                udi = device.Get(NM_DEVICE, 'Udi',
                                 dbus_interface=dbus.PROPERTIES_IFACE)
                if self.device.udi == udi:
                    return opath

    def _on_properties_changed(self, changed):
        if 'State' not in changed:
            return

        if changed['State'] == NM_CONNECTED and self.state == DISCONNECTED:
            # emit the connected signal and send back the opath
            # if the deferred is present
            self.state = CONNECTED
            self.Connected()
            self.connect_deferred.callback(self.opath)

        if changed['State'] == NM_DISCONNECTED and self.state == CONNECTED:
            if self.state == CONNECTED:
                self.state = DISCONNECTED
                self.Disconnected()
                if self.disconnect_deferred is not None:
                    # could happen if we are connected and a NM_DISCONNECTED
                    # signal arrives without having explicitly disconnected
                    self.disconnect_deferred.callback(self.conn_obj)
                self._cleanup()

    def _setup_signals(self):
        self.sm = self.bus.add_signal_receiver(self._on_properties_changed,
                                               "PropertiesChanged",
                                               path=self._get_device_opath(),
                                               dbus_interface=NM_GSM_INTFACE)

    def configure(self, config):
        self._setup_signals()
        # get the profile object and obtains its uuid
        # get ProfileManager and translate the uuid to a NM object path
        profiles = self.bus.get_object(WADER_PROFILES_SERVICE,
                                       WADER_PROFILES_OBJPATH)
        self.nm_opath = profiles.GetNMObjectPath(str(config.uuid),
                                       dbus_interface=WADER_PROFILES_INTFACE)
        # Disable +CREG notifications, otherwise NMDialer won't work
        return self.device.sconn.set_netreg_notification(0)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)
        args = (NM_USER_SETTINGS, self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s\n%s" % args)
        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()

    def stop(self):
        self._cleanup()
        return self.disconnect()

    def disconnect(self):
        self.disconnect_deferred = Deferred()
        self.int.DeactivateConnection(self.conn_obj)
        # the deferred will be callbacked as soon as we get a
        # connectivity status change
        return self.disconnect_deferred

