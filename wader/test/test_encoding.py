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

from wader.common.encoding import (CONTROL_0, CONTROL_1, LATIN_EX_A,
                                   LATIN_EX_B, check_if_ucs2,
                                   pack_ucs2_bytes, unpack_ucs2_bytes)

CTL_0 = '007F'
CTL_1 = '00FF'
LTN_A = '017F'
LTN_B = '024F'


class TestEncoding(unittest.TestCase):
    """Tests for encoding"""

    def test_check_if_ucs2(self):
        self.assertEqual(check_if_ucs2(CTL_0), True)
        self.assertEqual(check_if_ucs2(CTL_1), True)
        self.assertEqual(check_if_ucs2(LTN_A), True)
        self.assertEqual(check_if_ucs2(LTN_B), True)
        self.assertEqual(check_if_ucs2('6C34'), True)
        self.assertEqual(
            check_if_ucs2('0056006F006400610066006F006E0065'), True)
        self.assertEqual(check_if_ucs2('003'), False)

        # XXX: This should be invalid but fails at the moment
        self.assertEqual(check_if_ucs2('D834DD1E'), False)

    def test_check_if_ucs2_limit_control_0(self):
        self.assertEqual(check_if_ucs2(CTL_0, limit=CONTROL_0), True)
        self.assertEqual(check_if_ucs2(CTL_1, limit=CONTROL_0), False)
        self.assertEqual(check_if_ucs2(LTN_A, limit=CONTROL_0), False)
        self.assertEqual(check_if_ucs2(LTN_B, limit=CONTROL_0), False)
        self.assertEqual(check_if_ucs2('6C34', limit=CONTROL_0), False)
        self.assertEqual(
            check_if_ucs2(CTL_0 + CTL_0 + CTL_0, limit=CONTROL_0), True)
        self.assertEqual(
            check_if_ucs2('6C34' + CTL_0 + CTL_0, limit=CONTROL_0), False)
        self.assertEqual(
            check_if_ucs2(CTL_0 + '6C34' + CTL_0, limit=CONTROL_0), False)
        self.assertEqual(
            check_if_ucs2(CTL_0 + CTL_0 + '6C34', limit=CONTROL_0), False)

    def test_check_if_ucs2_limit_control_1(self):
        self.assertEqual(check_if_ucs2(CTL_0, limit=CONTROL_1), True)
        self.assertEqual(check_if_ucs2(CTL_1, limit=CONTROL_1), True)
        self.assertEqual(check_if_ucs2(LTN_A, limit=CONTROL_1), False)
        self.assertEqual(check_if_ucs2(LTN_B, limit=CONTROL_1), False)
        self.assertEqual(check_if_ucs2('6C34', limit=CONTROL_1), False)
        self.assertEqual(
            check_if_ucs2(CTL_1 + CTL_1 + CTL_1, limit=CONTROL_1), True)
        self.assertEqual(
            check_if_ucs2('6C34' + CTL_1 + CTL_1, limit=CONTROL_1), False)
        self.assertEqual(
            check_if_ucs2(CTL_1 + '6C34' + CTL_1, limit=CONTROL_1), False)
        self.assertEqual(
            check_if_ucs2(CTL_1 + CTL_1 + '6C34', limit=CONTROL_1), False)

    def test_check_if_ucs2_limit_extended_latin_a(self):
        self.assertEqual(check_if_ucs2(CTL_0, limit=LATIN_EX_A), True)
        self.assertEqual(check_if_ucs2(CTL_1, limit=LATIN_EX_A), True)
        self.assertEqual(check_if_ucs2(LTN_A, limit=LATIN_EX_A), True)
        self.assertEqual(check_if_ucs2(LTN_B, limit=LATIN_EX_A), False)
        self.assertEqual(check_if_ucs2('6C34', limit=LATIN_EX_A), False)
        self.assertEqual(
            check_if_ucs2(LTN_A + LTN_A + LTN_A, limit=LATIN_EX_A), True)
        self.assertEqual(
            check_if_ucs2('6C34' + LTN_A + LTN_A, limit=LATIN_EX_A), False)
        self.assertEqual(
            check_if_ucs2(LTN_A + '6C34' + LTN_A, limit=LATIN_EX_A), False)
        self.assertEqual(
            check_if_ucs2(LTN_A + LTN_A + '6C34', limit=LATIN_EX_A), False)

    def test_check_if_ucs2_limit_extended_latin_b(self):
        self.assertEqual(check_if_ucs2(CTL_0, limit=LATIN_EX_B), True)
        self.assertEqual(check_if_ucs2(CTL_1, limit=LATIN_EX_B), True)
        self.assertEqual(check_if_ucs2(LTN_A, limit=LATIN_EX_B), True)
        self.assertEqual(check_if_ucs2(LTN_B, limit=LATIN_EX_B), True)
        self.assertEqual(check_if_ucs2('6C34', limit=LATIN_EX_B), False)
        self.assertEqual(
            check_if_ucs2(LTN_B + LTN_B + LTN_B, limit=LATIN_EX_B), True)
        self.assertEqual(
            check_if_ucs2('6C34' + LTN_B + LTN_B, limit=LATIN_EX_B), False)
        self.assertEqual(
            check_if_ucs2(LTN_B + '6C34' + LTN_B, limit=LATIN_EX_B), False)
        self.assertEqual(
            check_if_ucs2(LTN_B + LTN_B + '6C34', limit=LATIN_EX_B), False)

    def test_pack_ucs2_bytes(self):
        # 07911356131313F311000A9260214365870008AA080068006F006C0061
        self.assertEqual(pack_ucs2_bytes('hola'), '0068006F006C0061')
        # 07911356131313F311000A9260214365870008AA0A0068006F006C00610073
        self.assertEqual(pack_ucs2_bytes('holas'), '0068006F006C00610073')

        self.assertEqual(pack_ucs2_bytes(u"中华人民共和国"),
                         '4E2D534E4EBA6C115171548C56FD')

    def test_unpack_ucs2_bytes(self):
        self.assertEqual(unpack_ucs2_bytes('0068006F006C0061'), 'hola')
        resp = 'holas'
        self.assertEqual(unpack_ucs2_bytes('0068006F006C00610073'), resp)
