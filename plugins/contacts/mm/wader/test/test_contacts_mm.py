# -*- coding: utf-8 -*-
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Pablo Mart??
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
"""Unittests for the ModemManager IContactProvider"""

import time

import dbus
import dbus.mainloop.glib
from twisted.trial import unittest
from twisted.internet import defer
from twisted.python import log

from wader.plugins.mm_provider import mm_provider, MMContact
from wader.common.consts import (WADER_SERVICE, WADER_INTFACE, WADER_OBJPATH,
                                 MDM_INTFACE, CRD_INTFACE)

CARD_PIN = "0000"


class TestModemManagerContactProvider(unittest.TestCase):
    """Test for the ModemManager IContactProvider"""

    def setUpClass(self):
        d = defer.Deferred()
        self.provider = mm_provider

        loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=loop)

        def enable_device_cb():
            time.sleep(1)
            self.provider.initialize(dict(opath=self.opath))
            d.callback(True)

        def enable_device_eb(e):
            error = e.get_dbus_message()
            if 'SimPinRequired' in error:
                pin = CARD_PIN
                self.device.SendPin(pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=enable_device_cb,
                                    error_handler=log.err)
            else:
                raise unittest.SkipTest("Cannot handle error %s" % error)

        def get_device_from_opath(opaths):
            if not len(opaths):
                raise unittest.SkipTest("Can't run this test without devices")

            self.opath = opaths[0]

            self.device = bus.get_object(WADER_SERVICE, self.opath)
            self.device.Enable(True, dbus_interface=MDM_INTFACE,
                               reply_handler=enable_device_cb,
                               error_handler=enable_device_eb)

        obj = bus.get_object(WADER_SERVICE, WADER_OBJPATH)
        obj.EnumerateDevices(dbus_interface=WADER_INTFACE,
                             reply_handler=get_device_from_opath,
                             error_handler=log.err)
        return d

    def tearDownClass(self):
        # leave everything as found
        self.device.Enable(False, dbus_interface=MDM_INTFACE)
        self.provider.close()

    def test_add_contact(self):
        name, number = 'John', '+4324343232'
        contact = self.provider.add_contact(MMContact(name, number))

        self.failUnlessIsInstance(contact, MMContact)
        self.failUnlessEqual(contact.name, name)
        self.failUnlessEqual(contact.number, number)
        # leave everything as found
        self.provider.remove_contact(contact)

    def test_edit_contact(self):
        name, number = 'John', '+4324343232'
        contact = self.provider.add_contact(MMContact(name, number))

        contact.name = 'Daniel'
        contact.number = '+1212121212'

        self.provider.edit_contact(contact)
        # now do a list and check the new values are there
        found = False
        for c in self.provider.list_contacts():
            if c.name == 'Daniel' and c.number == '+1212121212':
                found = True
                break

        self.assertEqual(found, True)
        # leave everything as found
        self.provider.remove_contact(contact)

    def test_find_contacts_by_name(self):
        name, number = 'James', '+322323222'

        contact = self.provider.add_contact(MMContact(name, number))
        contacts = list(self.provider.find_contacts_by_name("Jam"))
        self.failUnlessIn(contact, contacts)
        self.provider.remove_contact(contact)

    def test_find_contacts_by_number(self):
        name, number = 'James', '+322323222'

        contact = self.provider.add_contact(MMContact(name, number))
        contacts = list(self.provider.find_contacts_by_number("+322323222"))
        self.failUnlessIn(contact, contacts)
        self.provider.remove_contact(contact)

    def test_list_contacts(self):
        added_contacts = []
        name, number = 'Laura', '+223232222'

        append = added_contacts.append
        append(self.provider.add_contact(MMContact(name, number)))
        found = False
        for contact in self.provider.list_contacts():
            if contact.name == name and contact.number == number:
                found = True
                break

        self.assertEqual(found, True)
        map(self.provider.remove_contact, added_contacts)

    def test_remove_contact(self):
        # add a contact, remove it, and make sure is no longer present
        name, number = 'Natasha', '+322322111'
        contact = self.provider.add_contact(MMContact(name, number))
        # consume the generator and make it a list
        contacts = list(self.provider.list_contacts())
        self.failUnlessIn(contact, contacts)
        self.provider.remove_contact(contact)
        # leave everything as found
        self.failIfIn(contact, list(self.provider.list_contacts()))


