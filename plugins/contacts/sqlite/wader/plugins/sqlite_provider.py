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
from wader.common.encoding import to_u
from wader.common.interfaces import IContactProvider
from wader.common.utils import get_value_and_pop

contact_SCHEMA = """
create table contact (
    id integer primary key autoincrement,
    name text not null,
    number text not null,
    email text,
    picture blob);

create table version (
    version integer default 1);
"""

class SQLContact(Contact):
    """I am a :class:`Contact` with email and a picture"""

    def __init__(self, *args, **kw):
        self.email = to_u(get_value_and_pop(kw, 'email', ''))
        self.picture = get_value_and_pop(kw, 'picture', '')
        super(SQLContact, self).__init__(*args, **kw)

    @classmethod
    def from_row(cls, row):
        """Returns a :class:`Contact` out of ``row``"""
        return cls(row[1], row[2], index=row[0], email=row[3], picture=row[4])

    def to_row(self):
        """Returns a tuple object ready to be inserted in the DB"""
        return (self.index, self.name, self.number, self.email, self.picture)


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
            self.cursor.executescript(contact_SCHEMA)
        except sqlite3.OperationalError:
            # database was present
            pass

    def close(self):
        return self.cursor.close()

    def add_contact(self, contact):
        """See :meth:`IContactProvider.add_contact`"""
        if not isinstance(contact, SQLContact):
            return

        self.cursor.execute("insert into contact values(?, ?, ?, ?, ?)",
                            contact.to_row())
        contact.index = self.cursor.lastrowid
        return contact

    def edit_contact(self, contact):
        """See :meth:`IContactProvider.edit_contact`"""
        if not isinstance(contact, SQLContact):
            return

        self.cursor.execute(
            "update contact set name=?, number=?, email=?, picture=? "
            "where id=?", (contact.name, contact.number, contact.email,
                           contact.picture, contact.index))
        return contact

    def find_contacts_by_name(self, name):
        """See :meth:`IContactProvider.find_contacts_by_name`"""
        sql = "select * from contact where name like ?"
        self.cursor.execute(sql, ("%%%s%%" % name,))
        return [SQLContact.from_row(r) for r in self.cursor.fetchall()]

    def find_contacts_by_number(self, number):
        """See :meth:`IContactProvider.find_contacts_by_number`"""
        sql = "select * from contact where number like ?"
        self.cursor.execute(sql, ("%%%s%%" % number,))
        return [SQLContact.from_row(r) for r in self.cursor.fetchall()]

    def list_contacts(self):
        """See :meth:`IContactProvider.list_contacts`"""
        self.cursor.execute("select * from contact")
        return [SQLContact.from_row(r) for r in self.cursor.fetchall()]

    def remove_contact(self, contact):
        """See :meth:`IContactProvider.remove_contact`"""
        if isinstance(contact, SQLContact):
            # filter out non SQLcontact
            sql = "delete from contact where id=?"
            self.cursor.execute(sql, (contact.index,))


sqlite_provider = SQLiteContactProvider()
