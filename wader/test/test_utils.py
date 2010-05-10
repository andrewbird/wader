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
"""
tests for the wader.common.utils module
"""

import os
from random import shuffle, randint
from datetime import datetime
from pytz import timezone

from twisted.trial import unittest

from wader.common.utils import (get_file_data, save_file, natsort,
                                convert_ip_to_int, convert_int_to_ip,
                                rssi_to_percentage, flatten_list,
                                revert_dict, get_tz_aware_now)


def ip_generator(n):
    c = 0
    while c < n:
        yield "%d.%d.%d.%d" % (randint(0, 255), randint(0, 255),
                               randint(0, 255), randint(0, 255))
        c += 1


class TestUtilities(unittest.TestCase):

    def test_get_file_data(self):
        """
        Test reading a random file with ``get_file_data``
        """
        text = os.urandom(2000)
        path = '/tmp/file.foo'
        fobj = open(path, 'w')
        fobj.write(text)
        fobj.close()

        self.assertEqual(text, get_file_data(path))
        os.unlink(path)

    def test_save_file(self):
        """
        Tests that saving a random file works with ``save_file``
        """
        text = os.urandom(2000)
        path = '/tmp/file.foo'

        save_file(path, text)

        fobj = open(path, 'r')
        data = fobj.read()
        fobj.close()

        self.assertEqual(text, data)
        os.unlink(path)

    def test_natsort(self):
        """
        Test that the ``natsort`` function works as expected
        """
        l = []
        for i in range(15):
            l.append("ttyUSB%d" % i)

        unordered = l[:]
        shuffle(unordered)

        self.assertNotIdentical(l, unordered)
        natsort(unordered)
        self.assertEqual(l, unordered)

    def test_ip_to_int_conversion(self):
        for ip in ip_generator(50000):
            num = convert_ip_to_int(ip)
            self.failIf(num < 0)
            self.assertEqual(ip, convert_int_to_ip(num))

    def test_rssi_to_percentage(self):
        self.assertEqual(rssi_to_percentage(31), 100)
        self.assertEqual(rssi_to_percentage(32), 0)
        self.assertEqual(rssi_to_percentage(0), 0)

    def test_flatten_list(self):
        self.assertEqual(flatten_list([1, 2, [5, 6]]), [1, 2, 5, 6])
        self.assertEqual(flatten_list([1, 2, (5, 6)]), [1, 2, 5, 6])

        self.assertEqual(flatten_list([1, iter([2, 3, 4])]), [1, 2, 3, 4])

    def test_revert_dict(self):
        self.assertEqual(revert_dict({'a': 'b'}), {'b': 'a'})
        self.assertEqual(revert_dict(dict(foo='bar')), dict(bar='foo'))

    def test_get_tz_aware_now(self):
        now1 = get_tz_aware_now()
        now2 = datetime.now(timezone('Europe/Paris'))
        diff = now2 - now1
        self.assertNotEqual(now1.tzinfo, None)
        self.failIf(abs(now2 - now1).seconds > 5)
