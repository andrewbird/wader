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
"""Unittests for the ModemManager IContactProvider"""

import time
from optparse import OptionParser

import dbus
import dbus.mainloop.glib
from twisted.internet import defer
from twisted.python import log

from wader.plugins.mm_provider import mm_provider, MMContact
from wader.common.config import config
from wader.common.consts import (WADER_SERVICE, WADER_INTFACE, WADER_OBJPATH,
                                 MDM_INTFACE, CRD_INTFACE)

def _parse_args():
	parser=OptionParser()
	parser.add_option('-p', '--pin', dest='pin',
	    help='Insert sim pin card if needed',action="store")
	parser.add_option('-n', '--name', dest='name',
	    help='Name of the contact.', action="store" )
	parser.add_option('-m', '--number', dest='number',
            help='Number of the contact.', action="store")
	parser.add_option('-a', '--action', dest='action',
	        help="Action to execute, one of: Add, List, Remove", action="store")
	parser.add_option('-c', '--contact', dest='contact',
            help='Contact (for delete)', action="store")
        return parser.parse_args()

(opts,args) = _parse_args()

class ModemManagerContactProvider():
    """Test for the ModemManager IContactProvider"""

    def __init__(self):
        d = defer.Deferred()
        self.provider = mm_provider
        loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=loop)

        def enable_device_cb():
            time.sleep(1)
            self.provider.initialize(dict(opath=self.opath))
            d.callback(True)

        def enable_device_eb(e):
            error = e.get_dbus_message()
            if 'SimPinRequired' in error:
                self.device.SendPin(opts.pin, dbus_interface=CRD_INTFACE,
                                    reply_handler=enable_device_cb,
                                    error_handler=log.err)
            else:
                raise unittest.SkipTest("Cannot handle error %s" % error)

        def get_device_from_opath(opaths):
            self.opath = opaths[0]
            self.device = bus.get_object(WADER_SERVICE, self.opath)
            self.device.Enable(True, dbus_interface=MDM_INTFACE,
                               reply_handler=enable_device_cb,
                               error_handler=enable_device_eb)

        obj = bus.get_object(WADER_SERVICE, WADER_OBJPATH)
        obj.EnumerateDevices(dbus_interface=WADER_INTFACE,
                             reply_handler=get_device_from_opath,
                             error_handler=log.err)
        return d

    def _add_contact(self):
        return self.provider.add_contact(MMContact(opts.name, opts.number))

    def _list_contacts(self):
        return self.provider.list_contacts()

    def _remove_contact(self):
        self.provider.remove_contact(opts.contact)

cP=ModemManagerContactProvider()
if opts.action == "add" : print cP._add_contact()
elif opts.action == "list" : print cP._list_contacts()
elif opts.action == 'remove': print cP._remove_contact()
