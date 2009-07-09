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
"""Unittests for the persistent module"""

import os

from twisted.trial import unittest

from wader.common.persistent import populate_networks, get_network_by_id

TMPFILE = '/tmp/foo.db'


class TestNetworksManager(unittest.TestCase):
    """
    Tests for the NetworksManager
    """
    def setUpClass(self):
        networks = __import__('resources/extra/networks')
        instances = [getattr(networks, item)() for item in dir(networks)
            if (not item.startswith('__') and item != 'NetworkOperator')]
        populate_networks(instances, TMPFILE)

    def tearDownClass(self):
        os.unlink(TMPFILE)

    def test_lookup_network(self):
        """
        Test that looking up a known netid
        """
        network = get_network_by_id("21401", TMPFILE)
        self.assertEqual(network.name, 'Vodafone')
        self.assertEqual(network.country, 'Spain')

    def test_lookup_inexistent_network(self):
        """
        Test that looking up an unknown netid (6002 atm) returns None
        """
        network = get_network_by_id("6002", TMPFILE)
        self.assertEqual(network, None)

