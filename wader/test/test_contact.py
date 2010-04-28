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
"""Unittests for the contact module"""

from twisted.trial import unittest
from twisted.internet import defer

from wader.common.contact import ContactStore

SKIP_TEST = False
try:
    from wader.plugins.sqlite_provider import sqlite_provider, SQLContact
    sqlite_provider.initialize(dict(path=':memory:'))
    providers = [sqlite_provider]
except ImportError:
    SKIP_TEST = True


store = None
numtests = None
executed = None


class TestContactStore(unittest.TestCase):
    """Tests for wader.common.contact.ContactStore"""
    skip = "No contact providers found" if SKIP_TEST else None

    def setUpOnce(self):
        global store, numtests
        if store is None:
            store = ContactStore()
            map(store.add_provider, providers)

        if numtests is None:
            numtests = len([m for m in dir(self) if m.startswith('test_')])

        self.store = store
        return defer.succeed(True)

    def tearDownOnce(self):
        global store
        return defer.maybeDeferred(store.close)

    def setUp(self):
        return self.setUpOnce()

    def tearDown(self):
        global numtests, executed
        if executed is None:
            executed = 1
        else:
            executed += 1

        if numtests == executed:
            return self.tearDownOnce()

        return defer.succeed(True)

    def test_add_contact(self):
        c = SQLContact("John", "+433333223", email="john@mail.net")
        contact = self.store.add_contact(c)
        # now check that the contact is present
        contacts = self.store.list_contacts()
        self.assertIn(contact, contacts)
        # leave it as we found it
        self.store.remove_contact(contact)

    def test_remove_contact(self):
        # add a contact and remove it
        c = SQLContact("John", "+433333223", email="john@mail.net")
        contact = self.store.add_contact(c)
        self.store.remove_contact(contact)
        # now check that is not present anymore
        contacts = list(self.store.list_contacts())
        self.assertNotIn(contact, contacts)

    def test_list_contacts(self):
        # add a couple of contacts and check they are present
        contact1 = self.store.add_contact(
                SQLContact("Daniel", "+213333223", email="dan@mail.net"))
        contact2 = self.store.add_contact(
                SQLContact("Andy", "+113333223", email="andy@mail.net"))

        contacts = self.store.list_contacts()
        self.assertIn(contact1, contacts)
        self.assertIn(contact2, contacts)
        # leave it as we found it
        self.store.remove_contact(contact1)
        self.store.remove_contact(contact2)

    def test_find_contacts_by_name(self):
        contact1 = self.store.add_contact(
                SQLContact("Daniel", "+213333223", email="dan@mail.net"))
        matches = self.store.find_contacts_by_name("Daniel")
        self.assertIn(contact1, matches)
        # leave it as we found it
        self.store.remove_contact(contact1)

    def test_find_contacts_by_number_full_match(self):
        contact1 = self.store.add_contact(
                SQLContact("Daniel", "+213333223", email="dan@mail.net"))
        matches = self.store.find_contacts_by_number("+213333223")
        self.assertIn(contact1, matches)
        # leave it as we found it
        self.store.remove_contact(contact1)

    def test_find_contacts_by_number_uk_match(self):
        contact1 = self.store.add_contact(
                SQLContact("Daniel", "073333223", email="dan@mail.net"))
        matches = self.store.find_contacts_by_number("+4473333223")
        self.assertIn(contact1, matches)
        # leave it as we found it
        self.store.remove_contact(contact1)

    def test_find_contacts_by_number_ie_match(self):
        contact1 = self.store.add_contact(
                SQLContact("Daniel", "081234567", email="dan@mail.net"))
        matches = self.store.find_contacts_by_number("+35381234567")
        self.assertIn(contact1, matches)
        # leave it as we found it
        self.store.remove_contact(contact1)
