# -*- coding: utf-8 -*-
# Copyright (C) 2006-2008  Vodafone España, S.A.
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
"""Unittests for DBus exported methods"""

import dbus
import dbus.mainloop.glib
gloop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

from twisted.internet import defer
from twisted.python import log
from twisted.trial import unittest

from wader.common.config import config
from wader.common.consts import (WADER_SERVICE, CTS_INTFACE, SMS_INTFACE,
                                 NET_INTFACE, CRD_INTFACE)
import wader.common.aterrors as E
from wader.common.startup import (attach_to_serial_port,
                                  setup_and_export_device)
from wader.common.middleware import NetworkOperator
from wader.common.contact import Contact
from wader.common.oal import osobj


class TestDBusExportedMethods(unittest.TestCase):
    """
    Tests for the exported methods over D-Bus
    """
    def setUp(self):
        self.sconn = None
        self.serial = None
        self.device = None
        self.remote_obj = None
        try:
            d = osobj.hw_manager.get_devices()
            def get_device_cb(devices):
                if not devices:
                    self.skip = "No devices found"
                    return

                device = attach_to_serial_port(devices[0])
                self.device = setup_and_export_device(device)
                self.sconn = self.device.sconn
                d2 = self.device.initialize()
                d2.addCallback(self._get_remote_obj)
                d2.addCallback(lambda ign: self.sconn.delete_all_sms())
                d2.addCallback(lambda ign: self.sconn.delete_all_contacts())
                return d2

            d.addCallback(get_device_cb)
            return d
        except:
            log.err()

    def tearDown(self):
        return self.device.close()

    def _get_remote_obj(self, ignored=None):
        bus = dbus.SystemBus(mainloop=gloop)
        try:
            self.remote_obj = bus.get_object(WADER_SERVICE, self.device.udi)
            self.remote_obj.Enable(dbus_interface=CRD_INTFACE)
        except:
            log.err()
        return True

    def test_AddContact(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Contacts.Add"""
        c = Contact("Johnny", "+435443434343")
        d = defer.Deferred()
        def remote_add_contact_cb(index):
            d2 = self.sconn.get_contact_by_index(index)
            d2.addCallback(lambda contact: self.assertEqual(contact, c))
            d2.addCallback(lambda _: self.sconn.delete_contact(index))
            d2.addCallback(lambda _: d.callback(True))

        def remote_add_contact_eb(failure):
            log.err(failure)

        self.remote_obj.Add(c.name, c.number,
                            dbus_interface=CTS_INTFACE,
                            reply_handler=remote_add_contact_cb,
                            error_handler=remote_add_contact_eb)
        return d

    def test_DeleteContact(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Contacts.Delete"""
        def remove_contact(index):
            d = defer.Deferred()
            def remote_del_contact_cb():
                d2 = self.sconn.get_contact_by_index(index)
                d3 = self.failUnlessFailure(d2, E.GenericError)
                d3.chainDeferred(d)

            def remote_del_contact_eb(failure):
                log.err(failure)

            self.remote_obj.Delete(index,
                                   dbus_interface=CTS_INTFACE,
                                   reply_handler=remote_del_contact_cb,
                                   error_handler=remote_del_contact_eb)

            return d

        c = Contact("OM", "+215443434343")
        d = self.sconn.add_contact(c)
        d.addCallback(remove_contact)
        return d

    def test_DisablePin(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Card.Enable(pin, False)
        """
        pin = config.get('test', 'pin', '0000')
        d = defer.Deferred()
        def remote_disable_pin_cb():
            d2 = self.sconn.get_pin_status()
            d2.addCallback(lambda status: self.assertEqual(status, 0))
            d3 = self.sconn.enable_pin(pin)
            d3.addCallback(lambda ignored: d.callback(True))

        def remote_disable_pin_eb(failure):
            log.msg("FAILURE RECEIVED %s" % repr(failure))
            log.err(failure)
            d.errback(failure)

        self.remote_obj.EnablePin(pin, False,
                               dbus_interface=CRD_INTFACE,
                               reply_handler=remote_disable_pin_cb,
                               error_handler=remote_disable_pin_eb)
        return d

    def test_EnablePin(self):
        """
        Test that org.freedesktop.ModemManager.Modem.Gsm.Card.Enable
        """
        pin = config.get('test', 'pin', '0000')
        d = defer.Deferred()
        def remote_enable_pin_cb():
            # it seems to have worked
            d2 = self.sconn.get_pin_status()
            d2.addCallback(lambda status: self.assertEqual(status, 1))
            d2.addCallback(lambda _: d.callback(True))

        def remote_enable_pin_eb(exception):
            log.err(exception)
            d.errback(exception)

        self.remote_obj.EnablePin(pin, True,
                               dbus_interface=CRD_INTFACE,
                               reply_handler=remote_enable_pin_cb,
                               error_handler=remote_enable_pin_eb)
        return d

    def test_FindContacts(self):
        """
        Test that org.freedesktop.ModemManager.Modem.Gsm.Contacts.Find works
        """
        contact = Contact("Eugene", "+43534534")
        d = self.sconn.add_contact(contact)
        def callback(index):
            contact.index = index
            d2 = defer.Deferred()
            def remote_find_contacts_cb(reply):
                self.assertEqual(len(reply), 1)
                reply = list(reply[0])
                self.assertIn(contact.name, reply)
                self.assertIn(contact.number, reply)
                self.assertIn(contact.index, reply)

                d3 = self.sconn.delete_contact(contact.index)
                d3.addCallback(lambda _: d2.callback(True))

            def remote_find_contacts_eb(reply):
                log.err(reply)
                d2.errback(reply)

            self.remote_obj.Find("Euge", dbus_interface=CTS_INTFACE,
                                    reply_handler=remote_find_contacts_cb,
                                    error_handler=remote_find_contacts_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_Get_Contact(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Contacts.Get"""
        contact = Contact("Mario", "+312232332")
        d = self.sconn.add_contact(contact)
        def callback(index):
            contact.index = index
            d2 = defer.Deferred()
            def remote_get_contact_by_index_cb(reply):
                reply = list(reply)
                self.assertIn(contact.name, reply)
                self.assertIn(contact.number, reply)
                self.assertIn(contact.index, reply)

                d3 = self.sconn.delete_contact(contact.index)
                d3.addCallback(lambda _: d2.callback(True))

            def remote_get_contact_by_index_eb(reply):
                log.err(reply)
                d2.errback(reply)

            self.remote_obj.Get(index,
                                dbus_interface=CTS_INTFACE,
                                reply_handler=remote_get_contact_by_index_cb,
                                error_handler=remote_get_contact_by_index_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_ListContacts(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Contacts.List"""
        contact = Contact("Jauma", "+356456445654")
        d = self.sconn.add_contact(contact)
        def callback(index):
            contact.index = index
            d2 = defer.Deferred()
            def get_contacts_cb(contacts):
                def remote_get_contacts_cb(reply):
                    reply = list(reply[0])
                    self.assertIn(contact.name, reply)
                    self.assertIn(contact.number, reply)
                    self.assertIn(contact.index, reply)

                    d3 = self.sconn.delete_contact(contact.index)
                    d3.addCallback(lambda _: d2.callback(True))

                def remote_get_contacts_eb(reply):
                    log.err(reply)
                    d2.errback(reply)

                self.remote_obj.List(dbus_interface=CTS_INTFACE,
                                     reply_handler=remote_get_contacts_cb,
                                     error_handler=remote_get_contacts_eb)

            self.sconn.get_contacts().addCallback(get_contacts_cb)
            return d2

        d.addCallback(callback)
        return d

    def test_GetBands(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetBands"""
        d = self.sconn.get_bands()
        def get_bands_cb(bands):
            d2 = defer.Deferred()
            def remote_get_bands_cb(reply):
                self.assertEqual(reply, bands)
                d2.callback(True)
            def remote_get_bands_eb(reply):
                log.err(reply)
                d2.errback(reply)

            self.remote_obj.GetBands(dbus_interface=CRD_INTFACE,
                                     reply_handler=remote_get_bands_cb,
                                     error_handler=remote_get_bands_eb)
            return d2

        d.addCallback(get_bands_cb)
        return d

    def test_GetCardModel(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetModel"""
        d = self.sconn.get_card_model()
        def callback(model):
            d2 = defer.Deferred()
            def remote_get_card_model_cb(reply):
                self.assertEqual(model, reply)
                d2.callback(True)
            def remote_get_card_model_eb(reply):
                log.err(reply)
                d2.errback(reply)

            self.remote_obj.GetModel(dbus_interface=CRD_INTFACE,
                                     reply_handler=remote_get_card_model_cb,
                                     error_handler=remote_get_card_model_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetCardVersion(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetVersion"""
        d = self.sconn.get_card_version()
        def callback(version):
            d2 = defer.Deferred()
            def remote_get_card_version_cb(reply):
                self.assertEqual(version, reply)
                d2.callback(True)
            def remote_get_card_version_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetVersion(dbus_interface=CRD_INTFACE,
                                   reply_handler=remote_get_card_version_cb,
                                   error_handler=remote_get_card_version_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetCharsets(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetCharsets"""
        d = self.sconn.get_charsets()
        def process_charsets(charsets):
            d2 = defer.Deferred()

            def get_charsets_cb(reply):
                self.assertEquals(reply, charsets)
                d2.callback(True)

            def get_charsets_eb(reply):
                log.err(reply)
                d2.errback(reply)

            self.remote_obj.GetCharsets(dbus_interface=CRD_INTFACE,
                                        reply_handler=get_charsets_cb,
                                        error_handler=get_charsets_eb)

            return d2

        d.addCallback(process_charsets)
        return d

    def test_GetCharset(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetCharset"""
        d = self.sconn.get_charset()
        def callback(charset):
            d2 = defer.Deferred()
            def remote_get_charset_cb(reply):
                self.assertEqual(charset, reply)
                d2.callback(True)
            def remote_get_charset_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetCharset(dbus_interface=CRD_INTFACE,
                                    reply_handler=remote_get_charset_cb,
                                    error_handler=remote_get_charset_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetImei(self):
        """Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetImei"""
        d = self.sconn.get_imei()
        def callback(imei):
            d2 = defer.Deferred()
            def remote_get_imei_cb(reply):
                self.assertEqual(imei, reply)
                d2.callback(True)
            def remote_get_imei_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetImei(dbus_interface=CRD_INTFACE,
                                    reply_handler=remote_get_imei_cb,
                                    error_handler=remote_get_imei_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetImsi(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetImsi
        """
        d = self.sconn.get_imsi()
        def callback(imsi):
            d2 = defer.Deferred()
            def remote_get_imsi_cb(reply):
                self.assertEqual(imsi, reply)
                d2.callback(True)
            def remote_get_imsi_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetImsi(dbus_interface=CRD_INTFACE,
                                    reply_handler=remote_get_imsi_cb,
                                    error_handler=remote_get_imsi_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetManufacturerName(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Card.GetManufacturer
        """
        d = self.sconn.get_manufacturer_name()
        def callback(name):
            d2 = defer.Deferred()
            def remote_get_manfname_cb(reply):
                self.assertEqual(name, reply)
                d2.callback(True)
            def remote_get_manfname_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetManufacturer(dbus_interface=CRD_INTFACE,
                                    reply_handler=remote_get_manfname_cb,
                                    error_handler=remote_get_manfname_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetRegistrationInfo(self):
        """
        Test org.freedesktop.ModemManager.Gsm.Network.GetRegistrationInfo
        """
        d = self.sconn.get_netreg_status()
        def callback(status):
            d2 = defer.Deferred()
            def remote_get_netreg_status_cb(reply):
                _status, numeric_oper, long_oper = reply
                self.assertEqual(status, _status)
                d2.callback(True)
            def remote_get_netreg_status_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetRegistrationInfo(dbus_interface=NET_INTFACE,
                                    reply_handler=remote_get_netreg_status_cb,
                                    error_handler=remote_get_netreg_status_eb)
            return d2

        d.addCallback(callback)
        return d

    def test_GetNetworkInfo(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Network.GetInfo
        """
        d = self.sconn.get_network_info()
        def callback(netinfo):
            d2 = defer.Deferred()
            def remote_get_netinfo_cb(reply):
                self.assertEqual(netinfo, reply)
                d2.callback(True)
            def remote_get_netinfo_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetInfo(dbus_interface=NET_INTFACE,
                                    reply_handler=remote_get_netinfo_cb,
                                    error_handler=remote_get_netinfo_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_Scan(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Network.Scan
        """
        raise unittest.SkipTest("Not ready")
        d = self.sconn.get_network_names()
        def callback(netobjs):
            d2 = defer.Deferred()
            def scan_cb(reply):
                for struct in reply:
                    self.assertIn(NetworkOperator(*list(struct)), netobjs)

                d2.callback(True)

            def scan_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.Scan(dbus_interface=NET_INTFACE,
                                 reply_handler=scan_cb,
                                 error_handler=scan_eb)
            return d2

        d.addCallback(callback)
        return d

    def test_GetPhonebookSize(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Contacts.GetPhonebookSize
        """
        d = self.sconn.get_phonebook_size()
        def callback(size):
            d2 = defer.Deferred()
            def remote_get_phonebooksize_cb(reply):
                self.assertEqual(size, reply)
                d2.callback(True)
            def remote_get_phonebooksize_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetPhonebookSize(dbus_interface=CTS_INTFACE,
                                    reply_handler=remote_get_phonebooksize_cb,
                                    error_handler=remote_get_phonebooksize_eb)
            return d2

        d.addCallback(callback)
        return d

    def test_GetRoamingIDs(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Network.GetRoamingIDs
        """
        d = self.sconn.get_roaming_ids()
        def callback(roaming_ids):
            d2 = defer.Deferred()
            def remote_get_smsc_cb(reply):
                rids = [obj.netid for obj in roaming_ids]
                for netid in reply:
                    self.assertIn(netid, rids)

                d2.callback(True)
            def remote_get_smsc_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetRoamingIDs(dbus_interface=NET_INTFACE,
                                    reply_handler=remote_get_smsc_cb,
                                    error_handler=remote_get_smsc_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetSignalQuality(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Network.GetSignalQuality
        """
        d = self.sconn.get_signal_quality()
        def callback(rids):
            d2 = defer.Deferred()
            def remote_get_sigqual_cb(reply):
                self.assertEqual(rids, reply)
                d2.callback(True)
            def remote_get_sigqual_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetSignalQuality(dbus_interface=NET_INTFACE,
                                      reply_handler=remote_get_sigqual_cb,
                                      error_handler=remote_get_sigqual_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetSmsc(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.SMS.GetSmsc
        """
        d = self.sconn.get_smsc()
        def callback(smsc):
            d2 = defer.Deferred()
            def remote_get_smsc_cb(reply):
                self.assertEqual(smsc, reply)
                d2.callback(True)
            def remote_get_smsc_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetSmsc(dbus_interface=SMS_INTFACE,
                                    reply_handler=remote_get_smsc_cb,
                                    error_handler=remote_get_smsc_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_GetFormat(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.SMS.GetFormat
        """
        d = self.sconn.get_sms_format()
        def callback(_format):
            d2 = defer.Deferred()
            def remote_get_smsc_cb(reply):
                self.assertEqual(_format, reply)
                d2.callback(True)
            def remote_get_smsc_eb(reply):
                log.err(reply)
                d.errback(reply)

            self.remote_obj.GetFormat(dbus_interface=SMS_INTFACE,
                                      reply_handler=remote_get_smsc_cb,
                                      error_handler=remote_get_smsc_eb)
            return d2
        d.addCallback(callback)
        return d

    def test_SetCharset(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.Card.SetCharset
        """
        bad_charset = 'IRA'
        old_charset = self.device.sim.charset
        d = defer.Deferred()
        def remote_set_charset_cb():
            def check_and_set_good_charset_cb(charset):
                self.assertEqual(charset, bad_charset)
                d2 = self.sconn.set_charset(old_charset)
                d2.addCallback(lambda _: d.callback(True))
                return d2

            # check that the charset we just set over D-Bus is correct
            d2 = self.sconn.get_charset()
            d2.addCallback(check_and_set_good_charset_cb)
            return d2

        def remote_set_charset_eb(reply):
            log.err(reply)
            d.errback(reply)

        self.remote_obj.SetCharset(bad_charset,
                                dbus_interface=CRD_INTFACE,
                                reply_handler=remote_set_charset_cb,
                                error_handler=remote_set_charset_eb)
        return d

    def test_SetFormat(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.SMS.SetFormat
        """
        def check_and_set_format(_format):
            d2 = defer.Deferred()
            def remote_set_format_cb():
                # leave it like we found it
                d3 = self.sconn.set_sms_format(0)
                d3.chainDeferred(d2)

            def remote_set_format_eb(failure):
                log.err(failure)
                d2.errback(failure)

            self.assertEquals(_format, 0)
            self.remote_obj.SetFormat(1,
                                      dbus_interface=SMS_INTFACE,
                                      reply_handler=remote_set_format_cb,
                                      error_handler=remote_set_format_eb)

            return d2

        d = self.sconn.get_sms_format()
        d.addCallback(check_and_set_format)
        return d

    def test_SetSmsc(self):
        """
        Test org.freedesktop.ModemManager.Modem.Gsm.SMS.SetSmsc
        """
        badsmsc = '+3453456343'
        d = defer.Deferred()
        def remote_set_smsc_cb():
            def check_and_set_good_smsc_cb(smsc):
                self.assertEqual(smsc, badsmsc)
                goodsmsc = config.get('test', 'smsc', '+34607003110')
                d3 = self.sconn.set_smsc(goodsmsc)
                d3.addCallback(lambda ignored: d.callback(True))
                return d3

            d2 = self.sconn.get_smsc()
            d2.addCallback(check_and_set_good_smsc_cb)
            return d2

        def remote_set_smsc_eb(reply):
            log.err(reply)
            d.errback(reply)

        self.remote_obj.SetSmsc(str(badsmsc),
                                dbus_interface=SMS_INTFACE,
                                reply_handler=remote_set_smsc_cb,
                                error_handler=remote_set_smsc_eb)
        return d
