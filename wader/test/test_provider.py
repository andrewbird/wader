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
"""Unittests for the provider layer """

from datetime import datetime, timedelta, date
import os
from pytz import timezone
import sqlite3
import sys
from time import time

from twisted.trial import unittest

from wader.common.provider import (SMS_SCHEMA, SmsProvider, Message, Folder,
                                   Thread, DBError, inbox_folder,
                                   outbox_folder, drafts_folder, READ, UNREAD,
                                   message_read, NETWORKS_SCHEMA, TYPE_PREPAID,
                                   TYPE_CONTRACT, NetworkProvider,
                                   NetworkOperator, UsageProvider)
from wader.common.utils import get_tz_aware_now


class TestNetworkDBTriggers(unittest.TestCase):
    """Tests for the network DB triggers"""

    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None)
        c = self.conn.cursor()
        # create schema
        c.executescript(NETWORKS_SCHEMA)

    def tearDown(self):
        self.conn.close()

    def test_deleting_on_cascade_apn(self):
        """test trigger fkd_network_info_apn"""
        c = self.conn.cursor()
        c.execute("insert into network_info values "
                  "('21401', 'Vodafone', 'Spain')")
        c.execute("insert into apn values (NULL, 'ac.vodafone.es', 'vodafone',"
                  "'vodafone', '195.235.113.3', '10.0.0.1', 1, '+34324324342',"
                  "NULL, NULL, NULL, NULL, NULL, NULL,'21401')")
        # make sure we have 1 apn now
        c.execute("select count(*) from apn")
        self.assertEqual(c.fetchone()[0], 1)
        # now delete the only network_info
        c.execute("delete from network_info where id='21401'")
        # make sure we have 0 apns now
        c.execute("select count(*) from apn")
        self.assertEqual(c.fetchone()[0], 0)

    def test_insert_apn_with_unknown_network_id(self):
        """test trigger fki_apns_with_unknown_network_id"""
        c = self.conn.cursor()
        c.execute("insert into network_info values "
                  "('21401', 'Vodafone', 'Spain')")
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                  "insert into apn values (1, 'ac.vodafone.es', 'vodafone',"
                  "'vodafone', '195.235.113.3', '10.0.0.1', 1, NULL, NULL,"
                  "NULL, NULL, NULL, NULL, NULL, '21402')")
        # leave it as we found it
        c.execute("delete from network_info where id='21401'")

    def test_update_network_info_id_with_apns_associated(self):
        """test fku_prevent_apn_network_info_network_id_bad_update trigger"""
        c = self.conn.cursor()
        c.execute("insert into network_info values "
                  "('21401', 'Vodafone', 'Spain')")
        c.execute("insert into apn values (NULL, 'ac.vodafone.es', 'vodafone',"
                  "'vodafone', '195.235.113.3', '10.0.0.1', 1, NULL, NULL,"
                  "NULL, NULL, NULL, NULL, NULL, '21401')")
        # now update the netid
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                          "update network_info set id='21402' "
                          "where name='Vodafone'")
        # leave it as we found it
        c.execute("delete from network_info where id='21401'")

    def test_update_apn_network_id_with_unknown_netid(self):
        """test fku_prevent_apn_network_id_bad_update trigger"""
        c = self.conn.cursor()
        c.execute("insert into network_info values "
                  "('21401', 'Vodafone', 'Spain')")
        c.execute("insert into apn values (1, 'ac.vodafone.es', 'vodafone',"
                  "'vodafone', '195.235.113.3', '10.0.0.1', 1, NULL, NULL,"
                  "NULL, NULL, NULL, NULL, NULL, '21401')")
        # now update the netid
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                          "update apn set network_id='21402' where id=1")
        # leave it as we found it
        c.execute("delete from network_info where id='21401'")


class TestNetworkProvider(unittest.TestCase):
    """Tests for the network provider"""

    def setUp(self):
        self.provider = NetworkProvider(':memory:')

    def tearDown(self):
        self.provider.close()

    def create_test_mbpi(self):
        self.mbpi = 'mbpi'

        f = open(self.mbpi, 'w')
        xml = """<?xml version="1.0"?>
<!-- -*- Mode: XML; tab-width: 4; indent-tabs-mode: t; c-basic-offset: 4 -*- -->
<!DOCTYPE serviceproviders SYSTEM "serviceproviders.2.dtd">

<serviceproviders format="2.0">

<!-- United Arab Emirates -->
<country code="ae">
        <provider>
                <name>Etisalat</name>
                <gsm>
                        <network-id mcc="424" mnc="02"/>
                        <apn value="mnet">
                                <name>Etisalat</name>
                                <username>mnet</username>
                                <password>mnet</password>
                                <dns>194.170.1.6</dns>
                                <dns>194.170.1.7</dns>
                        </apn>
                        <apn value="etisalat.ae">
                                <name>Etisalat 3G</name>
                                <username>etisalat.ae</username>
                                <password>etisalat.ae</password>
                        </apn>
                </gsm>
        </provider>
</country>

<!-- Germany -->
<country code="de">
        <provider>
                <name>Vodafone (D2)</name>
                <gsm>
                        <network-id mcc="262" mnc="02"/>
                        <network-id mcc="262" mnc="04"/>
                        <network-id mcc="262" mnc="09"/>

                        <apn value="web.vodafone.de">
                                <username>vodafone</username>
                                <password>vodafone</password>
                                <dns>139.7.30.125</dns>
                                <dns>139.7.30.126</dns>
                        </apn>
                        <apn value="event.vodafone.de">
                                <name>WebSessions</name>
                                <username>vodafone</username>
                                <password>vodafone</password>
                                <dns>139.7.30.125</dns>
                                <dns>139.7.30.126</dns>
                        </apn>
                </gsm>
        </provider>
</country>

</serviceproviders>
"""
        f.write(xml)
        f.close

    def test_populate_networks(self):
        self.provider.populate_networks()

    def test_populate_db_from_objs(self):
        networks = [NetworkOperator(["21401"], "prepaid.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Vodafone"),
                    NetworkOperator(["21401"], "contract.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_CONTRACT, '+23123121', '+2132121', "Spain",
                        "Vodafone")]

        self.provider.populate_networks_from_objs(networks)
        # we should get just two objects
        response = self.provider.get_network_by_id("214013241213122")
        self.assertEqual(len(response), 2)
        # leave it as we found it
        c = self.provider.conn.cursor()
        c.execute("delete from network_info where id='21401'")
        response = self.provider.get_network_by_id("214013241213122")
        self.assertEqual(len(response), 0)

    def test_populate_db_from_mbpi_real(self):
        mbpi = '/usr/share/mobile-broadband-provider-info/serviceproviders.xml'
        if not os.path.exists(mbpi):
            raise unittest.SkipTest("No MBPI installed")

        self.provider.populate_networks_from_mbpi(mbpi)

        c = self.provider.conn.cursor()
        c.execute("select * from network_info")
        response = c.fetchall()
        self.failUnless(len(response) >= 1)

        # leave it as we found it
        c.execute("delete from network_info")

    def test_populate_db_from_networks_py_real(self):
        extra = '../../../resources/extra'
        if not os.path.exists(extra):
            raise unittest.SkipTest('Path to "networks.py" not valid')

        sys.path.insert(0, extra)
        import networks

        def is_valid(item):
            return not item.startswith(("__", "Base", "NetworkOperator"))

        self.provider.populate_networks_from_objs([getattr(networks, item)()
                          for item in dir(networks) if is_valid(item)])

        c = self.provider.conn.cursor()

        c.execute("select country from network_info where id = '23415'")
        self.assertEqual(c.fetchone()[0], 'United Kingdom')

        # leave it as we found it
        c.execute("delete from network_info")

    def test_populate_db_from_mbpi_merge_network_no_clash(self):
        networks = [NetworkOperator(["21401"], "Preloaded",
                        "Preloaded", "Preloaded", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Preloaded")]

        self.provider.populate_networks_from_objs(networks)

        self.create_test_mbpi()
        self.provider.populate_networks_from_mbpi(self.mbpi)

        c = self.provider.conn.cursor()
        c.execute("select * from network_info")
        response = c.fetchall()
        self.assertEqual(len(response), 5)

        # leave it as we found it
        c.execute("delete from network_info")

    def test_populate_db_from_mbpi_merge_network_conflict(self):
        networks = [NetworkOperator(["26202"], "Preloaded",
                        "Preloaded", "Preloaded", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Germany",
                        "Preloaded")]

        self.provider.populate_networks_from_objs(networks)

        self.create_test_mbpi()
        self.provider.populate_networks_from_mbpi(self.mbpi)

        c = self.provider.conn.cursor()

        # make sure we merged
        c.execute("select * from network_info")
        response = c.fetchall()
        self.assertEqual(len(response), 4)

        # make sure we didn't overwrite the original
        c.execute("select name from network_info where id = '26202'")
        self.assertEqual(c.fetchone()[0], 'Preloaded')

        # leave it as we found it
        c.execute("delete from network_info")

    def test_populate_db_from_mbpi_merge_apn_no_clash(self):
        networks = [NetworkOperator(["21401"], "Preloaded",
                        "Preloaded", "Preloaded", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Preloaded")]

        self.provider.populate_networks_from_objs(networks)

        self.create_test_mbpi()
        self.provider.populate_networks_from_mbpi(self.mbpi)

        c = self.provider.conn.cursor()

        c.execute("select * from apn")
        response = c.fetchall()
        self.assertEqual(len(response), 9)

        # make sure we prefixed the foreign entry
        c.execute("select type from apn where network_id = '26202'")
        self.assertEqual(c.fetchone()[0][:4], 'MBPI')

        # leave it as we found it
        c.execute("delete from network_info")

    def test_populate_db_from_mbpi_merge_apn_conflict(self):
        networks = [NetworkOperator(["26202"], "Preloaded",
                        "Preloaded", "Preloaded", "10.0.0.1", "10.0.0.2",
                        "Preloaded", '+23323232', '+23423232', "Germany",
                        "Preloaded")]

        self.provider.populate_networks_from_objs(networks)

        self.create_test_mbpi()
        self.provider.populate_networks_from_mbpi(self.mbpi)

        c = self.provider.conn.cursor()

        # make sure we merged and didn't load any apns for the existing nets
        c.execute("select * from apn")
        response = c.fetchall()
        self.assertEqual(len(response), 7)

        # make sure we didn't overwrite the original
        c.execute("select type from apn where network_id = '26202'")
        self.assertEqual(c.fetchone()[0], 'Preloaded')

        # leave it as we found it
        c.execute("delete from network_info")

    def test_assert_passing_netid_raises_exception(self):
        self.assertRaises(ValueError, self.provider.get_network_by_id, "21401")

    def test_get_network_by_id_five_digit_netid(self):
        networks = [NetworkOperator(["21401"], "prepaid.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Vodafone"),
                    NetworkOperator(["21401"], "contract.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_CONTRACT, '+23123121', '+2132121', "Spain",
                        "Vodafone")]

        self.provider.populate_networks_from_objs(networks)
        # we should get just two objects
        response = self.provider.get_network_by_id("2140153241213122")
        self.assertEqual(len(response), 2)
        # leave it as we found it
        c = self.provider.conn.cursor()
        c.execute("delete from network_info where 1=1")

    def test_get_network_by_id_six_digit_netid(self):
        networks = [NetworkOperator(["214016"], "prepaid.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Vodafone"),
                    NetworkOperator(["214015"], "contract.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_CONTRACT, '+23123121', '+2132121', "Spain",
                        "Vodafone")]

        self.provider.populate_networks_from_objs(networks)
        # we should get just two objects
        response = self.provider.get_network_by_id("2140153241213122")
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].apn, "contract.vodafone.es")
        # leave it as we found it
        c = self.provider.conn.cursor()
        c.execute("delete from network_info where 1=1")

    def test_get_network_by_id_seven_digit_netid(self):
        networks = [NetworkOperator(["2140161"], "prepaid.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_PREPAID, '+23323232', '+23423232', "Spain",
                        "Vodafone"),
                    NetworkOperator(["2140162"], "contract.vodafone.es",
                        "vodafone", "vodafone", "10.0.0.1", "10.0.0.2",
                        TYPE_CONTRACT, '+23123121', '+2132121', "Spain",
                        "Vodafone")]

        self.provider.populate_networks_from_objs(networks)
        # we should get just two objects
        response = self.provider.get_network_by_id("2140161213322323")
        self.assertEqual(response[0].apn, "prepaid.vodafone.es")
        self.assertEqual(len(response), 1)
        # leave it as we found it
        c = self.provider.conn.cursor()
        c.execute("delete from network_info where 1=1")


class TestSmsDBTriggers(unittest.TestCase):
    """Tests for the SMS DB triggers"""

    def setUp(self):
        self.conn = sqlite3.connect(':memory:', isolation_level=None)
        c = self.conn.cursor()
        # add read function
        self.conn.create_function('msg_is_read', 1, message_read)
        # create schema
        c.executescript(SMS_SCHEMA)
        # initialize folder table
        c.execute("insert into folder values (1, 'Inbox')")
        c.execute("insert into folder values (2, 'Outbox')")
        c.execute("insert into folder values (3, 'Drafts')")

    def tearDown(self):
        self.conn.close()

    def test_deleting_on_cascade_folder(self):
        """test trigger fkd_folder_thread trigger"""
        c = self.conn.cursor()
        c.execute("insert into folder values (4, 'foo')")
        c.execute("insert into thread values (null, ?, '+3232323232'"
                  ", 1, 'hey how are ya?', 1, 4)", (time(),))
        # make sure that we have 1 threads now
        c.execute("select count(*) from thread")
        self.assertEqual(c.fetchone()[0], 1)
        # now delete the only folder
        c.execute("delete from folder where id = 4")
        c.execute("select count(*) from thread")
        # make sure that we have 0 threads now
        self.assertEqual(c.fetchone()[0], 0)

    def test_deleting_on_cascade_thread(self):
        """test trigger fkd_thread_message trigger"""
        c = self.conn.cursor()
        c.execute("insert into folder values (4, 'foo')")
        c.execute("insert into thread values (null, ?, '+3232323232'"
                  ", 1, 'hey how are ya?', 1, 4)", (time(),))
        c.execute("insert into message values (null, ?, '+3232323232'"
                  ", 'hey how are ya?', 2, 1)", (time(),))
        c.execute("select count(*) from message")
        self.assertEqual(c.fetchone()[0], 1)
        # now delete the only thread
        c.execute("delete from thread where id = 1")
        c.execute("select count(*) from message")
        # make sure that we have 0 threads now
        self.assertEqual(c.fetchone()[0], 0)

    def test_inserting_new_message_updates_thread_snippet(self):
        """test fki_update_thread_values snippet update"""
        c = self.conn.cursor()
        # insert a thread, add a new message and check the snippet
        # and the sms.text match
        snippet_text = 'thread snippet test'
        c.execute("insert into thread values (5, ?, '+34654321232',"
                  "1, '', 1, 1)", (time(),))
        c.execute("insert into message values (null, ?, '+34654321232',"
                  "?, 2, 5)", (time(), snippet_text))
        c.execute("select snippet from thread where id=5")
        snippet = c.fetchone()[0]
        self.assertEqual(snippet, snippet_text)
        # leave everything as we found it
        c.execute("delete from thread where id=5")

    def test_inserting_new_message_updates_thread_date(self):
        """test fki_update_thread_values date update"""
        c = self.conn.cursor()
        # insert a thread, add a new message and check the thread date
        # and the sms date match
        now = int(time())
        c.execute("insert into thread values (5, ?, '+34654321232',"
                  "1, '', 1, 1)", (now - 10,))
        c.execute("insert into message values (null, ?, '+34654321232',"
                  "'hey there', 2, 5)", (now,))
        c.execute("select date from thread where id=5")
        _date = c.fetchone()[0]
        self.assertEqual(now, _date)
        # leave everything as we found it
        c.execute("delete from thread where id=5")

    def test_inserting_non_existing_folder_id_in_thread(self):
        """test fki_thread_folder trigger"""
        c = self.conn.cursor()
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                          "insert into thread values (null, ?, '+3232323232'"
                          ", 1, 'hey how are ya?', 1, 9)", (time(),))

    def test_inserting_non_existing_thread_id_in_message(self):
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+3232323232', 1"
                  ",'hey how are ya?', 1, 1)", (time(),))
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                          "insert into message values (null, ?, '+3232323232'"
                          ", 'hey how are ya?', 2, 2)", (time(),))
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_updating_sms_flags_decreases_thread_read_attribute(self):
        """test fku_mark_message_unread trigger"""
        # add a thread to inbox_folder
        c = self.conn.cursor()
        c.execute("insert into thread values (1, 121322311, '+322121111',"
                  "0, 'test_updating_sms_flags_decreases', 0, 1)")
        # add a couple of read messages
        c.execute("insert into message values (1, 121322311, '+322121111',"
                  "'test_updating_sms_flags_decreases', ?, 1)", (READ,))
        c.execute("insert into message values (2, 121322319, '+322121111',"
                  "'test_updating_sms_flags_decreases 2', ?, 1)", (READ,))
        c.execute("select read from thread where id=1")
        # make sure we have exactly two read messages
        self.assertEqual(c.fetchone()[0], 2)
        # update one of them and mark it as unread
        c.execute("update message set flags=? where id=1", (UNREAD,))
        c.execute("select read from thread where id=1")
        # make sure we have exactly one read message
        self.assertEqual(c.fetchone()[0], 1)
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_updating_sms_flags_increases_thread_read_attribute(self):
        """test fku_mark_message_read trigger"""
        # add a thread to inbox_folder
        c = self.conn.cursor()
        c.execute("insert into thread values (1, 121322311, '+322121111',"
                  "0, 'test_updating_sms_flags_increases', 0, 1)")
        # add a couple of read messages
        c.execute("insert into message values (1, 121322311, '+322121111',"
                  "'test_updating_sms_flags_increases', 1, 1)")
        c.execute("insert into message values (2, 121322319, '+322121111',"
                  "'test_updating_sms_flags_increases 2', 1, 1)")
        c.execute("select read from thread where id=1")
        # make sure we have exactly zero read messages
        self.assertEqual(c.fetchone()[0], 0)
        # update one of them and mark it as read
        c.execute("update message set flags = 2 where id=1")
        c.execute("select read from thread where id=1")
        # make sure we have exactly one read message
        self.assertEqual(c.fetchone()[0], 1)
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_that_update_message_count_increases_message_count(self):
        """test fki_update_message_count trigger"""
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+3232323232', 1"
                  ", 'hey how are ya?', 1, 1)", (time(),))
        c.execute("select message_count from thread where id = 1")
        self.assertEqual(c.fetchone()[0], 1)
        c.execute("insert into message values (null, ?, '+3232323232'"
                  ", 'hey how are ya?', 2, 1)", (time(),))
        c.execute("select message_count from thread where id = 1")
        self.assertEqual(c.fetchone()[0], 2)
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_that_update_message_count_decreases_message_count(self):
        """test fkd_update_message_count trigger"""
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+3232323232'"
                  ", 1, 'hey how are ya?', 1, 1)", (time(),))
        c.execute("select message_count from thread where id=1")
        self.assertEqual(c.fetchone()[0], 1)
        c.execute("insert into message values (null, ?, '+3232323232'"
                  ", 'hey how are ya?', 2, 1)", (time(),))
        c.execute("select message_count from thread where id=1")
        self.assertEqual(c.fetchone()[0], 2)
        c.execute("delete from message where id=1")
        c.execute("select message_count from thread where id=1")
        self.assertEqual(c.fetchone()[0], 1)
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_update_folder_id_with_threads_associated(self):
        """test fku_folder_thread trigger"""
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, ',+3232323232',"
                  "1, 'hey how are ya?', 1, 1)", (time(),))
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                  "update folder set id = (select max(id) from folder) + 1")
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_update_message_thread_id_with_messages_associated(self):
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+3232323232',"
                  "1, 'hey how are ya?', 1, 1)", (time(),))
        c.execute("insert into message values (null, ?, '+3232323232',"
                  "'hey how are ya?', 2, 1)", (time(),))
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                  "update thread set id = (select max(id) from thread) + 1")
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_update_message_thread_id_with_non_existing_thread_id(self):
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+3232323232',"
                  "1, 'hey how are ya?', 1, 1)", (time(),))
        c.execute("insert into message values (null, ?, '+3232323232',"
                  "'hey how are ya?', 2, 1)", (time(),))
        self.assertRaises(sqlite3.IntegrityError, c.execute,
                  "update thread set id = (select max(id) from thread) + 1")
        # leave everything as we found it
        c.execute("delete from thread where id=1")

    def test_update_thread_folder_id_with_non_existing_folder_id(self):
        """test fku_thread_folder trigger"""
        c = self.conn.cursor()
        c.execute("insert into thread values (1, ?, '+23423432423',"
                  "1, 'hey how are ya?', 1, 1)", (time(),))
        self.assertRaises(sqlite3.IntegrityError, c.execute,
              "update thread set folder_id = (select max(id) from folder) + 1")
        # leave everything as we found it
        c.execute("delete from thread where id=1")


class TestSmsProvider(unittest.TestCase):
    """Tests for SmsProvider"""

    def setUp(self):
        self.provider = SmsProvider(':memory:')
        self.provider.add_folder(inbox_folder)
        self.provider.add_folder(outbox_folder)
        self.provider.add_folder(drafts_folder)

    def tearDown(self):
        self.provider.close()

    def test_add_folder(self):
        # add a folder and make sure it is there
        folder = self.provider.add_folder(Folder("Test"))
        self.assertIn(folder, list(self.provider.list_folders()))
        # leave everything as found
        self.provider.delete_folder(folder)
        self.assertNotIn(folder, list(self.provider.list_folders()))

    def test_add_sms(self):
        sms = Message('+3243243223', 'hey how are you?',
                      _datetime=get_tz_aware_now())
        sms = self.provider.add_sms(sms)
        self.assertIn(sms, list(self.provider.list_sms()))
        # leave everything as found
        self.provider.delete_sms(sms)
        self.assertNotIn(sms, list(self.provider.list_sms()))

    def test_sms_time_storage(self):
        zones = ['Europe/London', # UTC+0(without DST), UTC+1(with DST)
                 'Europe/Paris',  # UTC+1(without DST), UTC+2(with DST)
                 'Asia/Jakarta']  # UTC+7(no DST adjustment in 2010)

        for tzstring in zones:
            tz = timezone(tzstring)

            # db resolution is secs
            now = datetime.now(tz).replace(microsecond=0)

            sms = Message('+447917267410', tzstring, _datetime=now)
            sms = self.provider.add_sms(sms)

            for dbsms in self.provider.list_sms():
                if dbsms.text == tzstring:
                    break

            dbnow = dbsms.datetime.astimezone(tz)
            self.assertEqual(now, dbnow)

            # leave everything as found
            self.provider.delete_sms(sms)
            self.assertNotIn(sms, list(self.provider.list_sms()))

    def test_delete_folder(self):
        # add a folder and make sure it is there
        folder = self.provider.add_folder(Folder("Test 2"))
        self.assertIn(folder, list(self.provider.list_folders()))
        # delete the folder and make sure its gone
        self.provider.delete_folder(folder)
        self.assertNotIn(folder, list(self.provider.list_folders()))

    def test_delete_undeleteable_folder(self):
        # trying to delete an undeleteable folder shall raise DBError
        self.assertIn(inbox_folder, list(self.provider.list_folders()))
        self.assertRaises(DBError, self.provider.delete_folder, inbox_folder)

    def test_delete_folder_with_threads_attached(self):
        # add a folder
        folder = self.provider.add_folder(Folder("Test 2"))
        self.assertIn(folder, list(self.provider.list_folders()))
        # attach a couple of threads to the folder
        t1 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+322323233', index=5, folder=folder))
        t2 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+322323233', index=6, folder=folder))
        # make sure they appear
        self.assertIn(t1, list(self.provider.list_threads()))
        self.assertIn(t2, list(self.provider.list_threads()))
        # delete the folder and threads should be gone
        self.provider.delete_folder(folder)
        self.assertNotIn(folder, list(self.provider.list_folders()))
        self.assertNotIn(t1, list(self.provider.list_threads()))
        self.assertNotIn(t2, list(self.provider.list_threads()))

    def test_delete_thread(self):
        # add a thread to inbox and make sure its there
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', index=3,
                   folder=inbox_folder))
        self.assertIn(t, list(self.provider.list_threads()))
        # delete it and make sure its gone
        self.provider.delete_thread(t)
        self.assertNotIn(t, list(self.provider.list_threads()))

    def test_delete_thread_with_sms_attached(self):
        # add a thread to inbox
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545332', folder=inbox_folder))
        # add a message attached to that thread and make sure its present
        sms = self.provider.add_sms(
            Message(number='+3443545332', text='how is it going then?',
                    _datetime=get_tz_aware_now(), thread=t))
        self.assertIn(sms, list(self.provider.list_sms()))
        # delete the thread and both the thread and SMS should be gone
        self.provider.delete_thread(t)
        self.assertNotIn(sms, list(self.provider.list_sms()))

    def test_delete_sms(self):
        # add a thread to inbox
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=inbox_folder))
        # add a message attached to that thread and make sure its present
        sms = self.provider.add_sms(
            Message(number='+3443545333', text='how is it going then?',
                    _datetime=get_tz_aware_now(), thread=t))
        self.assertIn(sms, list(self.provider.list_sms()))
        # delete it and make sure its gone
        self.provider.delete_sms(sms)
        self.assertNotIn(sms, list(self.provider.list_sms()))
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_folders(self):
        folders = list(self.provider.list_folders())
        for folder in [inbox_folder, outbox_folder, drafts_folder]:
            self.assertIn(folder, folders)

    def test_list_from_folder(self):
        # add a folder and attach a thread to it
        folder = self.provider.add_folder(Folder("Test 3"))
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=folder))
        # add a thread attached to inbox
        t2 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=inbox_folder))
        # t should be present in threads, but not t2
        threads = list(self.provider.list_from_folder(folder))
        self.assertIn(t, threads)
        self.assertNotIn(t2, threads)
        # leave it as we found it
        self.provider.delete_folder(folder)
        self.provider.delete_thread(t2)

    def test_list_from_folder_and_the_results_order(self):
        """test that list_from_folder returns a correctly ordered result"""
        now = get_tz_aware_now()
        five_min_ago = now - timedelta(minutes=5)
        # add a couple of threads to inbox_folder, one of them
        # just got updated/created and the other five minuts ago
        t = self.provider.add_thread(
            Thread(now, '+3443545333', folder=inbox_folder))
        t2 = self.provider.add_thread(
            Thread(five_min_ago, '+3443545331', folder=inbox_folder))
        # if we list from inbox, t should appear before t2
        threads = list(self.provider.list_from_folder(inbox_folder))
        self.assertEqual(threads[0], t)
        self.assertEqual(threads[1], t2)
        # leave it as we found it
        self.provider.delete_thread(t)
        self.provider.delete_thread(t2)

    def test_list_from_thread(self):
        """test for list_from_thread"""
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=inbox_folder))
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_from_thread sms1',
                    _datetime=get_tz_aware_now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_from_thread sms2',
                    _datetime=get_tz_aware_now(), thread=t))
        # sms1 and sms2 should be present in messages
        messages = list(self.provider.list_from_thread(t))
        self.assertIn(sms1, messages)
        self.assertIn(sms2, messages)
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_from_thread_and_the_results_order(self):
        """test that list_from_thread returns a correctly ordered result"""
        number = '+3443545333'
        now = get_tz_aware_now()
        five_min_ago = now - timedelta(minutes=5)
        # add a thread and attach two messages to it, one just sent
        # and the other is five minutes older
        t = self.provider.add_thread(
            Thread(now, number, folder=inbox_folder))
        sms1 = self.provider.add_sms(
            Message(number=number, text='test_list_from_thread sms1',
                    _datetime=now, thread=t))
        sms2 = self.provider.add_sms(
            Message(number=number, text='test_list_from_thread sms2',
                    _datetime=five_min_ago, thread=t))
        # sms1 and sms2 should be present in messages
        messages = list(self.provider.list_from_thread(t))
        self.assertEqual(messages[0], sms1)
        self.assertEqual(messages[1], sms2)
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_sms(self):
        # add a thread to inbox and attach a couple of messages to it
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=inbox_folder))
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=get_tz_aware_now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=get_tz_aware_now(), thread=t))
        # sms1 and sms2 should be present in messages
        messages = list(self.provider.list_sms())
        self.assertIn(sms1, messages)
        self.assertIn(sms2, messages)
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_threads(self):
        # add two threads to the inbox folder
        t1 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3643445333', folder=inbox_folder))
        t2 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3443545333', folder=inbox_folder))
        # make sure they are present if we list them
        threads = list(self.provider.list_threads())
        self.assertIn(t1, threads)
        self.assertIn(t2, threads)
        # leave it as we found it
        self.provider.delete_thread(t1)
        self.provider.delete_thread(t2)

    def test_move_thread_from_folder_to_folder(self):
        # add a thread to inbox_folder and check its present
        t1 = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3643445333', folder=inbox_folder))
        threads = list(self.provider.list_from_folder(inbox_folder))
        self.assertIn(t1, threads)
        # create a new folder, move t1 to it and check its there
        folder = self.provider.add_folder(Folder("Test 4"))
        self.provider.move_to_folder(t1, folder)
        threads = list(self.provider.list_from_folder(folder))
        self.assertIn(t1, threads)
        self.provider.delete_folder(folder)
        # leave it as we found it
        threads = list(self.provider.list_threads())
        self.assertNotIn(t1, threads)

    def test_move_sms_from_folder_to_folder(self):
        # add a thread to inbox_folder
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), '+3643445333', folder=inbox_folder))
        # add two sms to t1
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=get_tz_aware_now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms 2',
                    _datetime=get_tz_aware_now(), thread=t))
        # sms1 and sms2 should be present in thread
        messages = list(self.provider.list_from_thread(t))
        self.assertIn(sms1, messages)
        self.assertIn(sms2, messages)
        # now create a new folder and move sms2 there
        folder = self.provider.add_folder(Folder("Test 6"))
        self.provider.move_to_folder(sms2, folder)
        # now only sms1 should be present in original thread
        inbox_messages = list(self.provider.list_from_thread(t))
        new_thread = list(self.provider.list_from_folder(folder))[0]
        folder_messages = list(self.provider.list_from_thread(new_thread))
        self.assertIn(sms1, inbox_messages)
        self.assertNotIn(sms2, inbox_messages)
        # and sms2 should be present in folder_messages
        self.assertIn(sms2, folder_messages)
        self.assertNotIn(sms1, folder_messages)
        # leave it as we found it
        self.provider.delete_folder(folder)
        self.provider.delete_thread(t)

    def test_update_sms_flags(self):
        """test that update_sms_flags works as expected"""
        # add a thread to inbox_folder
        number = '+3243242323'
        t = self.provider.add_thread(
            Thread(get_tz_aware_now(), number, folder=inbox_folder))
        # add one sms to t1
        sms1 = self.provider.add_sms(
            Message(number=number, text='test_update_sms_flags',
                    _datetime=get_tz_aware_now(), thread=t))
        self.assertEqual(sms1.flags, READ)
        # now mark sms1 as unread
        sms1 = self.provider.update_sms_flags(sms1, UNREAD)
        self.assertEqual(sms1.flags, UNREAD)
        # leave it as we found it
        self.provider.delete_thread(t)


class TestUsageProvider(unittest.TestCase):
    def setUp(self):
        self.provider = UsageProvider(':memory:')

    def tearDown(self):
        self.provider.close()

    def test_add_usage_item(self):
        now = get_tz_aware_now()
        later = now + timedelta(minutes=30)
        umts, bytes_recv, bytes_sent = True, 12345460, 12333211
        item = self.provider.add_usage_item(now, later, bytes_recv,
                                            bytes_sent, umts)
        usage_items = self.provider.get_usage_for_day(date.today())
        self.assertIn(item, usage_items)
        self.provider.delete_usage_item(item)

    def test_delete_usage_item(self):
        now = get_tz_aware_now()
        later = now + timedelta(minutes=60)
        umts, bytes_recv, bytes_sent = True, 12345470, 12333212
        item = self.provider.add_usage_item(now, later, bytes_recv,
                                            bytes_sent, umts)
        usage_items = self.provider.get_usage_for_day(date.today())
        self.assertIn(item, usage_items)
        self.provider.delete_usage_item(item)
        # now check that it is indeed gone
        usage_items = self.provider.get_usage_for_day(date.today())
        self.assertNotIn(item, usage_items)

    def test_get_usage_for_day(self):
        # add one usage item for today (45m)
        now1 = get_tz_aware_now()
        later1 = now1 + timedelta(minutes=45)
        umts1, bytes_recv1, bytes_sent1 = True, 1200034, 124566
        item1 = self.provider.add_usage_item(now1, later1, bytes_recv1,
                                             bytes_sent1, umts1)
        # add another usage item for today (17m)  55 minutes later
        now2 = get_tz_aware_now() + timedelta(minutes=55)
        later2 = now1 + timedelta(minutes=17)
        umts2, bytes_recv2, bytes_sent2 = True, 12000, 1245
        item2 = self.provider.add_usage_item(now2, later2, bytes_recv2,
                                             bytes_sent2, umts2)

        # add another usage item for tomorrow (25m)
        now3 = get_tz_aware_now() + timedelta(days=1)
        later3 = now3 + timedelta(minutes=25)
        umts3, bytes_recv3, bytes_sent3 = True, 14000, 1785
        item3 = self.provider.add_usage_item(now3, later3, bytes_recv3,
                                             bytes_sent3, umts3)

        # now get the usage for today
        today_items = self.provider.get_usage_for_day(date.today())
        self.assertIn(item1, today_items)
        self.assertIn(item2, today_items)
        self.assertNotIn(item3, today_items)
        # get the usage for tomorrow
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_items = self.provider.get_usage_for_day(tomorrow)
        self.assertNotIn(item1, tomorrow_items)
        self.assertNotIn(item2, tomorrow_items)
        self.assertIn(item3, tomorrow_items)

        # leave it as we found it
        for i in [item1, item2, item3]:
            self.provider.delete_usage_item(i)

    def test_get_usage_for_month(self):
        current_month = date.today().month
        current_year = date.today().year
        # add one usage item for day 12 of this month (45m)
        now1 = datetime(date.today().year, current_month, 12, 13, 10,
                        tzinfo=timezone('UTC'))
        later1 = now1 + timedelta(minutes=45)
        umts1, bytes_recv1, bytes_sent1 = True, 1200034, 124566
        item1 = self.provider.add_usage_item(now1, later1, bytes_recv1,
                                             bytes_sent1, umts1)
        # add another usage item for day 13 of this month (17m)
        now2 = datetime(date.today().year, current_month, 13, 15, 10,
                        tzinfo=timezone('UTC'))
        later2 = now1 + timedelta(minutes=17)
        umts2, bytes_recv2, bytes_sent2 = True, 12000, 1245
        item2 = self.provider.add_usage_item(now2, later2, bytes_recv2,
                                             bytes_sent2, umts2)
        # add another usage item for next month
        if current_month < 12:
            month = current_month + 1
            year = current_year
        else:
            month = 1
            year = current_year + 1

        # next month at 6.50am (25m)
        now3 = datetime(year, month, 2, 6, 50, tzinfo=timezone('UTC'))
        later3 = now3 + timedelta(minutes=25)
        umts3, bytes_recv3, bytes_sent3 = True, 14000, 1785
        item3 = self.provider.add_usage_item(now3, later3, bytes_recv3,
                                             bytes_sent3, umts3)
        # now get the usage for this month
        this_month_items = self.provider.get_usage_for_month(now1.date())
        self.assertIn(item1, this_month_items)
        self.assertIn(item2, this_month_items)
        self.assertNotIn(item3, this_month_items)
        # now get the usage for next month
        next_month_items = self.provider.get_usage_for_month(now3)
        self.assertNotIn(item1, next_month_items)
        self.assertNotIn(item2, next_month_items)
        self.assertIn(item3, next_month_items)
        # leave it as we found it
        for i in [item1, item2, item3]:
            self.provider.delete_usage_item(i)

    def test_get_total_usage(self):
        current_month = date.today().month
        current_year = date.today().year
        # add one usage item for day 12 of this month (45m)
        now1 = datetime(current_year, current_month, 12, 13, 10,
                        tzinfo=timezone('UTC'))
        later1 = now1 + timedelta(minutes=45)
        umts1, bytes_recv1, bytes_sent1 = True, 1200034, 124566
        item1 = self.provider.add_usage_item(now1, later1, bytes_recv1,
                                             bytes_sent1, umts1)
        # add another usage item for day 13 of this month (17m), one year ago
        now2 = datetime(current_year - 1, current_month, 13, 15, 10,
                        tzinfo=timezone('UTC'))
        later2 = now1 + timedelta(minutes=17)
        umts2, bytes_recv2, bytes_sent2 = True, 12000, 1245
        item2 = self.provider.add_usage_item(now2, later2, bytes_recv2,
                                             bytes_sent2, umts2)

        items = self.provider.get_total_usage()
        self.assertIn(item1, items)
        self.assertIn(item2, items)
        # leave it as we found it
        for i in [item1, item2]:
            self.provider.delete_usage_item(i)

    def test_get_total_usage_passing_a_date(self):
        current_month = date.today().month
        current_year = date.today().year
        # add one usage item for day 12 of this month (45m)
        now1 = datetime(current_year, current_month, 12, 13, 10,
                        tzinfo=timezone('UTC'))
        later1 = now1 + timedelta(minutes=45)
        umts1, bytes_recv1, bytes_sent1 = True, 1200034, 124566
        item1 = self.provider.add_usage_item(now1, later1, bytes_recv1,
                                             bytes_sent1, umts1)
        # add another usage item for day 13 of this month (17m), one year ago
        now2 = datetime(current_year - 1, current_month, 13, 15, 10,
                        tzinfo=timezone('UTC'))
        later2 = now1 + timedelta(minutes=17)
        umts2, bytes_recv2, bytes_sent2 = True, 12000, 1245
        item2 = self.provider.add_usage_item(now2, later2, bytes_recv2,
                                             bytes_sent2, umts2)

        items = self.provider.get_total_usage(now1.date())
        self.assertIn(item1, items)
        self.assertNotIn(item2, items)
        # leave it as we found it
        for i in [item1, item2]:
            self.provider.delete_usage_item(i)
