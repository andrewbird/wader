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

import sqlite3

from zope.interface import implements
from twisted.plugin import IPlugin

from wader.common.provider import Contact, ContactProvider
from wader.common.interfaces import IContactProvider

class SQLContact(Contact):
    """I represent a contact in the DB"""

    def __eq__(self, other):
        return self.index == other.index

    def __ne__(self, other):
        return not self.__eq__(other)


class SQLiteContactProvider(object):
    """SQLite IContactProvider backend"""

    implements(IPlugin, IContactProvider)
    name = "SQLite contact backend"
    author = u"Pablo Martí"
    version = "0.1"

    def __init__(self):
        self.provider = None

    def initialize(self, init_obj):
        self.provider = ContactProvider(init_obj['path'])

    def close(self):
        return self.provider.close()

    def add_contact(self, contact):
        """See :meth:`IContactProvider.add_contact`"""
        if not isinstance(contact, SQLContact):
            return

        return self.provider.add_contact(contact)

    def find_contacts(self, pattern):
        """See :meth:`IContactProvider.find_contacts`"""
        return self.provider.find_contacts(pattern)

    def list_contacts(self):
        """See :meth:`IContactProvider.list_contacts`"""
        return self.provider.list_contacts()

    def remove_contact(self, contact):
        """See :meth:`IContactProvider.remove_contact`"""
        if isinstance(contact, SQLContact):
            # filter out non SQLContacts
            return self.provider.remove_contact(contact)


sqlite_provider = SQLiteContactProvider()
