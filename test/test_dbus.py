# -*- coding: utf-8 -*-
# Copyright (C) 2011-2012  Sphere Systems, U.K.
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
"""
Self-contained unittest suite for ModemManager implementations
"""

# install the following packages on Ubuntu
# python-dbus, python-gobject
#
# install the following packages On OpenSuSE
# dbus-1-python, python-gnome, python-gobject2
#
# to run all the tests:
# nosetests -v --with-xunit test/test_dbus.py
# or selectively
# nosetests -v --with-xunit test/test_dbus.py -m test_ZDisableReEnable10

# Make sure the very first thing we do is to set the glib loop as default
import dbus
import dbus.mainloop.glib
loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

import gobject

import random
import string
import sys
import time

try:
    import unittest2 as unittest
except ImportError:
    import unittest

# Duplicate any consts rather than include wader/common/consts

MM_SERVICE = 'org.freedesktop.ModemManager'
MM_OBJPATH = '/org/freedesktop/ModemManager'
MM_INTFACE = MM_SERVICE

MDM_INTFACE = 'org.freedesktop.ModemManager.Modem'
SPL_INTFACE = 'org.freedesktop.ModemManager.Modem.Simple'
CRD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Card'
CTS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Contacts'
SMS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.SMS'
NET_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Network'

MM_NETWORK_BAND_ANY = 0x1

# MM_NETWORK_MODE_* is a confusing mess of modes and prefs
MM_NETWORK_MODE_UNKNOWN = 0x00000000
MM_NETWORK_MODE_ANY = 0x00000001
MM_NETWORK_MODE_GPRS = 0x00000002
MM_NETWORK_MODE_EDGE = 0x00000004
MM_NETWORK_MODE_UMTS = 0x00000008
MM_NETWORK_MODE_HSDPA = 0x00000010
MM_NETWORK_MODE_2G_PREFERRED = 0x00000020
MM_NETWORK_MODE_3G_PREFERRED = 0x00000040
MM_NETWORK_MODE_2G_ONLY = 0x00000080
MM_NETWORK_MODE_3G_ONLY = 0x00000100
MM_NETWORK_MODE_HSUPA = 0x00000200
MM_NETWORK_MODE_HSPA = 0x00000400

MM_ALLOWED_MODE_ANY = 0
MM_ALLOWED_MODE_2G_PREFERRED = 1
MM_ALLOWED_MODE_3G_PREFERRED = 2
MM_ALLOWED_MODE_2G_ONLY = 3
MM_ALLOWED_MODE_3G_ONLY = 4

# should the extensions introduced by the Wader project be tested?
TEST_WADER_EXTENSIONS = True
# generic message for [wader] skipped tests
GENERIC_SKIP_MSG = "Wader extension to MM"

CONFIG = {
    'pin': '0000',
    'puk': None,
}


def get_bit_list(value):
    return [(1 << bit) for bit in range(32) if (1 << bit) & value]


def get_dbus_error(e):
    if hasattr(e, 'get_dbus_name'):
        return e.get_dbus_name()

    return e.message


def get_dbus_message(e):
    if hasattr(e, 'get_dbus_message'):
        return e.get_dbus_message()

    return ''


def get_random_string():
    return 'Test-' + ''.join(random.choice(
                    string.ascii_uppercase + string.digits) for x in range(11))


def convert_network_mode_to_allowed_mode(mode):
    trans_table = {
        MM_NETWORK_MODE_ANY: MM_ALLOWED_MODE_ANY,
        MM_NETWORK_MODE_2G_PREFERRED: MM_ALLOWED_MODE_2G_PREFERRED,
        MM_NETWORK_MODE_3G_PREFERRED: MM_ALLOWED_MODE_3G_PREFERRED,
        MM_NETWORK_MODE_2G_ONLY: MM_ALLOWED_MODE_2G_ONLY,
        MM_NETWORK_MODE_3G_ONLY: MM_ALLOWED_MODE_3G_ONLY,
    }
    return trans_table.get(mode)


class DBusTestCase(unittest.TestCase):
    """Test-suite for ModemManager DBus exported methods"""

    @classmethod
    def setUpClass(cls):
        bus = dbus.SystemBus()
        obj = bus.get_object(MM_SERVICE, MM_OBJPATH)

        opaths = obj.EnumerateDevices(dbus_interface=MM_INTFACE)
        if not len(opaths):
            raise RuntimeError("Can't run these tests without a device")
        cls.device = bus.get_object(MM_SERVICE, opaths[0])

        def enable_device_cb():
            pass

        def enable_device_eb(e):

            def send_pin_eb(e):
                raise RuntimeError("Send PIN failed \"%s\"" % str(e))

            def send_puk_eb(e):
                raise RuntimeError("Send PUK failed \"%s\"" % str(e))

            def send_pin_cb():
                try:
                    # enable the device
                    cls.device.Enable(True, dbus_interface=MDM_INTFACE)
                    enable_device_cb()
                except dbus.DBusException, e:
                    send_pin_eb(e)

            if 'SimPinRequired' in get_dbus_error(e):
                pin = CONFIG.get('pin', '0000')
                try:
                    cls.device.SendPin(pin, dbus_interface=CRD_INTFACE)
                    send_pin_cb()
                except dbus.DBusException, e:
                    send_puk_eb(e)

            elif 'SimPukRequired' in get_dbus_error(e):
                puk = CONFIG.get('puk')
                if not puk:
                    msg = "SimPukRequired error and no PUK defined in config"
                    raise RuntimeError(msg)

                try:
                    cls.device.SendPuk(puk, pin, dbus_interface=CRD_INTFACE)
                    send_pin_cb()
                except dbus.DBusException, e:
                    send_puk_eb(e)

            else:
                raise RuntimeError("Cannot handle error \"%s\"" % str(e))

        try:
            # enable the device
            cls.device.Enable(True, dbus_interface=MDM_INTFACE)
            enable_device_cb()
        except dbus.DBusException, e:
            enable_device_eb(e)

        cls.flag_simready = False

    @classmethod
    def tearDownClass(cls):
        def enable_device_cb():
            pass

        def enable_device_eb(e):
            raise RuntimeError("Disabling failed \"%s\"" % str(e))

        try:
            # disable the device
            cls.device.Enable(False, dbus_interface=MDM_INTFACE)
            enable_device_cb()
        except dbus.DBusException, e:
            enable_device_eb(e)

###############################################################################
# Helpers follow
###############################################################################

    def do_wait_for_signal(self, iface, name, duration,
                            func=None, *fargs, **fkwargs):
        """
        Sets up the glib loop and waits for the signal ``name`` to occur on the
        specified interface ``iface``. On receipt it returns the signal args in
        a tuple, or if the total ``duration`` was exceeded, None.
        If a function is specified, it is called once the loop is running
        """
        result = {}

        main_loop = gobject.MainLoop()

        def timeout():
            main_loop.quit()

        def handler(*args):
            result['args'] = args
            main_loop.quit()

        sm = self.device.connect_to_signal(name, handler, dbus_interface=iface)
        if func is not None:
            gobject.timeout_add(250, func, *fargs, **fkwargs)
        gid = gobject.timeout_add_seconds(duration, timeout)
        main_loop.run()
        gobject.source_remove(gid)
        sm.remove()

        return result.get('args')

    def do_when_registered(self):
        """
        Waits upto 2 minutes for registration and fails the test if it doesn't
        occur.
        Many prior tests can leave the card unregistered, use this if you need
        registration for your test to be successful
        """
        timeout = 120
        for t in range(timeout/5):
            reply = self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE)
            status, numeric_oper = reply[:2]

            # we must be registered to our home network or roaming
            if status in [1, 5]:
                return

            time.sleep(5)

        self.fail("Timeout after %d seconds" % timeout)

    def do_when_sim_ready(self):
        name = "Test-Ready"
        number = "00000000"
        while not self.flag_simready:
            try:
                self.device.Add(name, number, dbus_interface=CTS_INTFACE)
                self.flag_simready = True
            except dbus.DBusException, e:
                if 'SimBusy' in get_dbus_error(e):
                    time.sleep(5)
                    continue
                else:
                    self.fail(str(e))

    def do_remove_all_contacts(self):
        contacts = self.device.List(dbus_interface=CTS_INTFACE)
        for contact in contacts:
            self.device.Delete(contact[0], dbus_interface=CTS_INTFACE)

###############################################################################
# Tests follow
###############################################################################

    # org.freedesktop.DBus.Properties tests
    def test_MmPropertiesChangedSignal(self):
        """Test for DBus.Properties.MmPropertiesChanged signal"""
        # Note: hopefully the trigger for this is normal operation
        args = self.do_wait_for_signal(None, "MmPropertiesChanged", 120)
        if args is None:
            self.fail("Timeout")

        self.assertEqual(len(args), 2)
        self.assertIsInstance(args[0], basestring)
        self.assertIsInstance(args[1], dict)

    test_MmPropertiesChangedSignal.timeout = 240

    # org.freedesktop.ModemManager.Modem tests
    def test_ModemDeviceProperty(self):
        """Test for Modem.Device property"""
        if not sys.platform.startswith('linux'):
            raise unittest.SkipTest("Cannot be tested on OS != Linux")

        def check_if_valid_device(device):
            # Huawei, Novatel, ZTE, Old options, etc.
            for name in ['tty', 'hso', 'usb', 'wwan']:
                if name in device:
                    return True

            return False

        prop = self.device.Get(MDM_INTFACE, 'Device',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)
        self.assertTrue(check_if_valid_device(prop))

    def test_ModemConnTypeProperty(self):
        """Test for Modem.ConnType property"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        prop = self.device.Get(MDM_INTFACE, 'ConnType',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.UInt32)
        # Note: Don't accept '0' as valid here because we want to flag
        #       unknown devices so that we notice and add the correct value
        self.assertIn(prop, [1, 2, 3, 4, 5, 6, 7])

    # XXX: not implemented in Wader
    def test_ModemDeviceIdentifierProperty(self):
        """Test for Modem.DeviceIdentifier property"""
        raise unittest.SkipTest("not implemented in Wader")

        prop = self.device.Get(MDM_INTFACE, 'DeviceIdentifier',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)

    def test_ModemDriverProperty(self):
        """Test for Modem.Driver property"""
        if not sys.platform.startswith('linux'):
            raise unittest.SkipTest("Cannot be tested on OS != Linux")

        prop = self.device.Get(MDM_INTFACE, 'Driver',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIn(prop, ['hso', 'option', 'mbm', 'sierra', 'cdc_ether',
                                'cdc_wdm', 'cdc_acm', 'qcserial'])

    def test_ModemEnabledProperty(self):
        """Test for Modem.Enabled property"""
        prop = self.device.Get(MDM_INTFACE, 'Enabled',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.Boolean)

    def test_ModemEquipmentIdentifierProperty(self):
        """Test for Modem.EquipmentIdentifier property"""
        prop = self.device.Get(MDM_INTFACE, 'EquipmentIdentifier',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)

    def test_ModemIpMethodProperty(self):
        """Test for Modem.IpMethod property"""
        prop = self.device.Get(MDM_INTFACE, 'IpMethod',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.UInt32)
        self.assertIn(prop, [0, 1, 2])

    # XXX: not implemented in Wader
    def test_ModemIpTimeoutProperty(self):
        """Test for Modem.IpTimeout property"""
        raise unittest.SkipTest("not implemented in Wader")

        prop = self.device.Get(MDM_INTFACE, 'IpTimeout',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.UInt32)

    def test_ModemLastApnProperty(self):
        """Test for Modem.LastApn property"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        prop = self.device.Get(MDM_INTFACE, 'LastApn',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)

    def test_ModemMasterDeviceProperty(self):
        """Test for Modem.MasterDevice property"""
        prop = self.device.Get(MDM_INTFACE, 'MasterDevice',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)

    # XXX: not implemented in Wader
    # <property name="PinRetryCounts" type="a{su}" access="read">

    def test_ModemStateChangedSignal(self):
        """Test for Modem.StateChanged signal"""

        # XXX: Need a good trigger here, Disable/Enable is no good as if it
        # fails due to a bug unrelated to this test, all following tests
        # fail.

        raise unittest.SkipTest("Untested")

#        def trigger():
#            self.device.Enable(False, dbus_interface=MDM_INTFACE)
#
#        def cleanup():
#            try:
#                self.device.Enable(True, dbus_interface=MDM_INTFACE)
#
#            except dbus.DBusException, e:
#                if 'SimPinRequired' in get_dbus_error(e):
#                    pin = CONFIG.get('pin', '0000')
#                    try:
#                        self.device.SendPin(pin, dbus_interface=CRD_INTFACE)
#
#                    except dbus.DBusException, e:
#                        self.fail(str(e))
#                else:
#                    self.fail(str(e))
#
#            # We need to give a chance to reregister, but don't want to raise
#            # an error if it doesn't occur
#            time.sleep(30)
#
#        self.addCleanup(cleanup)
#
#        args = self.do_wait_for_signal(MDM_INTFACE, "StateChanged", 120,
#                                        trigger)
#        if args is None:
#            self.fail("Timeout")
#
#        self.assertEqual(len(args), 3)
#        self.assertIsInstance(args[0], dbus.UInt32)
#        self.assertIsInstance(args[1], dbus.UInt32)
#        self.assertIsInstance(args[2], dbus.UInt32)
#
#        self.assertIn(args[0], [0, 10, 20, 30, 40, 50, 60, 70, 80, 90])  # old
#        self.assertIn(args[1], [0, 10, 20, 30, 40, 50, 60, 70, 80, 90])  # new
#        self.assertIn(args[2], [0, 1, 2])  # reason
#
#    test_ModemStateChangedSignal.timeout = 240

    def test_ModemStateProperty(self):
        """Test for Modem.State property"""
        prop = self.device.Get(MDM_INTFACE, 'State',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.UInt32)
        self.assertIn(prop, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90])

    def test_ModemUnlockRequiredProperty(self):
        """Test for Modem.UnlockRequired property"""
        prop = self.device.Get(MDM_INTFACE, 'UnlockRequired',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, basestring)

    def test_ModemUnlockRetriesProperty(self):
        """Test for Modem.UnlockRetries property"""
        prop = self.device.Get(MDM_INTFACE, 'UnlockRetries',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(prop, dbus.UInt32)

    def test_ModemGetInfo(self):
        """Test for Modem.GetInfo"""
        info = self.device.GetInfo(dbus_interface=MDM_INTFACE)
        self.assertEqual(len(info), 3)
        self.assertIsInstance(info[0], basestring)
        self.assertIsInstance(info[1], basestring)
        self.assertIsInstance(info[2], basestring)

    def test_ModemFactoryReset(self):
        """Test for Modem.FactoryReset"""
        raise unittest.SkipTest("Untested")

    # org.freedesktop.ModemManager.Modem.Gsm.Card tests
    def _test_CardChangePin(self, charset):
        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

        good_pin = CONFIG.get('pin', '0000')
        bad_pin = '1111'

        # if this operations don't fail we can assume it is working
        self.device.ChangePin(good_pin, bad_pin, dbus_interface=CRD_INTFACE)
        self.device.ChangePin(bad_pin, good_pin, dbus_interface=CRD_INTFACE)

    def test_CardChangePinGsm(self):
        """Test for Modem.Gsm.Card.ChangePin in GSM charset"""
        self._test_CardChangePin('GSM')

    def test_CardChangePinUcs2(self):
        """Test for Modem.Gsm.Card.ChangePin in UCS2 charset"""
        self._test_CardChangePin('UCS2')

    def test_CardCheck(self):
        """Test for Modem.Gsm.Card.Check"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        status = self.device.Check(dbus_interface=CRD_INTFACE)
        self.assertEqual(status, "READY")

    def test_CardEnableEcho(self):
        """Test for Modem.Gsm.Card.EnableEcho"""
        # disabling Echo will probably leave Wader unusable
        raise unittest.SkipTest("Untestable method")

    def _test_CardEnablePin(self, charset):
        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

        pin = CONFIG.get('pin', '0000')
        # disable and enable PIN auth, if these operations don't fail
        # we can assume that the underlying implementation works
        self.device.EnablePin(pin, False, dbus_interface=CRD_INTFACE)
        self.device.EnablePin(pin, True, dbus_interface=CRD_INTFACE)

    def test_CardEnablePinGsm(self):
        """Test for Modem.Gsm.Card.EnablePin in GSM charset"""
        self._test_CardEnablePin('GSM')

    def test_CardEnablePinUcs2(self):
        """Test for Modem.Gsm.Card.EnablePin in UCS2 charset"""
        self._test_CardEnablePin('UCS2')

    def test_CardGetCharset(self):
        """Test for Modem.Gsm.Card.GetCharset"""
        charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)
        self.assertIn(charset, ['GSM', 'IRA', 'UCS2'])

    def test_CardGetCharsets(self):
        """Test for Modem.Gsm.Card.GetCharsets"""
        charsets = self.device.GetCharsets(dbus_interface=CRD_INTFACE)
        self.assertIn('IRA', charsets)
        self.assertIn('UCS2', charsets)

    def test_CardGetImei(self):
        """Test for Modem.Gsm.Card.GetImei"""
        imei = self.device.GetImei(dbus_interface=CRD_INTFACE)
        self.assertRegexpMatches(imei, '^\d{14,17}$')  # 14 <= IMEI <= 17

    def test_CardGetImsi(self):
        """Test for Modem.Gsm.Card.GetImsi"""
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
        # according to http://en.wikipedia.org/wiki/IMSI there are
        # also IMSIs with 14 digits
        self.assertRegexpMatches(imsi, '^\d{14,15}$')  # 14 <= IMSI <= 15

    def test_CardGetOperatorId(self):
        """Test for Modem.Gsm.Card.GetOperatorId"""
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)

        known_good_sims = []
        known_good_sims.append('234159222401636')  # ASDA Mobile
        known_good_sims.append('234107305239842')  # TESCO
        known_good_sims.append('214012300907507')  # VF-ES

        try:
            # We have to order this list so the longest matches are first.
            # IMSI prefix, length of MCC+MNC
            for sim in [('23415', 5),    # VF-UK
                        ('23410', 5),    # O2-UK
                        ('21403', 5),    # Orange-ES, Masmovil-ES
                        ('21401', 5)]:   # VF-ES
                if imsi.startswith(sim[0]):
                    mcc_mnc = self.device.GetOperatorId(
                                dbus_interface=CRD_INTFACE)
                    self.assertEqual(mcc_mnc, sim[0][:sim[1]],
                                        "mcc_mnc=%s : sim_first=%s" % \
                                        (mcc_mnc, sim[0][:sim[1]]))
                    return
        except dbus.DBusException as e:
            if imsi in known_good_sims:
                self.fail("Failure with known good SIM")

            # We know some SIM cards will fail.
            GENERAL = MDM_INTFACE + '.General'
            txt = '%s not in %s' % (GENERAL, get_dbus_error(e))
            msg = get_dbus_message(e)
            if len(msg):
                txt = '%s: dbus_message=%s' % (txt, msg)
            self.assertIn(GENERAL, get_dbus_error(e), txt)
            raise unittest.SkipTest("Failure, but not known if SIM is old")

        raise unittest.SkipTest("Untested")

    def test_CardGetSpn(self):
        """Test for Modem.Gsm.Card.GetSpn"""
        self.do_when_registered()

        known_good_sims = []
        known_good_sims.append('234159222401636')  # ASDA Mobile
        known_good_sims.append('234107305239842')  # TESCO
        known_good_sims.append('214035453022694')  # MASmovil

        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)

        # Note: It's difficult to determine MVNO SIMs from MNOs issued ones
        #       so unless we can find a better method of telling them apart
        #       we have to do exact matching on the whole IMSI.
        try:
            for sim in [('234159222401636', 'ASDA Mobile'),
                        ('23415', ''),      # VF-UK
                        ('234107305239842', 'TESCO'),
                        ('23410', ''),      # O2-UK
                        ('214035453022694', 'MASmovil'),
                        ('21403', ''),      # Orange-ES
                        ('21401', '')]:     # Vodafone-ES
                if imsi.startswith(sim[0]):
                    spn = self.device.GetSpn(dbus_interface=CRD_INTFACE)
                    self.assertEqual(spn, sim[1])
                    return

        except dbus.DBusException as e:
            if imsi in known_good_sims:
                self.fail("Failure with known good SIM")

            # We know some SIM cards will fail.
            GENERAL = MDM_INTFACE + '.General'
            txt = '%s not in %s' % (GENERAL, get_dbus_error(e))
            msg = get_dbus_message(e)
            if len(msg):
                txt = '%s: dbus_message=%s' % (txt, msg)
            self.assertIn(GENERAL, get_dbus_error(e), txt)
            raise unittest.SkipTest(
                "Failure, but not known if SIM has a populated SPN")

        raise unittest.SkipTest("Untested")

    test_CardGetSpn.timeout = 60

    def test_CardSimIdentifier(self):
        """Test for Modem.Gsm.Card.SimIdentifier property."""
        iccid = self.device.Get(CRD_INTFACE, 'SimIdentifier',
                                        dbus_interface=dbus.PROPERTIES_IFACE)

        msg = 'ICCID "%s" is not valid number string' % iccid
        self.assertRegexpMatches(iccid, r'89\d{16,17}', msg)

        try:
            from stdnum import luhn
            msg = 'ICCID "%s" does not pass Luhn algorithm validity test.' \
                    % iccid
            self.assertTrue(luhn.is_valid(iccid), msg)
        except ImportError:
            raise unittest.SkipTest('stdnum module not installed')

    def test_CardResetSettings(self):
        """Test for Modem.Gsm.Card.ResetSettings"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("Untested")

    def test_CardSendATString(self):
        """Test for Modem.Gsm.Card.SendATString"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("Untested")

    def test_CardSendPin(self):
        """Test for Modem.Gsm.Card.SendPin"""
        raise unittest.SkipTest("Untested")

    def test_CardSendPuk(self):
        """Test for Modem.Gsm.Card.SendPuk"""
        raise unittest.SkipTest("Untested")

    def test_CardSetCharset(self):
        """Test for Modem.Gsm.Card.SetCharset"""
        charsets = ["IRA", "GSM", "UCS2"]
        # get the current charset
        charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)
        self.assertIn(charset, charsets)
        # now pick a new charset
        new_charset = random.choice(charsets)
        while new_charset == charset:
            new_charset = random.choice(charsets)

        # set the charset to new_charset
        self.device.SetCharset(new_charset, dbus_interface=CRD_INTFACE)
        _charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)

        # leave everything as found
        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

        # check that the new charset is the expected one
        self.assertEqual(new_charset, _charset)

    def test_CardSupportedBandsProperty(self):
        """Test for Modem.Gsm.Card.SupportedBands property"""
        bands = self.device.Get(CRD_INTFACE, 'SupportedBands',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        if not bands:
            raise unittest.SkipTest("Cannot be tested")

        self.assertNotIn(MM_NETWORK_BAND_ANY, get_bit_list(bands))

    def test_CardSupportedModesProperty(self):
        """Test for Modem.Gsm.Card.SupportedModes property"""
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        blist = get_bit_list(modes)
        self.assertNotIn(MM_NETWORK_MODE_ANY, blist)

        # Check we are only advertising preferences
        self.assertNotIn(MM_NETWORK_MODE_GPRS, blist)
        self.assertNotIn(MM_NETWORK_MODE_EDGE, blist)
        self.assertNotIn(MM_NETWORK_MODE_UMTS, blist)
        self.assertNotIn(MM_NETWORK_MODE_HSDPA, blist)
        self.assertNotIn(MM_NETWORK_MODE_HSUPA, blist)
        self.assertNotIn(MM_NETWORK_MODE_HSPA, blist)

    # org.freedesktop.ModemManager.Modem.Gsm.Contacts tests
    def test_ContactsAdd(self):
        """Test for Modem.Gsm.Contacts.Add Ascii"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = "John", "+435443434343"
        # add a contact with ascii data
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # get the object via DBus and check that its data is correct
        _index, _name, _number = self.device.Get(index,
                                                    dbus_interface=CTS_INTFACE)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

        self.assertEqual(name, _name)
        self.assertEqual(number, _number)

    def test_ContactsAdd_UTF8_name(self):
        """Test for Modem.Gsm.Contacts.Add UTF8"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = u"中华人民共和", "+43544311113"
        # add a contact with UTF8 data
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # get the object via DBus and check that its data is correct
        _index, _name, _number = self.device.Get(index,
                                                    dbus_interface=CTS_INTFACE)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

        self.assertEqual(name, _name)
        self.assertEqual(number, _number)

    def test_ContactsDelete(self):
        """Test for Modem.Gsm.Contacts.Delete"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = "Juan", "+21544343434"
        # add a contact, and delete it
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # now delete it and check that its index is no longer present
        # if we list all the contacts
        self.device.Delete(index, dbus_interface=CTS_INTFACE)
        contacts = self.device.List(dbus_interface=CTS_INTFACE)
        self.assertNotIn(index, [c[0] for c in contacts])

    def test_ContactsEdit(self):
        """Test for Modem.Gsm.Contacts.Edit"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = "Eugenio", "+435345342121"
        new_name, new_number = "Eugenia", "+43542323122"
        # add a contact
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # edit it and get by index to check that the new values are set
        self.device.Edit(index, new_name, new_number,
                         dbus_interface=CTS_INTFACE)

        _index, _name, _number = self.device.Get(index,
                                                    dbus_interface=CTS_INTFACE)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

        self.assertEqual(_name, new_name)
        self.assertEqual(_number, new_number)

    def test_ContactsFindByName(self):
        """Test for Modem.Gsm.Contacts.FindByName"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        # add three contacts with similar names
        data = [('JohnOne', '+34656575757'), ('JohnTwo', '+34666575757'),
                ('JohnThree', '+34766575757')]
        indexes = [self.device.Add(name, number, dbus_interface=CTS_INTFACE)
                        for name, number in data]
        def cleanup():
            for index in indexes:
                self.device.Delete(index, dbus_interface=CTS_INTFACE)

        self.addCleanup(cleanup)

        # now search by name and make sure the matches match
        search_data = [('John', 3), ('JohnT', 2), ('JohnOne', 1)]
        for name, expected_matches in search_data:
            contacts = self.device.FindByName(name, dbus_interface=CTS_INTFACE)
            self.assertEqual(len(contacts), expected_matches)

    def test_ContactsFindByNumber(self):
        """Test for Modem.Gsm.Contacts.FindByNumber"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        # add three contacts with similar numbers
        data = [('JohnOne', '+34656575757'), ('JohnTwo', '+34666575757'),
                ('JohnThree', '+34766575757')]
        indexes = [self.device.Add(name, number, dbus_interface=CTS_INTFACE)
                        for name, number in data]

        def cleanup():
            for index in indexes:
                self.device.Delete(index, dbus_interface=CTS_INTFACE)

        self.addCleanup(cleanup)

        # now search by number and make sure the matches match
        search_data = [('575757', 3), ('66575757', 2), ('+34666575757', 1)]
        for number, expected_matches in search_data:
            contacts = self.device.FindByNumber(number,
                                                dbus_interface=CTS_INTFACE)
            self.assertEqual(len(contacts), expected_matches)

    def test_ContactsGet(self):
        """Test for Modem.Gsm.Contacts.Get"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = "Mario", "+312232332"

        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        reply = self.device.Get(index, dbus_interface=CTS_INTFACE)

        self.device.Delete(index, dbus_interface=CTS_INTFACE)

        self.assertIn(name, reply)
        self.assertIn(number, reply)
        self.assertIn(index, reply)

    def test_ContactsGetCount(self):
        """Test for Modem.Gsm.Contacts.GetCount"""
        self.do_when_sim_ready()
        count = self.device.GetCount(dbus_interface=CTS_INTFACE)
        contacts = self.device.List(dbus_interface=CTS_INTFACE)
        self.assertIsInstance(count, dbus.UInt32)
        self.assertEqual(count, len(contacts))

    def test_ContactsGetCount_2(self):
        """Test for Modem.Gsm.Contacts.GetCount 2"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        count = self.device.GetCount(dbus_interface=CTS_INTFACE)
        index = self.device.Add("Boethius", "+21123322323",
                                dbus_interface=CTS_INTFACE)
        count2 = self.device.GetCount(dbus_interface=CTS_INTFACE)

        self.device.Delete(index, dbus_interface=CTS_INTFACE)

        self.assertEqual(count + 1, count2)

    def test_ContactsGetPhonebookSize(self):
        """Test for Modem.Gsm.Contacts.GetPhonebookSize"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        size = self.device.GetPhonebookSize(dbus_interface=CTS_INTFACE)
        self.assertIsInstance(size, dbus.Int32)
        self.assertGreaterEqual(size, 100)

    def test_ContactsList(self):
        """Test for Modem.Gsm.Contacts.List"""
        self.do_when_sim_ready()
        self.do_remove_all_contacts()

        name, number = "Jauma", "+356456445654"

        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        reply = self.device.List(dbus_interface=CTS_INTFACE)

        # leave everything as found
        self.device.Delete(index, dbus_interface=CTS_INTFACE)

        found = False
        for contact in reply:
            if (index, name, number) == contact:
                found = True
                break

        self.assertTrue(found)

    # org.freedesktop.ModemManager.Modem.Gsm.Network tests
    def test_NetworkGetApns(self):
        """Test for Modem.Gsm.Network.GetApns"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        l = self.device.GetApns(dbus_interface=NET_INTFACE)
        self.assertIsInstance(l, list)
        if len(l):
            self.assertIsInstance(l[0], tuple)
            self.assertIsInstance(l[0][0], dbus.UInt32)
            self.assertIsInstance(l[0][1], basestring)

    def test_NetworkGetBand(self):
        """Test for Modem.Gsm.Network.GetBand"""
        band = self.device.GetBand(dbus_interface=NET_INTFACE)
        self.assertIsInstance(band, dbus.UInt32)
        self.assertGreater(band, 0)

    def test_NetworkGetNetworkMode(self):
        """Test for Modem.Gsm.Network.GetNetworkMode"""
        mode = self.device.GetNetworkMode(dbus_interface=NET_INTFACE)
        self.assertIsInstance(mode, dbus.UInt32)
        # currently goes between 0 and 0x400
        self.assertGreaterEqual(mode, 0)
        self.assertLessEqual(mode, 0x400)

    def test_NetworkGetRegistrationInfo(self):
        """Test for Modem.Gsm.Network.GetRegistrationInfo"""
        reply = self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE)
        status, numeric_oper = reply[:2]

        self.assertIsInstance(status, dbus.UInt32)
        self.assertIsInstance(numeric_oper, basestring)

        # we must be registered to our home network or roaming
        self.assertIn(status, [1, 5])

        if status == 1:  # home registration
            # get the IMSI and check that we are connected to a network
            # with a netid that matches the beginning of our IMSI
            imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
            # we should be registered with our home network
            msg = "%s doesn't start with %s" % (imsi, numeric_oper)
            self.assertTrue(imsi.startswith(numeric_oper), msg)

    def test_NetworkGetRoamingIDs(self):
        """Test for Modem.Gsm.Network.GetRoamingIDs"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        l = self.device.GetRoamingIDs(dbus_interface=NET_INTFACE)
        self.assertIsInstance(l, list)
        self.assertGreater(len(l), 0, "Empty list %s" % str(l))
        self.assertIsInstance(l[0], basestring)
        self.assertTrue(all(map(int, l)), "IDs = %s" % str(l))

    def test_NetworkGetSignalQuality(self):
        """Test for Modem.Gsm.Network.GetSignalQuality"""
        self.do_when_registered()

        quality = self.device.GetSignalQuality(dbus_interface=NET_INTFACE)
        self.assertIsInstance(quality, dbus.UInt32)
        self.assertGreaterEqual(quality, 0)
        self.assertLessEqual(quality, 100)

    def test_NetworkScan(self):
        """Test for Modem.Gsm.Network.Scan"""
        netreg = self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE)

        # potentially long operation, increasing timeout to 360 as core now
        # waits up to 300 secs
        networks = self.device.Scan(dbus_interface=NET_INTFACE, timeout=360)

        self.assertGreater(len(networks), 0)

        # our home network has to be around unless we are roaming ;)
        if netreg[0] == 1:
            # using the IMSI check that it's around
            imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)

            netids = [network['operator-num'] for network in networks]

            msg = "IMSI %s doesn't start with any of %s" % (imsi, str(netids))
            self.assertIn(True, map(imsi.startswith, netids), msg)

    def _test_NetworkSetApn(self, charset):
        # Set Charset
        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

        # Write and read back
        apn = get_random_string()
        self.device.SetApn(apn, dbus_interface=NET_INTFACE)
        l = self.device.GetApns(dbus_interface=NET_INTFACE)

        self.assertIsInstance(l, list)
        self.assertGreater(len(l), 0, "Empty list %s" % str(l))
        self.assertIsInstance(l[0], tuple)
        self.assertIn(apn, [a[1] for a in l])

    def test_NetworkSetApnGsm(self):
        """Test for Modem.Gsm.Network.SetApn using GSM charset"""
        self._test_NetworkSetApn('GSM')

    def test_NetworkSetApnUcs2(self):
        """Test for Modem.Gsm.Network.SetApn using UCS2 charset"""
        self._test_NetworkSetApn('UCS2')

    def test_NetworkSetApnWithMixedCharsets(self):
        """Test for Modem.Gsm.Network.SetApn using mixed charsets"""
        # GSM -> UCS2
        apn1 = get_random_string()
        self.device.SetCharset('GSM', dbus_interface=CRD_INTFACE)
        self.device.SetApn(apn1, dbus_interface=NET_INTFACE)
        self.device.SetCharset('UCS2', dbus_interface=CRD_INTFACE)
        list1 = self.device.GetApns(dbus_interface=NET_INTFACE)

        # UCS2 -> GSM
        apn2 = get_random_string()
        self.device.SetCharset('UCS2', dbus_interface=CRD_INTFACE)
        self.device.SetApn(apn2, dbus_interface=NET_INTFACE)
        self.device.SetCharset('GSM', dbus_interface=CRD_INTFACE)
        list2 = self.device.GetApns(dbus_interface=NET_INTFACE)

        self.assertIsInstance(list1, list)
        self.assertIsInstance(list2, list)

        self.assertIn(apn1, [a[1] for a in list1])
        self.assertIn(apn2, [a[1] for a in list2])

    def test_NetworkSetBand(self):
        """Test for Modem.Gsm.Network.SetBand"""
        bands = self.device.Get(CRD_INTFACE, 'SupportedBands',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        if not bands:
            raise unittest.SkipTest("Cannot be tested")

        def set_band_any():
            # leave it in BAND_ANY and give it some seconds to settle
            self.device.SetBand(MM_NETWORK_BAND_ANY)
            time.sleep(5)

        self.addCleanup(set_band_any)

        for band in get_bit_list(bands):
            self.device.SetBand(band)
            _band = self.device.GetBand()

            self.assertEqual(_band, band)

    def test_NetworkSetAllowedMode(self):
        """Test for Modem.Gsm.Network.SetAllowedMode"""
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        def set_mode_any():
            # leave it in MODE_ANY and give it some seconds to settle
            self.device.SetAllowedMode(MM_ALLOWED_MODE_ANY)
            time.sleep(5)

        self.addCleanup(set_mode_any)

        for net_mode in get_bit_list(modes):
            mode = convert_network_mode_to_allowed_mode(net_mode)
            if mode is not None:
                self.device.SetAllowedMode(mode)
                allowed_mode = self.device.Get(NET_INTFACE, 'AllowedMode',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
                self.assertEqual(allowed_mode, mode)

    def test_NetworkSetNetworkMode(self):
        """Test for Modem.Gsm.Network.SetNetworkMode"""
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        def set_mode_any():
            # leave it in MODE_ANY and give it some seconds to settle
            self.device.SetAllowedMode(MM_ALLOWED_MODE_ANY)
            time.sleep(5)

        self.addCleanup(set_mode_any)

        for mode in get_bit_list(modes):
            self.device.SetNetworkMode(mode)
            network_mode = self.device.GetNetworkMode()
            self.assertEqual(network_mode, mode)

    def test_NetworkSetRegistrationNotification(self):
        """Test for Modem.Gsm.Network.SetRegistrationNotification"""
        raise unittest.SkipTest("Untested")

    def test_NetworkSetInfoFormat(self):
        """Test for Modem.Gsm.Network.SetInfoFormat"""
        raise unittest.SkipTest("Untested")

    def test_NetworkRegister(self):
        """Test for Modem.Gsm.Network.Register"""
        raise unittest.SkipTest("Untested")

    def test_NetworkAccessTechnologyProperty(self):
        """Test for Modem.Gsm.Network.AccessTechnology property"""
        access_tech = self.device.Get(NET_INTFACE, "AccessTechnology",
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.assertIsInstance(access_tech, dbus.UInt32)
        self.assertGreaterEqual(access_tech, 0)
        self.assertLessEqual(access_tech, 10)

    def test_NetworkAllowedModeProperty(self):
        """Test for Modem.Gsm.Network.AllowedMode property"""
        # tested in NetworkSetAllowedMode
        pass

    def test_NetworkSignalQualitySignal(self):
        """Test for Modem.Gsm.Network.SignalQuality signal"""
        # Note: the trigger for this is the normal sig strength daemon
        args = self.do_wait_for_signal(NET_INTFACE, "SignalQuality", 180)
        if args is None:
            self.fail("Timeout")

        self.assertEqual(len(args), 1)
        self.assertIsInstance(args[0], dbus.UInt32)
        self.assertGreaterEqual(args[0], 0)
        self.assertLessEqual(args[0], 100)

    test_NetworkSignalQualitySignal.timeout = 240

    def test_NetworkRegistrationInfoSignal(self):
        """Test for Modem.Gsm.Network.RegistrationInfo signal"""
        # Note: the trigger for this is the normal net registration daemon
        args = self.do_wait_for_signal(NET_INTFACE, "RegistrationInfo", 240)
        if args is None:
            self.fail("Timeout")

        self.assertEqual(len(args), 3)
        self.assertIsInstance(args[0], dbus.UInt32)
        self.assertIsInstance(args[1], basestring)
        self.assertIsInstance(args[2], basestring)
        self.assertIn(args[0], range(5))

    test_NetworkRegistrationInfoSignal.timeout = 300

    # org.freedesktop.ModemManager.Modem.Simple tests
    def test_SimpleConnect(self):
        """Test for Modem.Simple.Connect"""
        raise unittest.SkipTest("Untested")

    def test_SimpleDisconnect(self):
        """Test for Modem.Simple.Disconnect"""
        raise unittest.SkipTest("Untested")

    def test_SimpleGetStatus(self):
        """Test for Modem.Simple.GetStatus"""
        status = self.device.GetStatus(dbus_interface=SPL_INTFACE)
        self.assertIn('band', status)
        self.assertIn('signal_quality', status)
        self.assertIn('operator_code', status)
        self.assertIn('operator_name', status)
        self.assertIsInstance(status['operator_name'], basestring)
        self.assertIsInstance(status['operator_code'], basestring)
        self.assertIsInstance(status['signal_quality'], dbus.UInt32)
        self.assertIsInstance(status['band'], dbus.UInt32)

    # org.freedesktop.ModemManager.Modem.Gsm.SMS tests
    def test_SmsDelete(self):
        """Test for Modem.Gsm.SMS.Delete"""
        sms = {'number': '+33622754135', 'text': 'delete test'}
        # save a sms, delete it and check is no longer present
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        self.assertEqual(len(indexes), 1)
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

        sms_found = False
        messages = self.device.List(dbus_interface=SMS_INTFACE)
        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
                break

        # the index should not be present
        self.assertEqual(sms_found, False)

    def test_SmsDeleteMultiparted(self):
        """Test for Modem.Gsm.SMS.Delete - Multipart"""
        sms = {'number': '+34622754135',
               'text': """test_SmsDeleteMultiparted test_SmsDeleteMultiparted
                           test_SmsDeleteMultiparted test_SmsDeleteMultiparted
                           test_SmsDeleteMultiparted test_SmsDeleteMultiparted
                           test_SmsDeleteMultiparted test_SmsDeleteMultiparted
                           """}
        # save a sms, delete it and check is no longer present
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        self.assertEqual(len(indexes), 1)
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

        messages = self.device.List(dbus_interface=SMS_INTFACE)
        sms_found = False
        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
        # the index should not be present
        self.assertEqual(sms_found, False)

    def test_SmsGet(self):
        """Test for Modem.Gsm.SMS.Get"""
        sms = {'number': '+33646754145', 'text': 'get test'}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])

    def test_SmsGetMultiparted(self):
        """Test for Modem.Gsm.SMS.Get - Multipart"""
        sms = {'number': '+34622754135',
               'text': """test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           """}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])

    def test_SmsGetSmsc(self):
        """Test for Modem.Gsm.SMS.GetSmsc"""
        smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)
        self.assertTrue(smsc.startswith('+'))

    def test_SmsGetFormat(self):
        """Test for Modem.Gsm.SMS.GetFormat"""
        fmt = self.device.GetFormat(dbus_interface=SMS_INTFACE)
        self.assertIsInstance(fmt, dbus.UInt32)
        self.assertIn(fmt, [0, 1])

    def test_SmsList(self):
        """Test for Modem.Gsm.SMS.List"""
        sms = {'number': '+33622754135', 'text': 'list test'}
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        messages = self.device.List(dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

        # now check that the indexes are present in a List
        sms_found = False
        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
                break
        self.assertEqual(sms_found, True)

    def test_SmsList_2(self):
        """Test for Modem.Gsm.SMS.List - 2"""
        # get the current number of Sms
        size_before = len(self.device.List(dbus_interface=SMS_INTFACE))
        # add three new ones
        messages = [
            {'number': '+324342322', 'text': 'hey there'},
            {'number': '+334223312', 'text': 'where you at?'},
            {'number': '+324323232', 'text': 'hows it going?'}]

        indexes = []
        for sms in messages:
            indexes.extend(self.device.Save(sms, dbus_interface=SMS_INTFACE))

        size_after = len(self.device.List(dbus_interface=SMS_INTFACE))

        # leave everything as found
        for index in indexes:
            self.device.Delete(index, dbus_interface=SMS_INTFACE)

        # check that the size has increased just three
        self.assertEqual(size_before + 3, size_after)

    def test_SmsListMultiparted(self):
        """Test for Modem.Gsm.SMS.List - Multipart"""
        sms = {'number': '+34622754135',
               'text': """test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted"""}
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        # now check that the indexes are present in a List
        messages = self.device.List(dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

        sms_found = False
        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
                break

        self.assertEqual(sms_found, True)

    def test_SmsListMultiparted_2(self):
        """Test for Modem.Gsm.SMS.List - Multipart 2"""
        # get the current number of Sms
        size_before = len(self.device.List(dbus_interface=SMS_INTFACE))
        # add three new ones
        what = [
            {'number': '+324342322', 'text': 'hey there'},
            {'number': '+34622754135',
             'text': """test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         """},
            {'number': '+34622754135',
             'text': """test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                         test_SmsListMultiparted_2 test_SmsListMultiparted_2
                          """},
            {'number': '+324323232', 'text': 'hows it going?'}]

        indexes = []
        for sms in what:
            indexes.extend(self.device.Save(sms, dbus_interface=SMS_INTFACE))

        size_after = len(self.device.List(dbus_interface=SMS_INTFACE))

        # leave everything as found
        for index in indexes:
            self.device.Delete(index, dbus_interface=SMS_INTFACE)

        # check that the size has increased just three
        self.assertEqual(size_before + 4, size_after)

    def test_SmsSave(self):
        """Test for Modem.Gsm.SMS.Save"""
        sms = {'number': '+34645454445', 'text': 'save test'}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])

    def test_SmsSaveMultiparted(self):
        """Test for Modem.Gsm.SMS.Save - Multipart"""
        sms = {'number': '+34622754135',
               'text': """test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           """}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])

    def test_SmsSend(self):
        """Test for Modem.Gsm.SMS.Send"""
        raise unittest.SkipTest("Not ready")
        #number = config.get('test', 'phone')
        #if not number:
        #    raise unittest.SkipTest("Cannot run this test without a number")

        #d = defer.Deferred()
        #sm = None  # SignalMatch
        #sms = {'number' : number, 'text' : 'send test'}

        #def on_sms_received_cb(index, complete):
        #    def compare_messages(_sms):
        #        self.assertEqual(_sms['text'], sms['text'])
        #        sm.remove() # remove SignalMatch
        #        # leave everything as found
        #        self.device.Delete(index, dbus_interface=SMS_INTFACE,
        #                           reply_handler=lambda: d.callback(True),
        #                           error_handler=d.errback)

        #    self.device.Get(index, dbus_interface=SMS_INTFACE,
        #                    reply_handler=compare_messages,
        #                    error_handler=d.errback)

        #sm = self.device.connect_to_signal("SmsReceived", on_sms_received_cb,
        #                                   dbus_interface=SMS_INTFACE)

        #self.device.Send(sms, dbus_interface=SMS_INTFACE,
        #                 # we are not interested in the callback
        #                 reply_handler=lambda indexes: None,
        #                 error_handler=d.errback)

        #return d

    def test_SmsSendFromStorage(self):
        """Test for Modem.Gsm.SMS.SendFromStorage"""
        raise unittest.SkipTest("Not ready")
        #number = config.get('test', 'phone')
        #if not number:
        #    raise unittest.SkipTest("Cannot run this test without a number")
        #d = defer.Deferred()
        #sm = None  # SignalMatch
        #sms = {'number' : number, 'text' : 'send from storage test' }

        #def on_sms_received_cb(index, complete):
        #    def compare_messages(_sms):
        #        self.assertEqual(_sms['text'], sms['text'])
        #        sm.remove() # remove SignalMatch
        #        # leave everything as found
        #        self.device.Delete(index, dbus_interface=SMS_INTFACE,
        #                           reply_handler=lambda: d.callback(True),
        #                           error_handler=d.errback)

        #    # now get it by index and check text is the same
        #    self.device.Get(index, dbus_interface=SMS_INTFACE,
        #                    reply_handler=compare_messages,
        #                    error_handler=d.errback)

        #def on_sms_saved_cb(indexes):
        #    self.assertEqual(len(indexes), 1)

        #    # send it from storage and wait for the signal
        #    self.device.SendFromStorage(indexes[0],
        #                                dbus_interface=SMS_INTFACE,
        #                                # we are not interested in callback
        #                                reply_handler=lambda indexes: None,
        #                                error_handler=d.errback)

        #sm = self.device.connect_to_signal("SmsReceived", on_sms_received_cb)

        ## save the message and send it to ourselves
        #self.device.Save(sms, dbus_interface=SMS_INTFACE,
        #                 reply_handler=on_sms_saved_cb,
        #                 error_handler=d.errback)

        #return d

    def test_SmsSetFormat(self):
        """Test for Modem.Gsm.SMS.SetFormat"""
        # set text format and check immediately that a
        # GetFormat call returns 1
        try:
            self.device.SetFormat(1, dbus_interface=SMS_INTFACE)
        except dbus.DBusException, e:
            if 'CMSError303' in get_dbus_error(e):
                # Ericsson doesn't allow us to set text format
                raise unittest.SkipTest()
        else:
            fmt = self.device.GetFormat(dbus_interface=SMS_INTFACE)

            # leave format as found
            self.device.SetFormat(0, dbus_interface=SMS_INTFACE)

            self.assertEqual(fmt, 1)

    def test_SmsSetIndication(self):
        """Test for Modem.Gsm.SMS.SetIndication"""
        # simple test for AT+CNMI, if this set command fails the
        # AT string needs to be changed. The reason the test is so simple
        # is because there's no GetIndication command in the spec, and I
        # didn't feel like coordinating an extension with the MM guys.
        # self.device.SetIndication(2, 1, 0, 1, 0)

    def test_SmsSetSmsc(self):
        """Test for Modem.Gsm.SMS.SetSmsc"""
        bad_smsc = '+3453456343'
        # get the original SMSC and memoize it
        smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)
        # set the SMSC to a bad value and read it to confirm it worked
        self.device.SetSmsc(bad_smsc, dbus_interface=SMS_INTFACE)
        _bad_smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)

        # leave everything as found
        self.device.SetSmsc(smsc, dbus_interface=SMS_INTFACE)

        # bad_smsc has been correctly set
        self.assertEqual(bad_smsc, _bad_smsc)

    def _test_Ussd(self, charset):
        self.do_when_registered()

        # get the IMSI and check if we have a suitable ussd request/regex
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
        if imsi.startswith("21401"):
            request, regex = ('*118#', r'^Spain.*$')
        elif imsi.startswith("23415"):
            request, regex = ('*#100#', r'^07\d{9}$')
        else:
            raise unittest.SkipTest("Untested")

        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

        response = self.device.Initiate(request)

        self.assertRegexpMatches(response, regex)

    def test_UssdGsm(self):
        """Test for Modem.Gsm.Ussd.Initiate using GSM charset"""
        self._test_Ussd('GSM')

    test_UssdGsm.timeout = 60

    def test_UssdUcs2(self):
        """Test for Modem.Gsm.Ussd.Initiate using UCS2 charset"""
        self._test_Ussd('UCS2')

    test_UssdUcs2.timeout = 60

    def _test_ZDisableReEnable(self, interval):
        # disable the device
        try:
            self.device.Enable(False, dbus_interface=MDM_INTFACE)

        except dbus.DBusException, e:
            self.fail(str(e))

        # maybe sleep - some devices might be async WRT enable/disable so let's
        #               try to catch them out
        if interval:
            time.sleep(interval)

        # reenable the device
        try:
            self.device.Enable(True, dbus_interface=MDM_INTFACE)

        except dbus.DBusException, e:
            if 'SimPinRequired' in get_dbus_error(e):
                pin = CONFIG.get('pin', '0000')
                try:
                    self.device.SendPin(pin, dbus_interface=CRD_INTFACE)

                except dbus.DBusException, e:
                    self.fail(str(e))
            else:
                self.fail(str(e))

    def test_ZDisableReEnable00(self):
        """Test for disable device and successful reenable - interval 0"""
        self._test_ZDisableReEnable(0)

    test_ZDisableReEnable00.timeout = 60

    def test_ZDisableReEnable10(self):
        """Test for disable device and successful reenable - interval 10"""
        self._test_ZDisableReEnable(10)

    test_ZDisableReEnable10.timeout = 60
