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
"""Unittests for the ZYB IContactProvider"""

from twisted.trial import unittest

from wader.plugins.zyb_provider import zyb_provider, ZYBContact

class TestZYBContactProvider(unittest.TestCase):
    """Test for the ZYB IContactProvider"""

    def setUpClass(self):
        self.provider = zyb_provider
        self.provider.initialize(dict(username='warptest',
                                      password='warptest'))

    def tearDownClass(self):
        # leave everything as found
        self.provider.close()

    def test_add_contact(self):
        name, number = 'John', '+4324343232'
        contact = self.provider.add_contact(ZYBContact(name, number))

        self.failUnlessIsInstance(contact, ZYBContact)
        self.failUnlessEqual(contact.name, name)
        self.failUnlessEqual(contact.number, number)
        # leave everything as found
        self.provider.remove_contact(contact)

    def test_find_contacts(self):
        name, number = 'James', '+322323222'

        contact = self.provider.add_contact(ZYBContact(name, number))
        contacts = list(self.provider.find_contacts("Jam"))

        self.failUnlessIn(contact, contacts)
        self.provider.remove_contact(contact)

    def test_list_contacts(self):
        added_contacts = []
        name, number = 'Laura', '+223232222'

        append = added_contacts.append
        append(self.provider.add_contact(ZYBContact(name, number)))

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
        contact = self.provider.add_contact(ZYBContact(name, number))
        # consume the generator and make it a list
        contacts = list(self.provider.list_contacts())

        self.failUnlessIn(contact, contacts)
        self.provider.remove_contact(contact)
        # leave everything as found
        self.failIfIn(contact, list(self.provider.list_contacts()))


