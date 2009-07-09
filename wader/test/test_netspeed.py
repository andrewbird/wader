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
"""Unittests for wader.common.netspeed"""

from twisted.trial import unittest

from wader.common.netspeed import bps_to_human

class TestNetSpeed(unittest.TestCase):
    """Tests for wader.common.netspeed"""

    def test_bps_to_human(self):
        self.assertEqual(bps_to_human(1001, 1000), ('1.00 Kbps', '1.00 Kbps'))
        self.assertEqual(bps_to_human(1000001, 1000001),
                         ('1.00 Mbps', '1.00 Mbps'))
        self.assertEqual(bps_to_human(100, 100), ('100.00 bps', '100.00 bps'))

