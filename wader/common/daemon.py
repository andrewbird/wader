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
"""Daemons for Wader"""

try:
    from glib import timeout_add_seconds, source_remove
except ImportError:
    from gobject import timeout_add_seconds, source_remove

from twisted.python import log

from wader.common.utils import rssi_to_percentage
import wader.common.signals as S

SIG_REG_INFO_FREQ = 120
SIG_RSSI_FREQ = 15

class WaderDaemon(object):
    """
    I represent a Daemon in Wader

    A Daemon is an entity that performs a repetitive action, like polling
    signal quality from the data card. A Daemon will emit DBus signals as
    if the device itself had emitted them.
    """
    def __init__(self, frequency, device):
        super(WaderDaemon, self).__init__()
        self.frequency = frequency
        self.device = device
        self.task_id = None

    def __repr__(self):
        return self.__class__.__name__

    def start(self):
        """Starts the Daemon"""
        log.msg("daemon %s started..." % self)
        if self.task_id is None:
            self.task_id = timeout_add_seconds(self.frequency, self.function)

            args = (self, 'function', self.frequency)
            log.msg("executing %s.%s every %d seconds" % args)


    def stop(self):
        """Stops the Daemon"""
        if self.task_id is not None:
            source_remove(self.task_id)

            self.task_id = None
            log.msg("daemon %s stopped..." % self)

    def function(self):
        """
        Function that will be called periodically

        It *always* needs to return True, otherwise it will be
        executed just once
        """
        raise NotImplementedError()


class SignalQualityDaemon(WaderDaemon):
    """I emit SIG_RSSI UnsolicitedNotifications"""

    def function(self):
        """Executes `get_signal_quality` periodically"""
        d = self.device.sconn.get_signal_quality()
        d.addCallback(rssi_to_percentage)
        d.addCallback(lambda rssi: self.device.exporter.SignalQuality(rssi))

        return True


class NetworkRegistrationDaemon(WaderDaemon):
    """
    I monitor several network registration parameters

    I cache, compare and emit if different from previous reading
    """

    def __init__(self, frequency, device):
        super(NetworkRegistrationDaemon, self).__init__(frequency, device)
        self.reading = None

    def function(self):
        d = self.device.sconn.get_netreg_info()
        d.addCallback(self.compare_and_emit_if_different)

        return True

    def compare_and_emit_if_different(self, info):
        """
        Compares ``info`` with previously cached value

        If they are different it will emit `RegistrationInfo` signal
        """
        if not self.reading:
            self.reading = info
        else:
            if self.reading == info:
                # nothing has changed
                return

        self.device.exporter.RegistrationInfo(*info)


class WaderDaemonCollection(object):
    """
    I am a collection of Daemons

    I provide some methods to manage the collection.
    """
    def __init__(self):
        self.daemons = {}
        self.running = False

    def append_daemon(self, name, daemon):
        """Adds ``daemon`` to the collection identified by ``name``"""
        self.daemons[name] = daemon

    def has_daemon(self, name):
        """Returns True if daemon ``name`` exists"""
        return name in self.daemons

    def remove_daemon(self, name):
        """Removes daemon with ``name``"""
        del self.daemons[name]

    def start_daemons(self, arg=None):
        """Starts all daemons"""
        for daemon in self.daemons.values():
            daemon.start()

        self.running = True

    def stop_daemon(self, name):
        """Stops daemon identified by ``name``"""
        try:
            self.daemons[name].stop()
        except KeyError:
            raise

    def stop_daemons(self):
        """Stops all daemons"""
        for daemon in self.daemons.values():
            daemon.stop()

        self.running = False


def build_daemon_collection(device):
    """Returns a :class:`WaderServiceCollection` customized for ``device``"""
    collection = WaderDaemonCollection()

    if device.ports.has_two():
        # check capabilities
        if S.SIG_RSSI not in device.custom.device_capabilities:
            # device doesn't sends unsolicited notifications about RSSI
            # changes, we will have to monitor it ourselves every 15s
            daemon = SignalQualityDaemon(SIG_RSSI_FREQ, device)
            collection.append_daemon(S.SIG_RSSI, daemon)

    else:
        # device with just one port will never be able to send us
        # unsolicited notifications, we'll have to fake 'em
        daemon = SignalQualityDaemon(SIG_RSSI_FREQ, device)
        collection.append_daemon(S.SIG_RSSI, daemon)

    # daemons to be used regardless of ports or capabilities
    daemon = NetworkRegistrationDaemon(SIG_REG_INFO_FREQ, device)
    collection.append_daemon(S.SIG_REG_INFO, daemon)

    return collection

