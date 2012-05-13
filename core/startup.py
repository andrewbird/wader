# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
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
from os.path import join

import dbus
from dbus.service import Object, BusName, method, signal

from twisted.application.service import Application, Service
from twisted.internet import reactor, defer
from twisted.plugin import IPlugin, getPlugins
from twisted.python import log

# Logger related imports.
import glob
import time
from twisted.python import threadable
from twisted.python.log import ILogObserver, FileLogObserver
from twisted.python.logfile import BaseLogFile, LogReader

import wader.common.consts as consts
from wader.common._dbus import DBusExporterHelper
from wader.common.provider import NetworkProvider
from core.serialport import SerialPort

DELAY = 10
ATTACH_DELAY = 1

OLDLOCK = join(consts.DATA_DIR, '.setup-done')

_application = None

# Wow, this is fantastic if you need to know where to add an errorback
#defer.setDebugging(True)


class WaderLogFile(BaseLogFile):
    """
    A log file that can be rotated.

    A rotateLength of None disables automatic log rotation.
    """
    def __init__(self, name, directory, defaultMode=None,
                                                     maxRotatedFiles=None):
        """
        Create a log file rotating on length.

        @param name: file name.
        @type name: C{str}
        @param directory: path of the log file.
        @type directory: C{str}
        @param defaultMode: mode used to create the file.
        @type defaultMode: C{int}
        @param maxRotatedFiles: if not None, max number of log files the class
            creates. Warning: it removes all log files above this number.
        @type maxRotatedFiles: C{int}
        """
        BaseLogFile.__init__(self, name, directory, defaultMode)
        self.maxRotatedFiles = maxRotatedFiles

    def _openFile(self):
        BaseLogFile._openFile(self)
        self.lastDate = self.toDate(os.stat(self.path)[8])

    def toDate(self, *args):
        """Convert a unixtime to (year, month, day) localtime tuple,
        or return the current (year, month, day) localtime tuple.

        This function primarily exists so you may overload it with
        gmtime, or some cruft to make unit testing possible.
        """
        # primarily so this can be unit tested easily
        return time.localtime(*args)[:3]

    def shouldRotate(self):
        """Rotate when the date has changed since last write"""
        return self.toDate() > self.lastDate

    def getLog(self, identifier):
        """
        Given an integer, return a LogReader for an old log file.
        """
        filename = "%s.%d" % (self.path, identifier)
        if not os.path.exists(filename):
            raise ValueError("no such logfile exists")
        return LogReader(filename)

    def write(self, data):
        """
        Write some data to the file.
        """
        BaseLogFile.write(self, data)
        # Guard against a corner case where time.time()
        # could potentially run backwards to yesterday.
        # Primarily due to network time.
        self.lastDate = max(self.lastDate, self.toDate())

    def rotate(self):
        """
        Rotate the file and create a new one.

        If it's not possible to open new logfile, this will fail silently,
        and continue logging to old logfile.
        """
        if not (os.access(self.directory, os.W_OK) and \
                os.access(self.path, os.W_OK)):
            return
        logs = self.listLogs()
        logs.reverse()
        for i in logs:
            if self.maxRotatedFiles is not None and i >= self.maxRotatedFiles:
                os.remove("%s.%d" % (self.path, i))
            else:
                os.rename("%s.%d" % (self.path, i),
                                                "%s.%d" % (self.path, i + 1))
        self._file.close()
        os.rename(self.path, "%s.1" % self.path)
        self._openFile()

    def listLogs(self):
        """
        Return sorted list of integers - the old logs' identifiers.
        """
        result = []
        for name in glob.glob("%s.*" % self.path):
            try:
                counter = int(name.split('.')[-1])
                if counter:
                    result.append(counter)
            except ValueError:
                pass
        result.sort()
        return result

    def __getstate__(self):
        state = BaseLogFile.__getstate__(self)
        del state["lastDate"]
        return state

threadable.synchronize(WaderLogFile)


def _get_application():
    """
    Factory function that returns an Application object.
    If the object does not exist then it creates a new Application object.
    (Internal use only).
    """
    global _application
    if _application is not None:
        return _application

    _application = Application(consts.APP_NAME)
    logfile = WaderLogFile(consts.LOG_NAME, consts.LOG_DIR,
                                            maxRotatedFiles=consts.LOG_NUMBER)
    _application.setComponent(ILogObserver, FileLogObserver(logfile).emit)
    return _application


def create_skeleton_and_do_initial_setup():
    """I perform the operations needed for the initial user setup"""
    PLUGINS = join(consts.BASE_DIR, 'usr', 'share', consts.APP_SLUG_NAME,
                    'plugins')

    if os.path.exists(OLDLOCK):
        # old way to signal that the setup is complete
        os.unlink(OLDLOCK)

    # maybe create new networks DB
    provider = NetworkProvider()
    try:
        if provider.is_current():
            log.msg("Networks DB is current")
        else:
            log.msg("Networks DB creation started")
            provider.populate_networks()
            log.msg("Networks DB population complete")
    except Exception, e:
        log.err(str(e))
    finally:
        provider.close()

    # maybe regenerate plugin cache
    regenerate = False

    # remove any compiled python files that are orphans
    for cmpname in glob.glob(join(PLUGINS, '*.py[co]')):
        pyname = cmpname[:-1]
        if not os.path.exists(pyname):
            regenerate = True
            os.unlink(cmpname)

    # check if any python is newer than the cache
    if not regenerate:
        try:
            timestamp = os.stat(join(PLUGINS, 'dropin.cache'))[8]
            for pyname in glob.glob(join(PLUGINS, '*.py')) + \
                            glob.glob(join(PLUGINS, '*.py[co]')):
                if timestamp < os.stat(pyname)[8]:
                    raise ValueError
        except:
                regenerate = True

    if regenerate:
        log.msg("Plugin cache generation started")
        import plugins
        list(getPlugins(IPlugin, package=plugins))
        log.msg("Plugin cache generation complete")
    else:
        log.msg("Plugin cache is current")


class WaderService(Service):
    """I am a Twisted service that starts up Wader"""

    def __init__(self):
        self.ctrl = None
        self.prof = None
        self.dial = None

    def startService(self):
        """Starts the Wader service"""
        log.msg("%s (%s) started" % (consts.APP_NAME, consts.APP_VERSION))

        create_skeleton_and_do_initial_setup()

        # check if we have an OSPlugin for this OS/Distro
        from core.oal import get_os_object
        if get_os_object() is None:
            message = 'OS/Distro not registered'
            details = """
The OS/Distro under which you are running %s is not
registered in the OS database. Check the documentation
for what you can do in order to support your OS/Distro
""" % consts.APP_NAME
            raise SystemExit("%s\n%s" % (message, details))

        from core.dialer import DialerManager
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
        name = BusName(consts.WADER_SERVICE, bus=dbus.SystemBus())
        super(StartupController, self).__init__(bus_name=name,
                                        object_path=consts.WADER_OBJPATH)
        from core.oal import get_os_object
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
    application = _get_application()
    service.setServiceParent(application)
    return application


def attach_to_serial_port(device):
    """Attaches the serial port in ``device``"""
    port = device.ports.get_application_port()
    if port.obj is not None:
        return defer.succeed(device)

    d = defer.Deferred()
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
