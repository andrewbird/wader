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
from optparse import OptionParser

from wader.plugins.sqlite_provider import sqlite_provider, SQLContact

def _parse_args():
	parser=OptionParser()
	parser.add_option('-n', '--name', dest='name',
	    help='Name of the contact.', action="store" )
	parser.add_option('-d', '--database', dest='path',
	    help='Path to sqlite database.', action="store" )
	parser.add_option('-m', '--number', dest='number',
            help='Number of the contact.', action="store")
	parser.add_option('-a', '--action', dest='action',
	        help="Action to execute, one of: add, list, remove", action="store")
	parser.add_option('-c', '--contact', dest='contact',
            help='Contact id (for delete)', action="store")
        return parser.parse_args()

opts, args = _parse_args()

class SQLiteContactProvider():
    """SQLite IContactProvider sample usage"""

    def __init__(self):
        self.provider = sqlite_provider
        self.provider.initialize(dict(path=opts.path))

    def _add_contact(self):
        return self.provider.add_contact(SQLContact(opts.name, opts.number))

    def _list_contacts(self):
        return self.provider.list_contacts()

    def _remove_contact(self):
        return self.provider.remove_contact(opts.contact)

    def _close(self):
        self.provider.close()

cp = SQLiteContactProvider()

if opts.action == "add":
    print cp._add_contact()
elif opts.action == "list":
    print cp._list_contacts()
elif opts.action == 'remove':
    print cp._remove_contact()
