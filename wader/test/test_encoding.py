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
"""Unittests for the encoding module"""

from twisted.trial import unittest

from wader.common.encoding import (check_if_ucs2,
                                   pack_ucs2_bytes, unpack_ucs2_bytes)

class TestEncoding(unittest.TestCase):
    """Tests for encoding"""

    def test_check_if_ucs2(self):
        self.assertEqual(check_if_ucs2('6C34'), True)
        self.assertEqual(check_if_ucs2('0056006F006400610066006F006E0065'),
                         True)
        # XXX: This should fail but doesn't
        self.assertEqual(check_if_ucs2('D834DD1E'), False)

    def test_pack_ucs2_bytes(self):
        # 07911356131313F311000A9260214365870008AA080068006F006C0061
        self.assertEqual(pack_ucs2_bytes('hola'), '0068006F006C0061')
        # 07911356131313F311000A9260214365870008AA0A0068006F006C00610073
        self.assertEqual(pack_ucs2_bytes('holas'), '0068006F006C00610073')

    def test_unpack_ucs2_bytes(self):
        self.assertEqual(unpack_ucs2_bytes('0068006F006C0061'), 'hola')
        resp = 'holas'
        self.assertEqual(unpack_ucs2_bytes('0068006F006C00610073'), resp)

