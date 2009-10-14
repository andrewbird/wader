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

from zope.interface import implements
from twisted.plugin import IPlugin
import vobject

SUDS_AVAILABLE = True
try:
    from suds.client import Client
except ImportError:
    SUDS_AVAILABLE = False

from wader.common.contact import Contact
from wader.common.exceptions import PluginInitialisationError
from wader.common.interfaces import IContactProvider

class ZYBContact(Contact):

    def __init__(self, name, number, index=None, email="", contact=None):
        super(ZYBContact, self).__init__(name, number, index=index)
        self.email = email
        self._contact = contact

    @classmethod
    def from_soap(cls, c):
        contact = vobject.readOne(c.StringRepresentation, allowQP=True)
        email = contact.getChildValue('email', default="")
        number = contact.getChildValue('tel', default="")
        return cls(contact.n.value.given, number, index=c.ID,
                   email=email, contact=contact)


class ZYBProvider(object):
    """ZYB IContactProvider backend"""
    implements(IPlugin, IContactProvider)

    name = "SQLite contact backend"
    author = u"Pablo Martí"
    version = u"0.1"

    def __init__(self):
        self.client = None
        self.user_id = None
        self.password = None
        self.ptoken = None
        self.utoken = None

    def _get_last_error(self):
        return self.client.service.GetLastErrorInfo(self.ptoken, self.utoken)

    def close(self):
        del self.client
        self.client = None
        self.user_id = None
        self.password = None
        self.ptoken = None
        self.utoken = None

    def initialize(self, init_obj):
        if not SUDS_AVAILABLE:
            raise PluginInitialisationError("install python-suds")

        self.user_id = init_obj['username']
        self.password = init_obj['password']
        self.client = Client('https://api.zyb.com/zybservice.asmx?WSDL')

        self.ptoken = self.client.service.AuthenticatePartner(self.user_id,
                                                             self.password)
        if not self.ptoken:
            msg = "Error getting partner token: %s"
            raise PluginInitialisationError(msg % self._get_last_error())

        self.utoken = self.client.service.AuthenticateUser(self.ptoken,
                                                           self.user_id,
                                                           self.password)
        if not self.utoken:
            msg = "Error getting user token: %s"
            raise PluginInitialisationError(msg % self._get_last_error())

    def add_contact(self, contact):
        """See :meth:`IContactProvider.add_contact`"""
        if not isinstance(contact, ZYBContact):
            return

        c = vobject.vCard()
        c.add('n')
        c.n.value = vobject.vcard.Name(given=contact.name)
        c.add('fn')
        c.fn.value = contact.name
        c.add('tel')
        c.tel.value = contact.number

        if contact.email is not None:
            c.add('email')
            c.email.value = contact.email
            c.email.type_param = 'INTERNET'

        _contact = self.client.service.CreateContact(self.ptoken, self.utoken,
                                                     c.serialize())
        return ZYBContact.from_soap(_contact)

    def find_contacts(self, pattern):
        """See :meth:`IContactProvider.find_contacts`"""
        # ZYB does not offer a browse API, this emulates it O(N)
        return (c for c in self.list_contacts()
                if c.name.startswith(pattern))

    def list_contacts(self):
        """See :meth:`IContactProvider.list_contacts`"""
        contacts = self.client.service.GetContactList(self.utoken, self.ptoken)
        return (ZYBContact.from_soap(c) for c in contacts[0])

    def remove_contact(self, contact):
        """See :meth:`IContactProvider.remove_contact`"""
        if isinstance(contact, ZYBContact):
            self.client.service.DeleteContact(self.ptoken, self.utoken,
                                              contact.index)


zyb_provider = ZYBProvider()

