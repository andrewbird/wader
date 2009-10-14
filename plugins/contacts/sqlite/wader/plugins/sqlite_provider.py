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

from wader.common.contact import Contact
from wader.common.interfaces import IContactProvider

DATA_SCHEMA = """
create table contacts (
    id     integer primary key,
    name   text,
    number text,
    email  text)
"""

class SQLContact(Contact):
    def __init__(self, name, number, index=None, email=""):
        super(SQLContact, self).__init__(name, number, index)
        self.email = email

    def __eq__(self, other):
        return self.index == other.index

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_row(cls, r):
        """Returns a `SQLContact` instance out of ``t``"""
        # (1, u'pablo', u'+234342342', u'foo@foo.com')
        return cls(r[1], r[2], index=r[0], email=r[3])


class SQLiteContactProvider(object):
    """SQLite IContactProvider backend"""
    implements(IPlugin, IContactProvider)

    name = "SQLite contact backend"
    author = u"Pablo Martí"
    version = "0.1"

    def __init__(self):
        self.cursor = None

    def initialize(self, init_obj):
        conn = sqlite3.connect(init_obj['path'], isolation_level=None)
        self.cursor = conn.cursor()
        try:
            self.cursor.execute(DATA_SCHEMA)
        except sqlite3.OperationalError:
            # database was present
            pass

    def close(self):
        self.cursor.close()

    def add_contact(self, contact):
        """See :meth:`IContactProvider.add_contact`"""
        if not isinstance(contact, SQLContact):
            return

        args = (None, contact.name, contact.number, contact.email)
        self.cursor.execute("insert into contacts values(?, ?, ?, ?)", args)
        return SQLContact(args[1], args[2], email=args[3],
                          index=self.cursor.lastrowid)

    def find_contacts(self, pattern):
        """See :meth:`IContactProvider.find_contacts`"""
        sql = "select * from contacts where name like ?"
        self.cursor.execute(sql, ("%%%s%%" % pattern,))
        return (SQLContact.from_row(r) for r in self.cursor.fetchall())

    def list_contacts(self):
        """See :meth:`IContactProvider.list_contacts`"""
        self.cursor.execute("select * from contacts")
        return (SQLContact.from_row(r) for r in self.cursor.fetchall())

    def remove_contact(self, contact):
        """See :meth:`IContactProvider.remove_contact`"""
        if isinstance(contact, SQLContact):
            # filter out non SQLContacts
            sql = "delete from contacts where id=?"
            self.cursor.execute(sql, (contact.index,))


sqlite_provider = SQLiteContactProvider()

