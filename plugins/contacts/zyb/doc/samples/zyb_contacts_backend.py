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
"""Sample ZYB IContactProvider usage"""

from optparse import OptionParser
from wader.plugins.zyb_provider import zyb_provider, ZYBContact

def _parse_args():
	parser=OptionParser()
	parser.add_option('-u', '--username', dest='username',
	    help='ZYB username', action="store" )
	parser.add_option('-p', '--password', dest='password',
	    help='ZYB password', action="store" )

	parser.add_option('-a', '--action', dest='action',
	        help="Action to execute, one of: add, list, remove", action="store")

	parser.add_option('-n', '--name', dest='name',
	    help='Name of the contact.', action="store" )
	parser.add_option('-m', '--number', dest='number',
            help='Number of the contact.', action="store")
	parser.add_option('-c', '--contact', dest='contact',
            help='Contact id (for delete)', action="store")


        return parser.parse_args()

(opts,args) = _parse_args()

class ZYBProvider():
    """Test for the ZYB IContactProvider"""

    def __init__(self):
        self.provider = zyb_provider
        self.provider.initialize(dict(username=opts.username,
                                      password=opts.password))

    def _close(self):
        # leave everything as found
        self.provider.close()

    def _add_contact(self):
        return self.provider.add_contact(ZYBContact(opts.name, opts.number))

    def _list_contacts(self):
        return self.provider.list_contacts()

    def _remove_contact(self):
        return self.provider.remove_contact(opts.contact)


cP=ZYBProvider()
if opts.action == "add" : print cP._add_contact()
elif opts.action == "list" : print cP._list_contacts()
elif opts.action == 'remove': print cP._remove_contact()
