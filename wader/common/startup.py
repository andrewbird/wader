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
import sys

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from dbus.service import Object, BusName, method, signal
gloop = DBusGMainLoop(set_as_default=True)

from twisted.application.service import Application, Service
from twisted.internet import reactor, defer
from twisted.python import log

import wader.common.consts as consts
from wader.common._dbus import DBusExporterHelper
from wader.common.persistent import populate_networks
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
        from wader.common.oal import osobj
        self.hm = osobj.hw_manager
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
        d.addCallback(lambda devs: [d.udi for d in devs])
        return self.add_callbacks(d, async_cb, async_eb)

    @signal(consts.WADER_INTFACE, signature='o')
    def DeviceAdded(self, udi):
        """Emitted when a 3G device is added"""
        log.msg("emitting DeviceAdded('%s')" % udi)

    @signal(consts.WADER_INTFACE, signature='o')
    def DeviceRemoved(self, udi):
        """Emitted when a 3G device is removed"""
        log.msg("emitting DeviceRemoved('%s')" % udi)


def get_wader_application():
    """
    Returns the application object required by twistd on startup

    In the future this will be the point that will load startup plugins
    and modify the application object
    """
    service = WaderService()
    application = Application(consts.APP_NAME)

    # XXX: restore
    #if config.get('plugins/ssh_shell', 'active', False):
    #    from wader.common import shell
    #    # user = config.get('plugins', 'ssh_user')  not used right now
    #    passwd = config.get('plugins/ssh_shell', 'ssh_pass', 'admin')
    #    port = config.get('plugins/ssh_shell', 'ssh_port',
    #                      'tcp:2222:interface=127.0.0.1')
    #    factory = shell.get_manhole_factory(dict(service=service),
    #                                        #admin=passwd)
    #    #strports.service(port, factory).setServiceParent(application)

    service.setServiceParent(application)
    return application

def attach_to_serial_port(device):
    """Attaches the serial port in ``device``"""
    d = defer.Deferred()
    ports = device.ports
    port = ports.cport if ports.has_two() else ports.dport
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
        return

    # regenerate plugin cache
    from twisted.plugin import IPlugin, getPlugins
    import wader.plugins
    list(getPlugins(IPlugin, package=wader.plugins))

    populate_dbs(populate_networks)

def populate_dbs(f):
    """
    Populates the networks database using ``f``

    ``f`` is a callable that accepts a list of NetworkOperators and
    populates the database

    :type f: callable
    """
    try:
        # only will succeed on development
        networks = __import__('resources/extra/networks')
    except ImportError:
        try:
            # this fails on feisty but not on gutsy
            networks = __import__(os.path.join(consts.EXTRA_DIR, 'networks'))
        except ImportError:
            sys.path.insert(0, consts.EXTRA_DIR)
            import networks

    def is_valid(item):
        return not item.startswith(("__", "Base", "NetworkOperator"))

    f([getattr(networks, item)() for item in dir(networks) if is_valid(item)])

