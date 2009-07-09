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
"""Unittests for the aterrors module"""

from twisted.trial import unittest
from wader.common.aterrors import extract_error
import wader.common.aterrors as E

class TestATErrors(unittest.TestCase):
    """Tests for wader.common.aterrors"""

    def test_cme_errors_string(self):
        raw = '\r\n+CME ERROR: SIM interface not started\r\n'
        self.assertEqual(extract_error(raw)[0], E.SimNotStarted)
        raw2 = 'AT+CPIN=1330\r\n\r\n+CME ERROR: operation not allowed\r\n'
        self.assertEqual(extract_error(raw2)[0], E.OperationNotAllowed)
        raw3 = '\r\n+CME ERROR: SIM busy\r\n'
        self.assertEqual(extract_error(raw3)[0], E.SimBusy)

    def test_cme_errors_numeric(self):
        raw = '\r\n+CME ERROR: 30\r\n'
        self.assertEqual(extract_error(raw)[0], E.NoNetwork)
        raw = '\r\n+CME ERROR: 100\r\n'
        self.assertEqual(extract_error(raw)[0], E.Unknown)
        raw = '\r\n+CME ERROR: 14\r\n'
        self.assertEqual(extract_error(raw)[0], E.SimBusy)

    def test_cms_errors(self):
        raw = '\r\n+CMS ERROR: 500\r\n'
        self.assertEqual(extract_error(raw)[0], E.CMSError500)
        raw2 = '\r\n+CMS ERROR: 301\r\n'
        self.assertEqual(extract_error(raw2)[0], E.CMSError301)

