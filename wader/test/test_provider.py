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

from datetime import datetime, timedelta
import sqlite3
from time import time

from twisted.trial import unittest

from wader.common.provider import (SMS_SCHEMA, SmsProvider, Message, Folder,
                                   Thread, DBError, inbox_folder,
                                   outbox_folder, drafts_folder, READ, UNREAD,
                                   message_read)

class TestDBTriggers(unittest.TestCase):
    """Tests for the DB triggers"""

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
        date = c.fetchone()[0]
        self.assertEqual(now, date)
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
                      _datetime=datetime.now())
        sms = self.provider.add_sms(sms)
        self.assertIn(sms, list(self.provider.list_sms()))
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
                Thread(datetime.now(), '+322323233', index=5, folder=folder))
        t2 = self.provider.add_thread(
                Thread(datetime.now(), '+322323233', index=6, folder=folder))
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
           Thread(datetime.now(), '+3443545333', index=3, folder=inbox_folder))
        self.assertIn(t, list(self.provider.list_threads()))
        # delete it and make sure its gone
        self.provider.delete_thread(t)
        self.assertNotIn(t, list(self.provider.list_threads()))

    def test_delete_thread_with_sms_attached(self):
        # add a thread to inbox
        t = self.provider.add_thread(
            Thread(datetime.now(), '+3443545332', folder=inbox_folder))
        # add a message attached to that thread and make sure its present
        sms = self.provider.add_sms(
            Message(number='+3443545332', text='how is it going then?',
                    _datetime=datetime.now(), thread=t))
        self.assertIn(sms, list(self.provider.list_sms()))
        # delete the thread and both the thread and SMS should be gone
        self.provider.delete_thread(t)
        self.assertNotIn(sms, list(self.provider.list_sms()))

    def test_delete_sms(self):
        # add a thread to inbox
        t = self.provider.add_thread(
            Thread(datetime.now(), '+3443545333', folder=inbox_folder))
        # add a message attached to that thread and make sure its present
        sms = self.provider.add_sms(
            Message(number='+3443545333', text='how is it going then?',
                    _datetime=datetime.now(), thread=t))
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
            Thread(datetime.now(), '+3443545333', folder=folder))
        # add a thread attached to inbox
        t2 = self.provider.add_thread(
            Thread(datetime.now(), '+3443545333', folder=inbox_folder))
        # t should be present in threads, but not t2
        threads = list(self.provider.list_from_folder(folder))
        self.assertIn(t, threads)
        self.assertNotIn(t2, threads)
        # leave it as we found it
        self.provider.delete_folder(folder)
        self.provider.delete_thread(t2)

    def test_list_from_folder_and_the_results_order(self):
        """test that list_from_folder returns a correctly ordered result"""
        now = datetime.now()
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
            Thread(datetime.now(), '+3443545333', folder=inbox_folder))
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_from_thread sms1',
                    _datetime=datetime.now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_from_thread sms2',
                    _datetime=datetime.now(), thread=t))
        # sms1 and sms2 should be present in messages
        messages = list(self.provider.list_from_thread(t))
        self.assertIn(sms1, messages)
        self.assertIn(sms2, messages)
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_from_thread_and_the_results_order(self):
        """test that list_from_thread returns a correctly ordered result"""
        number = '+3443545333'
        now = datetime.now()
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
            Thread(datetime.now(), '+3443545333', folder=inbox_folder))
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=datetime.now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=datetime.now(), thread=t))
        # sms1 and sms2 should be present in messages
        messages = list(self.provider.list_sms())
        self.assertIn(sms1, messages)
        self.assertIn(sms2, messages)
        # leave it as we found it
        self.provider.delete_thread(t)

    def test_list_threads(self):
        # add two threads to the inbox folder
        t1 = self.provider.add_thread(
            Thread(datetime.now(), '+3643445333', folder=inbox_folder))
        t2 = self.provider.add_thread(
            Thread(datetime.now(), '+3443545333', folder=inbox_folder))
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
            Thread(datetime.now(), '+3643445333', folder=inbox_folder))
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
            Thread(datetime.now(), '+3643445333', folder=inbox_folder))
        # add two sms to t1
        sms1 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms',
                    _datetime=datetime.now(), thread=t))
        sms2 = self.provider.add_sms(
            Message(number='+3443545333', text='test_list_sms 2',
                    _datetime=datetime.now(), thread=t))
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
            Thread(datetime.now(), number, folder=inbox_folder))
        # add one sms to t1
        sms1 = self.provider.add_sms(
            Message(number=number, text='test_update_sms_flags',
                    _datetime=datetime.now(), thread=t))
        self.assertEqual(sms1.flags, READ)
        # now mark sms1 as unread
        sms1 = self.provider.update_sms_flags(sms1, UNREAD)
        self.assertEqual(sms1.flags, UNREAD)
        # leave it as we found it
        self.provider.delete_thread(t)


