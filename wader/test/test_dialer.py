# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Authors:  Pablo Martí­, Isaac Clerencia
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
"""Unittests for the dialer module"""

import re

import dbus.mainloop.glib
gloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

from twisted.trial import unittest
from twisted.python import log
from twisted.internet import defer, utils

from wader.common.oal import osobj
from wader.common.startup import attach_to_serial_port
import wader.common.consts as consts
from wader.contrib import ifconfig

from wader.gtk.profiles import manager

class TestDialer(unittest.TestCase):
    """Test for dialer module"""

    def setUp(self):
        bus = dbus.SystemBus()
        self.profile_manager = manager
        self.dial_manager = bus.get_object(consts.WADER_DIALUP_SERVICE,
                                           consts.WADER_DIALUP_OBJECT)
        self.sconn = None
        self.profile = None
        self.dial_path = None
        try:
            d = osobj.hw_manager.get_devices()
            def get_device_cb(devices):
                self.device = attach_to_serial_port(devices[0])
                self.sconn = self.device.sconn
                d2 = self.device.initialize()
                d2.addCallback(self.set_profile_from_imsi)
                return d2

            d.addCallback(get_device_cb)
            return d
        except:
            log.err()

    def tearDown(self):
        if self.dial_path:
            #deactivate connection on teardown if dial_path is set
            self.dial_manager.DeactivateConnection(self.dial_path,
                    dbus_interface=consts.WADER_DIALUP_INTFACE)

        self.profile_manager.remove_profile(self.profile)

        del self.profile_manager
        return self.device.close()

    def set_profile_from_imsi(self, ignored):
        def set_it(imsi):
            imsi = imsi[:5]
            log.msg('Setting profile from IMSI')
            profile = self.profile_manager.get_profile_options_from_imsi(imsi)
            self.profile = profile
            return self.profile

        d = self.sconn.get_imsi()
        d.addCallback(set_it)
        return d

    def test_connection(self):
        """
        Checks that connecting with the device works
        """
        d = defer.Deferred()

        def _on_connect_cb(dial_path):
            log.msg("Dial path: %s" % dial_path)
            self.dial_path = dial_path
            #check if iface ppp0 is up
            # (hardcoded for now, improve wvdial wrapper to detect this)
            iface = ifconfig.ifconfig('ppp0')
            try:
                self.assertTrue(iface.has_key('raddr'))
            except:
                d.errback()

            def _process_ping_output(output):
                m = re.search('([0-9]+) packets transmitted, '
                              '([0-9]+) received', output)
                try:
                    self.assertTrue(m)
                except:
                    d.errback()

                tx = int(m.group(1))
                rx = int(m.group(2))
                log.msg('%d packets tx, %d packets rx' % (tx, rx))
                try:
                    self.assertTrue(rx > 0)
                except:
                    d.errback()

            def _deactivate_connection(ignored):
                log.msg("Trying to disconnect")
                self.dial_manager.DeactivateConnection(self.dial_path,
                    dbus_interface=consts.WADER_DIALUP_INTFACE,
                    reply_handler=_on_disconnect_cb,
                    error_handler=_on_disconnect_eb)
                self.dial_path = None

            d2 = utils.getProcessOutput('ping',
                                ('-c', '5', '-W', '3', 'www.google.com'))
            d2.addCallback(_process_ping_output)
            d2.addCallback(_deactivate_connection)
            d2.addErrback(lambda ign: d.errback())

        def _on_disconnect_cb():
            #check if iface ppp0 is down
            # (hardcoded for now, improve wvdial wrapper to detect this)
            iface = ifconfig.ifconfig('ppp0')
            try:
                self.assertTrue(not iface.has_key('raddr'))
            except:
                d.errback()

            log.msg("Disconnected correctly")

            d.callback(True)

        def _on_disconnect_eb():
            d.errback()

        log.msg("Profile path: %s" % self.profile)
        log.msg("Device path: %s" % self.device.udi)
        self.dial_manager.ActivateConnection(self.profile, self.device.udi,
                                    dbus_interface=consts.WADER_DIALUP_INTFACE,
                                    reply_handler=_on_connect_cb,
                                    error_handler=lambda ign:
                                                self.assertTrue(False))

        return d

