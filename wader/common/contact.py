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
"""Contact related classes and utilities"""

from zope.interface import implements

from wader.common.encoding import to_u
from wader.common.interfaces import IContact


class Contact(object):
    """I am a Contact on Wader"""

    implements(IContact)

    def __init__(self, name, number, index=None):
        super(Contact, self).__init__()
        self.name = to_u(name)
        self.number = to_u(number)
        self.index = index

    def __repr__(self):
        return '<Contact name="%s" number="%s">' % (self.name, self.number)

    __str__ = __repr__

    def __eq__(self, c):
        if all([self.index, c.index]):
            return self.index == c.index

        return self.name == c.name and self.number == c.number

    def __ne__(self, c):
        return not self.__eq__(c)

    def to_csv(self):
        """See :meth:`wader.common.interfaces.IContact.to_csv`"""
        name = '"%s"' % self.name
        number = '"%s"' % self.number
        return [name, number]


class ContactStore(object):
    """
    I am a contact store

    A central point to perform operations on the different contact
    backends (see :class:`~wader.common.interfaces.IContactProvider`)
    """

    def __init__(self):
        super(ContactStore, self).__init__()
        self._providers = []

    def add_provider(self, provider):
        """Adds ``provider`` to the list of registered providers"""
        self._providers.append(provider)

    def remove_provider(self, provider):
        """Removes ``provider`` to the list of registered providers"""
        self._providers.remove(provider)

    def _call_method(self, name, *args):
        """
        Executes method ``name`` using ``args`` in all the registered providers
        """
        return (getattr(prov, name)(*args) for prov in self._providers)

    def add_contact(self, data):
        """See :meth:`~wader.common.interfaces.IContactProvider.add_contact`"""
        self._call_method('add_contact', data)

    def list_contacts(self):
        """
        See :meth:`~wader.common.interfaces.IContactProvider.list_contacts`
        """
        self._call_method('list_contacts')

    def find_contacts(self, pattern):
        """
        See :meth:`~wader.common.interfaces.IContactProvider.find_contacts`
        """
        self._call_method('find_contacts', pattern)

    def remove_contact(self, contact):
        """
        See :meth:`~wader.common.interfaces.IContactProvider.remove_contact`
        """
        self._call_method('remove_contact', contact)
