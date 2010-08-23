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
"""Utilities used at startup"""

import os

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from dbus.service import Object, BusName, method, signal
gloop = DBusGMainLoop(set_as_default=True)

from twisted.application.service import Application, Service
from twisted.internet import reactor, defer
from twisted.plugin import IPlugin, getPlugins
from twisted.python import log

import wader.common.consts as consts
from wader.common._dbus import DBusExporterHelper
from wader.common.provider import NetworkProvider, nick_debug
from wader.common.serialport import SerialPort

DELAY = 10
ATTACH_DELAY = 1

OLDLOCK = os.path.join(consts.DATA_DIR, '.setup-done')


class WaderService(Service):
    """I am a Twisted service that starts up Wader"""

    def __init__(self):
        self.ctrl = None
        self.prof = None
        self.dial = None

    def startService(self):
        """Starts the Wader service"""
        from wader.common.dialer import DialerManager
        self.ctrl = StartupController()
        self.dial = DialerManager(self.ctrl)

    def get_clients(self):
        """
        Helper method for SSH sessions

        :rtype: dict
        """
        return self.ctrl.hm.clients


class StartupController(Object, DBusExporterHelper):
    """
    I manage devices in the system

    Discovery, identification, hotplugging, etc.

    :ivar clients: Dict with a reference to every configured device
    """

    def __init__(self):
        name = BusName(consts.WADER_SERVICE,
                       bus=dbus.SystemBus(mainloop=gloop))
        super(StartupController, self).__init__(bus_name=name,
                                        object_path=consts.WADER_OBJPATH)
        from wader.common.oal import get_os_object
        self.hm = get_os_object().hw_manager
        assert self.hm is not None, "Running Wader on an unsupported OS?"
        self.hm.register_controller(self)

    @method(consts.WADER_INTFACE, in_signature='', out_signature='ao',
            async_callbacks=('async_cb', 'async_eb'))
    def EnumerateDevices(self, async_cb, async_eb):
        """
        Returns a list of object paths with all the found devices

        It also includes the object paths of already handled devices
        """
        d = self.hm.get_devices()
        d.addCallback(lambda devs: [d.opath for d in devs])
        return self.add_callbacks(d, async_cb, async_eb)

    @signal(consts.WADER_INTFACE, signature='o')
    def DeviceAdded(self, opath):
        """Emitted when a 3G device is added"""
        log.msg("emitting DeviceAdded('%s')" % opath)

    @signal(consts.WADER_INTFACE, signature='o')
    def DeviceRemoved(self, opath):
        """Emitted when a 3G device is removed"""
        log.msg("emitting DeviceRemoved('%s')" % opath)


def get_wader_application():
    """
    Returns the application object required by twistd on startup

    In the future this will be the point that will load startup plugins
    and modify the application object
    """
    service = WaderService()
    application = Application(consts.APP_NAME)
    service.setServiceParent(application)
    return application


def attach_to_serial_port(device):
    """Attaches the serial port in ``device``"""
    d = defer.Deferred()
    port = device.ports.get_application_port()
    port.obj = SerialPort(device.sconn, port.path, reactor,
                          baudrate=device.baudrate)
    reactor.callLater(ATTACH_DELAY, lambda: d.callback(device))
    return d


def setup_and_export_device(device):
    """Sets up ``device`` and exports its methods over DBus"""
    if not device.custom.wrapper_klass:
        raise AttributeError("No wrapper class for device %s" % device)

    wrapper_klass = device.custom.wrapper_klass

    log.msg("wrapping plugin %s with class %s" % (device, wrapper_klass))
    device.sconn = wrapper_klass(device)

    # Use the exporter that device specifies
    if not device.custom.exporter_klass:
        raise AttributeError("No exporter class for device %s" % device)

    exporter_klass = device.custom.exporter_klass

    log.msg("exporting %s methods with class %s" % (device, exporter_klass))
    exporter = exporter_klass(device)
    device.exporter = exporter

    device.__repr__ = device.__str__
    return device


def create_skeleton_and_do_initial_setup():
    """I perform the operations needed for the initial user setup"""
    if os.path.exists(OLDLOCK):
        # old way to signal that the setup is complete
        os.unlink(OLDLOCK)

    if os.path.exists(consts.NETWORKS_DB):
        # new way to signal that the setup is complete
        provider = NetworkProvider()
        log.msg("startup.py - create_skeleton_and_do_initial_setup - Network.db exists and provider is:" + repr(provider) + "\n")
        nick_debug("startup.py - create_skeleton_and_do_initial_setup - Network.db exists and provider is: " + repr(provider))

        if provider.is_current():
            provider.close()
            log.msg("Networks DB was built from current sources")
            nick_debug("Networks DB was built from current sources")
            return

        provider.close()
        log.msg("Networks DB requires rebuild")
        nick_debug("startup.py - create_skeleton_and_do_initial_setup: Networks DB requires rebuild")
        os.remove(consts.NETWORKS_DB)

    # regenerate plugin cache
    import wader.plugins
    list(getPlugins(IPlugin, package=wader.plugins))

    # create new DB
    provider = NetworkProvider()
    try:
        nick_debug("startup.py - create_skeleton_and_do_initial_setup - create new DB and provider is the object:" +  repr(provider))
        provider.populate_networks()
        nick_debug("startup.py - create_skeleton_and_do_initial_setup - populate_networks complete.")

    except:
        log.err()
    finally:
        provider.close()
