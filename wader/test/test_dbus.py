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
import random
import re
import sys
import time

import dbus
import dbus.mainloop.glib
import gconf
from twisted.internet import defer
from twisted.trial import unittest

from wader.common.utils import (get_bands, get_network_modes,
                                convert_network_mode_to_allowed_mode)
from wader.common.consts import (MM_NETWORK_BAND_ANY, MM_NETWORK_MODE_ANY,
                                 MM_ALLOWED_MODE_ANY,
                                 MM_GSM_ACCESS_TECHNOLOGIES)

MM_SERVICE = 'org.freedesktop.ModemManager'
MM_OBJPATH = '/org/freedesktop/ModemManager'
MM_INTFACE = MM_SERVICE

MDM_INTFACE = 'org.freedesktop.ModemManager.Modem'
SPL_INTFACE = 'org.freedesktop.ModemManager.Modem.Simple'
CRD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Card'
CTS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Contacts'
SMS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Sms'
NET_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Network'

# should the extensions introduced by the Wader project be tested?
TEST_WADER_EXTENSIONS = True
# generic message for [wader] skipped tests
GENERIC_SKIP_MSG = "Wader extension to MM"
GCONF_BASE = '/apps/wader-core'

if dbus.version >= (0, 83, 0):

    def get_dbus_error(e):
        return e.get_dbus_name()
else:

    def get_dbus_error(e):
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


class DBusTestCase(unittest.TestCase):
    """Test-suite for ModemManager DBus exported methods"""

    def setUpClass(self):
        # setUpClass is meant to be deprecated, and setUp should be
        # used instead, however setUp's behaviour doesn't replicates
        # setUpClass' one, so for now we're going to use this
        # Twisted deprecated function
        d = defer.Deferred()
        self.device = None

        loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=loop)

        def enable_device_cb():
            # if we don't sleep for a sec, the test will start too soon
            # and Enable won't be finished yet, yielding spurious results.
            time.sleep(1)
            d.callback(True)

        def enable_device_eb(e):
            if 'SimPinRequired' in get_dbus_error(e):
                pin = config.get('test', 'pin', '0000')
                self.device.SendPin(pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=enable_device_cb,
                                    error_handler=d.errback)
            elif 'SimPukRequired' in get_dbus_error(e):
                pin = config.get('test', 'pin', '0000')
                puk = config.get('test', 'puk')
                if not puk:
                    msg = "SimPukRequired error and no PUK defined in config"
                    raise unittest.SkipTest(msg)

                self.device.SendPuk(puk, pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=enable_device_cb,
                                    error_handler=d.errback)
            else:
                raise unittest.SkipTest("Cannot handle error %s" % e)

        def get_device_from_opath(opaths):
            if not len(opaths):
                raise unittest.SkipTest("Can't run this test without devices")

            self.device = bus.get_object(MM_SERVICE, opaths[0])
            # enable the device
            self.device.Enable(True, dbus_interface=MDM_INTFACE,
                               reply_handler=enable_device_cb,
                               error_handler=enable_device_eb)

        obj = bus.get_object(MM_SERVICE, MM_OBJPATH)
        obj.EnumerateDevices(dbus_interface=MM_INTFACE,
                             reply_handler=get_device_from_opath,
                             error_handler=d.errback)
        return d

    def tearDownClass(self):
        # disable device at the end of the test
        self.device.Enable(False, dbus_interface=MDM_INTFACE)

    # org.freedesktop.ModemManager.Modem tests
    def test_ModemDeviceProperty(self):
        if sys.platform != 'linux2':
            raise unittest.SkipTest("Cannot be tested on OS != Linux")

        def check_if_valid_device(device):
            # Huawei, Novatel, ZTE, Old options, etc.
            for name in ['tty', 'hso', 'usb']:
                if name in device:
                    return True

            return False

        device = self.device.Get(MDM_INTFACE, 'Device',
                                 dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIsInstance(device, basestring)
        self.failUnless(check_if_valid_device(device))

    def test_ModemMasterDeviceProperty(self):
        master_device = self.device.Get(MDM_INTFACE, 'MasterDevice',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIsInstance(master_device, basestring)

    def test_ModemDriverProperty(self):
        if sys.platform != 'linux2':
            raise unittest.SkipTest("Cannot be tested on OS != Linux")

        driver = self.device.Get(MDM_INTFACE, 'Driver',
                                 dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIn(driver, ['hso', 'option', 'mbm', 'sierra',
                                   'cdc_ether', 'cdc_wdm', 'cdc_acm'])

    def test_ModemTypeProperty(self):
        _type = self.device.Get(MDM_INTFACE, 'Type',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIsInstance(_type, (int, dbus.UInt32))
        self.failUnlessIn(_type, [1, 2])

    def test_ModemIpMethodProperty(self):
        method = self.device.Get(MDM_INTFACE, 'IpMethod',
                                 dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIsInstance(method, (int, dbus.UInt32))
        self.failUnlessIn(method, [0, 1, 2])

    def test_ModemGetInfo(self):
        """Test for Modem.GetInfo"""
        info = self.device.GetInfo(dbus_interface=MDM_INTFACE)
        self.failUnless(len(info) == 3)
        self.failUnlessIsInstance(info[0], basestring)
        self.failUnlessIsInstance(info[1], basestring)
        self.failUnlessIsInstance(info[2], basestring)

    # org.freedesktop.ModemManager.Modem.Gsm.Card tests
    def test_CardChangePin(self):
        """Test for Card.ChangePin"""
        good_pin = config.get('test', 'pin', '0000')
        bad_pin = '1111'
        # if this operations don't fail we can assume it is working
        self.device.ChangePin(good_pin, bad_pin,
                              dbus_interface=CRD_INTFACE)
        self.device.ChangePin(bad_pin, good_pin)

    # if we unlocked the PIN at Enable we must increase the timeout
    # as the core gives the device 15 seconds to settle.
    test_CardChangePin.timeout = 30

    def test_CardCheck(self):
        """Test for Card.Check"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        status = self.device.Check(dbus_interface=CRD_INTFACE)
        self.assertEqual(status, "READY")

    def test_CardEnableEcho(self):
        """Test for Card.EnableEcho"""
        # disabling Echo will probably leave Wader unusable
        raise unittest.SkipTest("Untestable method")

    def test_CardEnablePin(self):
        """Test for Card.EnablePin"""
        pin = config.get('test', 'pin', '0000')
        # disable and enable PIN auth, if this operations don't fail
        # we can assume that the underlying implementation works
        self.device.EnablePin(pin, False, dbus_interface=CRD_INTFACE)
        self.device.EnablePin(pin, True, dbus_interface=CRD_INTFACE)

    test_CardEnablePin.timeout = 15

    def test_CardGetCharset(self):
        """Test for Card.GetCharset"""
        charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)
        self.failUnlessIn(charset, ['GSM', 'IRA', 'UCS2'])

    def test_CardGetCharsets(self):
        """Test for Card.GetCharsets"""
        charsets = self.device.GetCharsets(dbus_interface=CRD_INTFACE)
        self.failUnlessIn('IRA', charsets)
        self.failUnlessIn('UCS2', charsets)

    def test_CardGetImei(self):
        """Test for Card.GetImei"""
        imei = self.device.GetImei(dbus_interface=CRD_INTFACE)
        imei_regexp = re.compile('^\d{14,17}$') # 14 <= IMEI <= 17
        self.failUnless(imei_regexp.match(imei))

    def test_CardGetImsi(self):
        """Test for Card.GetImsi"""
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
        # according to http://en.wikipedia.org/wiki/IMSI there are
        # also IMSIs with 14 digits
        imsi_regexp = re.compile('^\d{14,15}$') # 14 <= IMSI <= 15
        self.failUnless(imsi_regexp.match(imsi))

    def test_CardResetSettings(self):
        """Test for Card.ResetSettings"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("Untested")

    def test_CardSendATString(self):
        """Test for Card.SendATString"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("Untested")

    def test_CardSendPin(self):
        """Test for Card.SendPin"""
        raise unittest.SkipTest("Untested")

    def test_CardSendPuk(self):
        """Test for Card.SendPuk"""
        raise unittest.SkipTest("Untested")

    def test_CardSetCharset(self):
        """Test for Card.SetCharset"""
        charsets = ["IRA", "GSM", "UCS2"]
        # get the current charset
        charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)
        self.failUnlessIn(charset, charsets)
        # now pick a new charset
        new_charset = random.choice(charsets)
        while new_charset == charset:
            new_charset = random.choice(charsets)

        # set the charset to new_charset
        self.device.SetCharset(new_charset, dbus_interface=CRD_INTFACE)
        _charset = self.device.GetCharset(dbus_interface=CRD_INTFACE)
        # check that the new charset is the expected one
        self.assertEqual(new_charset, _charset)
        # leave everything as found
        self.device.SetCharset(charset, dbus_interface=CRD_INTFACE)

    def test_CardSupportedBandsProperty(self):
        """Test for Card.SupportedBands property"""
        bands = self.device.Get(CRD_INTFACE, 'SupportedBands',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        if not bands:
            raise unittest.SkipTest("Cannot be tested")

        self.failIfIn(MM_NETWORK_BAND_ANY, get_bands(bands))

    def test_CardSupportedModesProperty(self):
        """Test for Card.SupportedModes property"""
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        self.failIfIn(MM_NETWORK_MODE_ANY, get_network_modes(modes))

    # org.freedesktop.ModemManager.Modem.Gsm.Contacts tests
    def test_ContactsAdd(self):
        """Test for Contacts.Add"""
        name, number = "John", "+435443434343"
        # add a contact with ascii data
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # get the object via DBus and check that its data is correct
        _index, _name, _number = self.device.Get(index,
                                                 dbus_interface=CTS_INTFACE)
        self.assertEqual(name, _name)
        self.assertEqual(number, _number)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

    def test_ContactsAdd_UTF8_name(self):
        """Test for Contacts.Add"""
        name, number = u"中华人民共和", "+43544311113"
        # add a contact with UTF8 data
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # get the object via DBus and check that its data is correct
        _index, _name, _number = self.device.Get(index,
                                                 dbus_interface=CTS_INTFACE)
        self.assertEqual(name, _name)
        self.assertEqual(number, _number)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

    def test_ContactsDelete(self):
        """Test for Contacts.Delete"""
        name, number = "Juan", "+21544343434"
        # add a contact, and delete it
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # now delete it and check that its index is no longer present
        # if we list all the contacts
        self.device.Delete(index, dbus_interface=CTS_INTFACE)
        contacts = self.device.List(dbus_interface=CTS_INTFACE)
        self.assertNotIn(index, [c[0] for c in contacts])

    def test_ContactsEdit(self):
        """Test for Contacts.Edit"""
        name, number = "Eugenio", "+435345342121"
        new_name, new_number = "Eugenia", "+43542323122"
        # add a contact
        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        # edit it and get by index to check that the new values are set
        self.device.Edit(index, new_name, new_number,
                         dbus_interface=CTS_INTFACE)

        _index, _name, _number = self.device.Get(index,
                                                 dbus_interface=CTS_INTFACE)
        self.assertEqual(_name, new_name)
        self.assertEqual(_number, new_number)
        # leave everything as found
        self.device.Delete(_index, dbus_interface=CTS_INTFACE)

    def test_ContactsFindByName(self):
        """Test for Contacts.FindByName"""
        # add three contacts with similar names
        data = [('JohnOne', '+34656575757'), ('JohnTwo', '+34666575757'),
                ('JohnThree', '+34766575757')]
        indexes = [self.device.Add(name, number, dbus_interface=CTS_INTFACE)
                        for name, number in data]
        # now search by name and make sure the matches match
        search_data = [('John', 3), ('JohnT', 2), ('JohnOne', 1)]
        for name, expected_matches in search_data:
            contacts = self.device.FindByName(name, dbus_interface=CTS_INTFACE)
            self.assertEqual(len(contacts), expected_matches)

        for index in indexes:
            self.device.Delete(index, dbus_interface=CTS_INTFACE)

    def test_ContactsFindByNumber(self):
        """Test for Contacts.FindByNumber"""
        # add three contacts with similar numbers
        data = [('JohnOne', '+34656575757'), ('JohnTwo', '+34666575757'),
                ('JohnThree', '+34766575757')]
        indexes = [self.device.Add(name, number, dbus_interface=CTS_INTFACE)
                        for name, number in data]
        # now search by number and make sure the matches match
        search_data = [('575757', 3), ('66575757', 2), ('+34666575757', 1)]
        for number, expected_matches in search_data:
            contacts = self.device.FindByNumber(number,
                                                dbus_interface=CTS_INTFACE)
            self.assertEqual(len(contacts), expected_matches)

        for index in indexes:
            self.device.Delete(index, dbus_interface=CTS_INTFACE)

    def test_ContactsGet(self):
        """Test Contacts.Get"""
        name, number = "Mario", "+312232332"

        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        reply = self.device.Get(index, dbus_interface=CTS_INTFACE)

        self.assertIn(name, reply)
        self.assertIn(number, reply)
        self.assertIn(index, reply)

        self.device.Delete(index, dbus_interface=CTS_INTFACE)

    def test_ContactsGetCount(self):
        """Test for Contacts.GetCount"""
        count = self.device.GetCount(dbus_interface=CTS_INTFACE)
        contacts = self.device.List(dbus_interface=CTS_INTFACE)
        self.assertEqual(count, len(contacts))

    def test_ContactsGetCount_2(self):
        """Test for Contacts.GetCount"""
        count = self.device.GetCount(dbus_interface=CTS_INTFACE)
        index = self.device.Add("Boethius", "+21123322323",
                                dbus_interface=CTS_INTFACE)
        count2 = self.device.GetCount(dbus_interface=CTS_INTFACE)
        self.assertEqual(count + 1, count2)
        self.device.Delete(index, dbus_interface=CTS_INTFACE)

    def test_ContactsGetPhonebookSize(self):
        """Test for Contacts.GetPhonebookSize"""
        size = self.device.GetPhonebookSize(dbus_interface=CTS_INTFACE)
        self.failUnlessIsInstance(size, int)
        self.failUnless(size >= 200)

    def test_ContactsList(self):
        """Test for Contacts.List"""
        name, number = "Jauma", "+356456445654"

        index = self.device.Add(name, number, dbus_interface=CTS_INTFACE)
        reply = self.device.List(dbus_interface=CTS_INTFACE)

        found = False
        for contact in reply:
            if (index, name, number) == contact:
                found = True
                break

        self.failUnless(found)
        # leave everything as found
        self.device.Delete(index, dbus_interface=CTS_INTFACE)

    # org.freedesktop.ModemManager.Modem.Gsm.Network tests
    def test_NetworkGetApns(self):
        """Test for Network.GetApns"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("Untested")

    def test_NetworkGetBand(self):
        """Test for Network.GetBand"""
        band = self.device.GetBand(dbus_interface=NET_INTFACE)
        self.failUnlessIsInstance(band, (dbus.UInt32, int))
        self.failUnless(band > 0)

    def test_NetworkGetNetworkMode(self):
        """Test for Network.GetNetworkMode"""
        mode = self.device.GetNetworkMode(dbus_interface=NET_INTFACE)
        self.failUnlessIsInstance(mode, (dbus.UInt32, int))
        # currently goes between 0 and 0x400
        self.failUnless(mode >= 0 and mode <= 0x400)

    def test_NetworkGetRegistrationInfo(self):
        """Test for Network.GetRegistrationInfo"""
        reply = self.device.GetRegistrationInfo(dbus_interface=NET_INTFACE)
        status, numeric_oper = reply[:2]
        # we must be registered to our home network or roaming
        self.failUnlessIn(status, [1, 5])
        # get the IMSI and check that we are connected to a network
        # with a netid that matches the beginning of our IMSI
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
        # we should be registered with our home network
        self.failUnless(imsi.startswith(numeric_oper))

    def test_NetworkGetRoamingIDs(self):
        """Test for Network.GetRoamingIDs"""
        if not TEST_WADER_EXTENSIONS:
            raise unittest.SkipTest(GENERIC_SKIP_MSG)

        raise unittest.SkipTest("This method is device-dependent")

    def test_NetworkGetSignalQuality(self):
        """Test for Network.GetSignalQuality"""
        quality = self.device.GetSignalQuality(dbus_interface=NET_INTFACE)
        self.failUnlessIsInstance(quality, (dbus.UInt32, int))
        self.failUnless(quality >= 1 and quality <= 100)

    def test_NetworkScan(self):
        """Test for Network.Scan"""
        # get the first five digits of the IMSI and check that its around
        imsi = self.device.GetImsi(dbus_interface=CRD_INTFACE)
        # potentially long operation, increasing timeout to 45
        networks = self.device.Scan(dbus_interface=NET_INTFACE, timeout=45)
        home_network_found = False
        for network in networks:
            if network['operator-num'] == imsi[:5]:
                home_network_found = True
                break

        # our home network has to be around
        # unless we are roaming ;)
        self.assertEqual(home_network_found, True)

    def test_NetworkSetApn(self):
        """Test for Network.SetApn"""
        raise unittest.SkipTest("Untested")

    def test_NetworkSetBand(self):
        """Test for Network.SetBand"""
        _bands = self.device.Get(CRD_INTFACE, 'SupportedBands',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        if not _bands:
            raise unittest.SkipTest("Cannot be tested")

        bands = get_bands(_bands)

        while bands:
            band = bands.pop()
            self.device.SetBand(band)
            _band = self.device.GetBand()
            self.failUnless(band & _band)

        # leave it in BAND_ANY and give it some seconds to settle
        self.device.SetBand(MM_NETWORK_BAND_ANY)
        time.sleep(5)

    def test_NetworkSetAllowedMode(self):
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        for net_mode in get_network_modes(modes):
            mode = convert_network_mode_to_allowed_mode(net_mode)
            if mode is None:
                # could not convert it to allowed_mode
                continue

            self.device.SetAllowedMode(mode)
            allowed_mode = self.device.Get(NET_INTFACE, 'AllowedMode',
                                        dbus_interface=dbus.PROPERTIES_IFACE)
            self.assertEqual(mode, allowed_mode)

        # leave it in MODE_ANY and give it some seconds to settle
        self.device.SetAllowedMode(MM_ALLOWED_MODE_ANY)
        time.sleep(5)

    def test_NetworkSetNetworkMode(self):
        """Test for Network.SetNetworkMode"""
        modes = self.device.Get(CRD_INTFACE, 'SupportedModes',
                                dbus_interface=dbus.PROPERTIES_IFACE)
        if not modes:
            raise unittest.SkipTest("Cannot be tested")

        for mode in get_network_modes(modes):
            self.device.SetNetworkMode(mode)
            _mode = self.device.GetNetworkMode()
            self.assertEqual(mode, _mode)

        # leave it in MODE_ANY and give it some seconds to settle
        self.device.SetNetworkMode(MM_NETWORK_MODE_ANY)
        time.sleep(5)

    def test_NetworkSetRegistrationNotification(self):
        """Test for Network.SetRegistrationNotification"""
        raise unittest.SkipTest("Untested")

    def test_NetworkSetInfoFormat(self):
        """Test for Network.SetInfoFormat"""
        raise unittest.SkipTest("Untested")

    def test_NetworkRegister(self):
        """Test for Network.Register"""
        raise unittest.SkipTest("Untested")

    def test_NetworkAccessTechnologyProperty(self):
        """Test for Modem.Gsm.AccessTechnology property"""
        access_tech = self.device.Get(NET_INTFACE, "AccessTechnology",
                            dbus_interface=dbus.PROPERTIES_IFACE)
        self.failUnlessIn(access_tech, MM_GSM_ACCESS_TECHNOLOGIES)

    def test_NetworkAllowedModeProperty(self):
        """Test for Modem.Gsm.AllowedMode property"""
        # tested in NetworkSetAllowedMode
        pass

    # org.freedesktop.ModemManager.Modem.Gsm.Simple tests
    def test_SimpleConnect(self):
        """Test for Simple.Connect"""
        raise unittest.SkipTest("Untested")

    def test_SimpleDisconnect(self):
        """Test for Simple.Disconnect"""
        raise unittest.SkipTest("Untested")

    def test_SimpleGetStatus(self):
        """Test for Simple.GetStatus"""
        status = self.device.GetStatus(dbus_interface=SPL_INTFACE)
        self.failUnless('band' in status)
        self.failUnless('signal_quality' in status)
        self.failUnless('operator_code' in status)
        self.failUnless('operator_name' in status)
        self.failUnlessIsInstance(status['operator_name'], basestring)
        self.failUnlessIsInstance(status['operator_code'], basestring)
        self.failUnlessIsInstance(status['signal_quality'], dbus.UInt32)
        self.failUnlessIsInstance(status['band'], dbus.UInt32)

    # org.freedesktop.ModemManager.Modem.Gsm.SMS tests
    def test_SmsDelete(self):
        """Test for Sms.Delete"""
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
        """Test for Sms.Delete"""
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
        """Test for Sms.Get"""
        sms = {'number': '+33646754145', 'text': 'get test'}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)
        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])
        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

    def test_SmsGetMultiparted(self):
        """Test for Sms.Get"""
        sms = {'number': '+34622754135',
               'text': """test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           test_SmsGetMultiparted test_SmsGetMultiparted
                           """}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)
        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])
        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

    def test_SmsGetSmsc(self):
        """Test for Sms.GetSmsc"""
        smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)
        self.failUnless(smsc.startswith('+'))

    def test_SmsGetFormat(self):
        """Test for Sms.GetFormat"""
        fmt = self.device.GetFormat(dbus_interface=SMS_INTFACE)
        self.failUnlessIn(fmt, [0, 1])

    def test_SmsList(self):
        """Test for Sms.List"""
        sms = {'number': '+33622754135', 'text': 'list test'}
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        messages = self.device.List(dbus_interface=SMS_INTFACE)
        # now check that the indexes are present in a List

        sms_found = False
        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
                break
        self.assertEqual(sms_found, True)

        # leave everything as found
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

    def test_SmsList_2(self):
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
        # and check that the size has increased just three
        self.assertEqual(size_before + 3, size_after)
        # leave everything as found
        for index in indexes:
            self.device.Delete(index, dbus_interface=SMS_INTFACE)

    def test_SmsListMultiparted(self):
        """Test for Sms.List"""
        sms = {'number': '+34622754135',
               'text': """test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted
                           test_SmsListMultiparted test_SmsListMultiparted"""}
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        # now check that the indexes are present in a List
        messages = self.device.List(dbus_interface=SMS_INTFACE)
        sms_found = False

        for msg in messages:
            if msg['index'] == indexes[0]:
                sms_found = True
                break

        self.assertEqual(sms_found, True)
        # leave everything as found
        self.device.Delete(indexes[0], dbus_interface=SMS_INTFACE)

    def test_SmsListMultiparted_2(self):
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
        # and check that the size has increased just three
        self.assertEqual(size_before + 4, size_after)

        # leave everything as found
        for index in indexes:
            self.device.Delete(index, dbus_interface=SMS_INTFACE)

    def test_SmsSave(self):
        """Test for Sms.Save"""
        sms = {'number': '+34645454445', 'text': 'save test'}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)
        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])
        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

    def test_SmsSaveMultiparted(self):
        """Test for Sms.Save"""
        sms = {'number': '+34622754135',
               'text': """test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           test_SmsSaveMultiparted test_SmsSaveMultiparted
                           """}
        # save the message, get it by index, and check its values match
        indexes = self.device.Save(sms, dbus_interface=SMS_INTFACE)
        _sms = self.device.Get(indexes[0], dbus_interface=SMS_INTFACE)
        self.assertEqual(sms['number'], _sms['number'])
        self.assertEqual(sms['text'], _sms['text'])
        # leave everything as found
        self.device.Delete(_sms['index'], dbus_interface=SMS_INTFACE)

    def test_SmsSend(self):
        """Test for Sms.Send"""
        raise unittest.SkipTest("Not ready")
        #number = config.get('test', 'phone')
        #if not number:
        #    raise unittest.SkipTest("Cannot run this test without a number")

        #d = defer.Deferred()
        #sm = None  # SignalMatch
        #sms = {'number' : number, 'text' : 'send test'}

        #def on_sms_received_cb(index):
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

        #sm = self.device.connect_to_signal("SMSReceived", on_sms_received_cb,
        #                                   dbus_interface=SMS_INTFACE)

        #self.device.Send(sms, dbus_interface=SMS_INTFACE,
        #                 # we are not interested in the callback
        #                 reply_handler=lambda indexes: None,
        #                 error_handler=d.errback)

        #return d

    def test_SmsSendFromStorage(self):
        """Test for Sms.SendFromStorage"""
        raise unittest.SkipTest("Not ready")
        #number = config.get('test', 'phone')
        #if not number:
        #    raise unittest.SkipTest("Cannot run this test without a number")
        #d = defer.Deferred()
        #sm = None  # SignalMatch
        #sms = {'number' : number, 'text' : 'send from storage test' }

        #def on_sms_received_cb(index):
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
        #                                # we are not interested in the callback
        #                                reply_handler=lambda indexes: None,
        #                                error_handler=d.errback)

        #sm = self.device.connect_to_signal("SMSReceived", on_sms_received_cb)

        ## save the message and send it to ourselves
        #self.device.Save(sms, dbus_interface=SMS_INTFACE,
        #                 reply_handler=on_sms_saved_cb,
        #                 error_handler=d.errback)

        #return d

    def test_SmsSetFormat(self):
        """Test for Sms.SetFormat"""
        # set text format and check immediately that a
        # GetFormat call returns 1
        try:
            self.device.SetFormat(1, dbus_interface=SMS_INTFACE)
        except dbus.DBusException, e:
            if 'CMSError303' in get_dbus_error(e):
                # MD300 doesn't allows to set text format
                return
        else:
            fmt = self.device.GetFormat(dbus_interface=SMS_INTFACE)
            self.assertEqual(fmt, 1)
            # leave format as found
            self.device.SetFormat(0, dbus_interface=SMS_INTFACE)

    def test_SmsSetIndication(self):
        """Test for Sms.SetIndication"""
        # simple test for AT+CNMI, if this set command fails the
        # AT string needs to be changed. The reason the test is so simple
        # is because there's no GetIndication command in the spec, and I
        # didn't feel like coordinating an extension with the MM guys.
        # self.device.SetIndication(2, 1, 0, 1, 0)

    def test_SmsSetSmsc(self):
        """Test for Sms.SetSmsc"""
        bad_smsc = '+3453456343'
        # get the original SMSC and memoize it
        smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)
        # set the SMSC to a bad value and read it to confirm it worked
        self.device.SetSmsc(bad_smsc, dbus_interface=SMS_INTFACE)
        _bad_smsc = self.device.GetSmsc(dbus_interface=SMS_INTFACE)
        # bad_smsc has been correctly set
        self.assertEqual(bad_smsc, _bad_smsc)
        # leave everything as found
        self.device.SetSmsc(smsc, dbus_interface=SMS_INTFACE)
