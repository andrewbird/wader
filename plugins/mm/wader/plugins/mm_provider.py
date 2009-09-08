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

import dbus
from zope.interface import implements
from twisted.plugin import IPlugin

from wader.common.contact import Contact
from wader.common.consts import WADER_SERVICE, CTS_INTFACE
from wader.common.interfaces import IContactProvider

class MMContact(Contact):
    """
    I am a ModemManager contact
    """
    @classmethod
    def from_tuple(cls, t):
        return cls(t[1], t[2], index=t[0])


class ModemManagerContactProvider(object):
    """ModemManager IContactProvider backend"""
    implements(IPlugin, IContactProvider)

    name = "ModemManager contact backend"
    author = u"Pablo Mart??"
    version = "0.1"

    def __init__(self):
        self.obj = None
        self.iface = None

    def initialize(self, init_obj):
        self.obj = dbus.SystemBus().get_object(WADER_SERVICE, init_obj['opath'])
        self.iface = dbus.Interface(self.obj, CTS_INTFACE)

    def close(self):
        del self.iface
        del self.obj

    def add_contact(self, contact):
        """See :meth:`IContactProvider.add_contact`"""
        if not isinstance(contact, MMContact):
            return

        index = self.iface.Add(contact.name, contact.number)
        return MMContact(contact.name, contact.number, index=index)

    def find_contacts(self, pattern):
        """See :meth:`IContactProvider.find_contacts`"""
        return (MMContact.from_tuple(t)
                    for t in self.iface.FindByName(pattern))

    def list_contacts(self):
        """See :meth:`IContactProvider.list_contacts`"""
        return (MMContact.from_tuple(t) for t in self.iface.List())

    def remove_contact(self, contact):
        """See :meth:`IContactProvider.remove_contact`"""
        # only remove ModemManager contacts
        if isinstance(contact, MMContact):
            self.iface.Delete(contact.index)


mm_provider = ModemManagerContactProvider()

