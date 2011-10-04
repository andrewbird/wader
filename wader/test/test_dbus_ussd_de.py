# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Copyright (C) 2009-2011  Vodafone España, S.A.
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
"""
Self-contained unittest suite for ModemManager implementations
"""

# install the following packages on Ubuntu
# python-dbus, python-gconf, python-gobject, python-twisted-core
#
# install the following packages On OpenSuSE
# dbus-1-python, python-gnome, python-gobject2, python-twisted
#
# to run the tests:
# trial -e -r glib2 --tbformat=verbose /path/to/test_dbus.py

import os
import re
import time

import dbus
import dbus.mainloop.glib
import gconf
from twisted.internet import defer, reactor
from twisted.internet.task import deferLater
from twisted.trial import unittest

MM_SERVICE = 'org.freedesktop.ModemManager'
MM_OBJPATH = '/org/freedesktop/ModemManager'
MM_INTFACE = MM_SERVICE

MDM_INTFACE = 'org.freedesktop.ModemManager.Modem'
SPL_INTFACE = 'org.freedesktop.ModemManager.Modem.Simple'
CRD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Card'
CTS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Contacts'
SMS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.SMS'
NET_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Network'
USD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Ussd'

# should the extensions introduced by the Wader project be tested?
TEST_WADER_EXTENSIONS = True
# generic message for [wader] skipped tests
GENERIC_SKIP_MSG = "Wader extension to MM"
GCONF_BASE = '/apps/wader-core'

def get_dbus_error(e):
    if dbus.version >= (0, 83, 0):
        return e.get_dbus_name()
    else:
        return e.message


class Config(object):
    """Simple GConf wrapper for string-only gets"""

    def __init__(self, path):
        self.path = path
        self.client = gconf.client_get_default()

    def get(self, section, key, default=None):
        path = os.path.join(self.path, section, key)
        value = self.client.get(path)
        if not value:
            return (default if default is not None else "")

        assert value.type == gconf.VALUE_STRING, "Unhandled type"
        return value.get_string()


config = Config(GCONF_BASE)

# ==================================================
#                    ATTENTION
# ==================================================
# The following settings are required to be specified
# for some tests otherwise they won't run:
#
# gconftool-2 -s -t string /apps/wader-core/test/pin 0000
# gconftool-2 -s -t string /apps/wader-core/test/puk 12345678
# Unused for now:
# gconftool-2 -s -t string /apps/wader-core/test/phone 876543210
#
# edit the GCONF_BASE variable above, to change the '/apps/wader-core'

device = None
numtests = None


class DBusTestCase(unittest.TestCase):
    """Test-suite for ModemManager DBus exported methods"""

    def setUp(self):
        return self.setUpOnce()

    def setUpOnce(self):
        # setUpClass has been removed in twisted 10.0, and setUp should be
        # used instead, however setUp's behaviour doesn't replicate
        # setUpClass' one, so for now we're going to live with this horrid
        # hack
        global device, numtests

        if device:
            self.device = device
            return defer.succeed(True)

        if numtests is None:
            numtests = len([m for m in dir(self) if m.startswith('test_')])

        d = defer.Deferred()

        self.device = None
        loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=loop)

        def enable_device_cb():
            # if we don't sleep for a sec, the test will start too soon
            # and Enable won't be finished yet, yielding spurious results.
            time.sleep(1)
            d.callback(True)

        def send_pin_cb():
            # enable the device
            self.device.Enable(True, dbus_interface=MDM_INTFACE,
                               reply_handler=enable_device_cb,
                               error_handler=d.errback)

        def enable_device_eb(e):
            if 'SimPinRequired' in get_dbus_error(e):
                pin = config.get('test', 'pin', '0000')
                self.device.SendPin(pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=send_pin_cb,
                                    error_handler=d.errback)
            elif 'SimPukRequired' in get_dbus_error(e):
                pin = config.get('test', 'pin', '0000')
                puk = config.get('test', 'puk')
                if not puk:
                    msg = "SimPukRequired error and no PUK defined in config"
                    raise unittest.SkipTest(msg)

                self.device.SendPuk(puk, pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=send_pin_cb,
                                    error_handler=d.errback)
            else:
                raise unittest.SkipTest("Cannot handle error %s" % e)

        def get_device_from_opath(opaths):
            global device

            if not len(opaths):
                raise unittest.SkipTest("Can't run this test without devices")

            self.device = device = bus.get_object(MM_SERVICE, opaths[0])
            # enable the device
            self.device.Enable(True, dbus_interface=MDM_INTFACE,
                               reply_handler=enable_device_cb,
                               error_handler=enable_device_eb)

        obj = bus.get_object(MM_SERVICE, MM_OBJPATH)
        obj.EnumerateDevices(dbus_interface=MM_INTFACE,
                             reply_handler=get_device_from_opath,
                             error_handler=d.errback)
        return d

    def tearDown(self):
        global numtests

        if numtests == 1:
            numtests = None
            return self.tearDownOnce()
        else:
            numtests -= 1
            return defer.succeed(True)

    def tearDownOnce(self):
        global device
        # disable device at the end of the test
        # self.device.Enable(False, dbus_interface=MDM_INTFACE)
        self.device = device = None

    def do_when_registered(self, callback, errback=None):
        """
        Waits for registration then fires callback
        Many prior tests can leave the card unregistered, use this if you need
        registration for your test to be successful
        """
        reply = self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE)
        status, numeric_oper = reply[:2]
        # we must be registered to our home network or roaming
        if status in [1, 5]:
            d = defer.succeed(status)
            d.addCallback(callback)
            return d
        elif status == 2:
            return deferLater(reactor, 5, self.do_when_registered,
                                          callback, errback)
        else:
            if errback is None:
                raise unittest.FailTest("Device is neither registered or"
                                        " trying: status == %d" % status)
            else:
                d = defer.fail(status)
                d.addErrback(errback)
                return d

    def test_UssdInteractiveStatesCancel(self):
        """Test for working ussd implementation"""
        def cb(*args):
            # get the IMSI and check if we have a suitable SIM
            imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
            if not imsi.startswith("26202"):
                raise unittest.SkipTest("Untested")

            request, regex = ('*100#', '^Bitte w.*')

            # make sure we are good to test
            # should be idle now
            state = self.device.Get(USD_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
            self.assertEqual(state, 'idle')

            d = defer.Deferred()

            def session_start(response):
                try:
                    self.failUnless(re.compile(regex).match(response))
                    # check network is waiting for user response
                    state = self.device.Get(USD_INTFACE, 'State',
                                            dbus_interface=dbus.PROPERTIES_IFACE)
                    self.assertEqual(state, 'user-response')
                except unittest.FailTest, e:
                    d.errback(unittest.FailTest(e))

                def check_idle():
                    # check network is idle
                    try:
                        state = self.device.Get(USD_INTFACE, 'State',
                                            dbus_interface=dbus.PROPERTIES_IFACE)
                        self.assertEqual(state, 'idle')
                        d.callback(True)
                    except unittest.FailTest, e:
                        d.errback(unittest.FailTest(e))

                # Cancel
                # Early TS27007 didn't have the facility to cancel a
                # current session, so our options are limited. We might
                # wait a while for the network to time it out though
                try:
                    self.device.Cancel()
                    return deferLater(reactor, 5, check_idle)
                except:
                    return deferLater(reactor, 30, check_idle)

            def session_fail(failure):
                d.errback(unittest.FailTest(failure))

            # get interactive menu
            self.device.Initiate(request, reply_handler=session_start,
                                          error_handler=session_fail)

            # should be 'active' now
            state = self.device.Get(USD_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
            self.assertEqual(state, 'active')

            return d

        return self.do_when_registered(cb)

    test_UssdInteractiveStatesCancel.timeout = 75

    def test_UssdInteractiveStatesComplete(self):
        """Test for working ussd implementation"""
        def cb(*args):
            # get the IMSI and check if we have a suitable SIM
            imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
            if not imsi.startswith("26202"):
                raise unittest.SkipTest("Untested")

            request, menu_regex, menu_item, text_regex = \
                ('*100#', '^Bitte w.*', '3', '.*MeinVodafone.*')

            # make sure we are good to test
            # should be idle now
            state = self.device.Get(USD_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
            self.assertEqual(state, 'idle')

            d = defer.Deferred()

            def session_start(response):
                try:
                    # Check we have the menu
                    self.failUnless(re.compile(menu_regex).match(response))

                    # Check network is waiting for user response
                    state = self.device.Get(USD_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
                    self.assertEqual(state, 'user-response')

                    # Choose menu item, check it's the proper text
                    response = self.device.Respond(menu_item)
                    self.failUnless(re.compile(text_regex).match(response))

                    # Should be just simple text message, no reply required
                    state = self.device.Get(USD_INTFACE, 'State',
                                           dbus_interface=dbus.PROPERTIES_IFACE)
                    self.assertEqual(state, 'idle')

                    d.callback(True)

                except unittest.FailTest, e:
                    self.device.Cancel()
                    d.errback(unittest.FailTest(e))

            def session_fail(failure):
                d.errback(unittest.FailTest(failure))

            # get interactive menu
            self.device.Initiate(request, reply_handler=session_start,
                                          error_handler=session_fail)

            # should be 'active' now
            state = self.device.Get(USD_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
            self.assertEqual(state, 'active')

            return d

        return self.do_when_registered(cb)

    test_UssdInteractiveStatesComplete.timeout = 75
