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
"""
Unittests for the SIM card

You need to be authenticated before running the test suite
"""

import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

from twisted.trial.unittest import TestCase, SkipTest
from twisted.python import log

import wader.common.aterrors as E
from wader.common.startup import attach_to_serial_port
from wader.common.config import config
from wader.common.contact import Contact
from wader.common.oal import osobj
from wader.common.middleware import BasicNetworkOperator

class TestSIMCard(TestCase):
    """Test for SIM card functionality"""

    def setUp(self):
        self.sconn = None
        self.serial = None
        self.device = None

        try:
            d = osobj.hw_manager.get_devices()
            def get_device_cb(devices):
                device = devices[0]
                self.device = attach_to_serial_port(device)
                self.sconn = self.device.sconn
                d2 = self.device.initialize()
                d2.addCallback(lambda ign: self.sconn.delete_all_contacts())
                d2.addCallback(lambda ign: self.sconn.delete_all_sms())
                return d2

            d.addCallback(get_device_cb)
            return d
        except:
            log.err()

    def tearDown(self):
        return self.device.close()

    def test_add_contact_with_index(self):
        """
        Test adding a contact specifying an index
        """
        contact = Contact("Vodafone", "+34670979779", 1)
        d = self.sconn.add_contact(contact)
        def process_contact_bak(ignored):
            d2 = self.sconn.get_contact_by_index(contact.index)
            d2.addCallback(lambda contact_bak2:
                           self.assertEqual(contact, contact_bak2))
            return self.sconn.delete_contact(contact.index)

        d.addCallback(process_contact_bak)
        return d

    def test_add_contact_without_index(self):
        """
        Test adding a contact without specifying an index
        """
        contact = Contact("Vodafone", "+34670979779")
        d = self.sconn.add_contact(contact)
        def process_contact_bak(index):
            self.assertEqual(index, 1)
            d2 = self.sconn.get_contact_by_index(index)
            d2.addCallback(lambda contact_bak2:
                           self.assertEqual(contact, contact_bak2))
            d2.addCallback(lambda ignored: self.sconn.delete_contact(index))
            return d2

        d.addCallback(process_contact_bak)
        return d

    def test_change_pin(self):
        """
        Test that change pin works
        """
        if not config:
            raise SkipTest("Not config")

        oldpin = config.get('test', 'pin', '0000')
        newpin = '1444'
        def change_pin_cb(ignored):
            # the pin has changed now, lets check if it really changed
            # by disabling the new pin
            d2 = self.sconn.enable_pin(newpin, False)
            d2.addCallback(lambda ignored: self.sconn.enable_pin(newpin, True))
            d2.addCallback(lambda ignored:
                            self.sconn.change_pin(newpin, oldpin))
            return d2

        d = self.sconn.change_pin(oldpin, newpin)
        d.addCallback(change_pin_cb)
        return d

    def test_change_pin_with_bad_pin_raises_error(self):
        """
        Test that change pin works
        """
        badoldpin = '5555'
        newpin = '1444'
        d = self.sconn.change_pin(badoldpin, newpin)
        return self.failUnlessFailure(d, E.GenericError, E.IncorrectPassword)

    def test_delete_contact(self):
        """
        Test deleting a contact
        """
        contact = Contact("Vodafoo", "+3467456654", 2)
        d = self.sconn.add_contact(contact)
        def callback(ignored):
            self.sconn.delete_contact(contact.index)
            d2 = self.sconn.get_used_contact_ids()
            d2.addCallback(lambda val: self.failIfIn(contact.index, val))
            return self.sconn.delete_contact(contact.index)

        d.addCallback(callback)
        return d

    def test_disable_and_enable_pin(self):
        """
        Tests that disable_pin and enable_pin works

        Also tests get_pin_status
        """
        if not config:
            raise SkipTest("Not config")

        pin = config.get('test', 'pin', '0000')
        def disable_pin_cb(ignored):
            self.sconn.get_pin_status().addCallback(lambda active:
                                self.assertEqual(active, 0))
            d2 = self.sconn.enable_pin(pin, True)
            d2.addCallback(lambda _:
                    self.sconn.get_pin_status().addCallback(lambda active:
                                                self.assertEqual(active, 1)))
            return d2

        d = self.sconn.enable_pin(pin, False)
        d.addCallback(disable_pin_cb)
        return d

    def test_find_contact(self):
        """
        Test finding a contact
        """
        contact = Contact("Vodafone", "+34670979779", 1)
        pattern = "Vodafo"
        self.sconn.add_contact(contact)
        d = self.sconn.find_contacts(pattern)
        def process_contact(contact_found):
            self.assertEqual(contact, contact_found[0])
            return self.sconn.delete_contact(contact.index)

        d.addCallback(process_contact)
        return d

    def test_get_charsets(self):
        """
        Test that we can get the charsets in the card

        At least the IRA charset must be present
        """
        def charset_cb(charsets):
            self.assertIn('IRA', charsets)
            #self.assertIn('GSM', charsets)
            #self.assertIn('UCS2', charsets)

        d = self.sconn.get_charsets()
        d.addCallback(charset_cb)
        return d

    def test_get_contacts(self):
        """
        Test that get_contacts works

        We add a couple of contacts and they must appear in get_contacts resp
        """
        contact = Contact("Vodafone", "+34670979779", 3)
        contact2 = Contact("Vodafoonz", "+34670923432", 4)
        self.sconn.add_contact(contact)
        self.sconn.add_contact(contact2)
        def get_contacts_cb(contacts):
            self.failUnlessIn(contact, contacts)
            self.failUnlessIn(contact2, contacts)

            d = self.sconn.delete_contact(contact.index)
            d.addCallback(lambda _: self.sconn.delete_contact(contact2.index))
            return d

        d = self.sconn.get_contacts()
        d.addCallback(get_contacts_cb)
        return d

    def test_get_contacts_empty(self):
        """
        Test that get_contacts returns an empty list when there's no contacts
        """
        d = self.sconn.get_contacts()
        d.addCallback(lambda resp: self.assertEqual(resp, []))
        return d

    def test_get_imei(self):
        """
        Test getting IMEI

        The IMEI is supposed to start with 35
        """

        d = self.sconn.get_imei()
        d.addCallback(lambda imei: self.failUnless(imei.startswith('35')))
        return d

    def test_get_imsi(self):
        """
        Test getting IMSI

        The IMSI is supposed to start with 21401
        """

        d = self.sconn.get_imsi()
        d.addCallback(lambda imsi: self.failUnless(imsi.startswith('21401')))
        return d

    def test_set_and_get_netreg_notifications(self):
        """
        Test that setting and getting netreg notifications works
        """
        def set_netreg_notification_cb(ignored):
            d2 = self.sconn.get_netreg_status()
            d2.addCallback(lambda resp: self.assertEqual(resp[0], 1))
            return d2

        d = self.sconn.set_netreg_notification()
        d.addCallback(set_netreg_notification_cb)
        return d

    def test_get_card_version(self):
        """
        Test that card version can be get

        Only checks that sim returns a valid non-empty string.
        """
        d = self.sconn.get_card_version()
        def get_card_version_cb(version):
            self.failUnless(isinstance(version, str))
            self.failUnless(len(version) > 0)

        d.addCallback(get_card_version_cb)
        return d

    def test_get_manufacturer_name(self):
        """
        Test that card manufacturer name can be get

        Only checks that sim returns a valid non-empty string.
        """
        d = self.sconn.get_manufacturer_name()
        def get_manufacturer_name_cb(name):
            self.failUnless(isinstance(name, str))
            self.failUnless(len(name) > 0)

        d.addCallback(get_manufacturer_name_cb)
        return d

    def test_get_network_info(self):
        """
        Test AT+COPS?
        """
        d = self.sconn.get_network_info()
        def process_netinfo(netinfo):
            """
            What can we test here? Just that we're registered
            """
            netname, cell_type = netinfo
            self.assertIn(cell_type, ['GPRS', '3G'])
            if isinstance(netname, int):
                d = self.sconn.get_imsi()
                d.addCallback(lambda imsi: self.assertEqual(imsi[:5], netname))
                return d

        d.addCallback(process_netinfo)
        return d

    def test_get_network_names(self):
        """
        Test AT+COPS=?

        We're gonna check that an operator that starts with my IMSI is present
        """
        def get_imsi_cb(imsi):
            oper = BasicNetworkOperator(int(imsi[:5]))
            d = self.sconn.get_network_names()
            d.addCallback(lambda opers: self.assertIn(oper, opers))
            return d

        d = self.sconn.get_imsi()
        d.addCallback(get_imsi_cb)
        return d

    def test_get_roaming_ids(self):
        """
        Test AT+CPOL?

        We'll test that we're receiving a valid list of BasicNetworkOperator
        """
        d = self.sconn.get_roaming_ids()
        def process_rids(rids):
            self.failUnless(len(rids) > 1)
            self.failUnless(isinstance(rids[0], BasicNetworkOperator))

        d.addCallback(process_rids)
        return d

    def test_get_signal_quality(self):
        """
        Test the signal quality

        We cannot really test much here as the RSSI is not deterministic
        """
        d = self.sconn.get_signal_quality()
        def process_rssi(rssi):
            self.failUnless(isinstance(rssi, int))
            self.failUnless(rssi >= 0)

        d.addCallback(process_rssi)
        return d

    def test_get_smsc(self):
        """
        Test getting SMSC
        """
        if not config:
            raise SkipTest("Not config")

        goodsmsc = config.get('test', 'smsc', '+34607003110')
        d = self.sconn.get_smsc()
        d.addCallback(lambda smsc: self.assertEqual(smsc, goodsmsc))
        return d

    def test_set_charset(self):
        """
        Test the we can set the character set

        We set it to IRA, check that actually is stored as IRA, and then we
        set it back to UCS2 and we check it again
        """
        if self.device.sim.charset not in 'UCS2':
            raise SkipTest("Not for this device")

        d = self.sconn.set_charset('IRA')
        def set_charset_cb(ignored):
            self.sconn.get_charset().addCallback(lambda charset:
                                        self.assertEqual(charset, 'IRA'))
            self.sconn.set_charset('UCS2')
            d = self.sconn.get_charset()
            d.addCallback(lambda charset: self.assertEqual(charset, 'UCS2'))
            return d

        d.addCallback(set_charset_cb)
        return d

    def test_set_network_info_format_numeric(self):
        """
        Test that setting the network info format to numeric works
        """
        self.sconn.set_network_info_format()
        d = self.sconn.get_network_info()
        d.addCallback(lambda netinfo:
                      self.assertTrue(isinstance(netinfo[0], int)))
        return d

    def test_set_network_info_format_alphanumeric(self):
        """
        Test that setting the network info format to alphanumeric works
        """
        self.sconn.set_network_info_format(0, 0)
        d = self.sconn.get_network_info()
        d.addCallback(lambda netinfo:
                      self.assertTrue(isinstance(netinfo[0], str)))
        return d

    def test_set_smsc(self):
        """
        Test that the SMSC can be set

        We set it to a "bad" SMSC, check that it was effectively changed and
        then we set the "good" SMSC again, checking again that the stored
        SMSC is the "good" one
        """
        if not config:
            raise SkipTest("Not config")

        bogus_smsc = '+34646456451'
        good_smsc = config.get('test', 'smsc', '+34607003110')
        def process_smsc(ignored):
            d2 = self.sconn.get_smsc()
            d2.addCallback(lambda smsc: self.assertEqual(smsc, bogus_smsc))
            d2.addCallback(lambda _: self.sconn.set_smsc(good_smsc))
            return d2

        d = self.sconn.set_smsc(bogus_smsc)
        d.addCallback(process_smsc)
        return d

