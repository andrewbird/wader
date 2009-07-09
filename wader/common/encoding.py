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
"""Helper methods for dealing with encoded strings"""

import codecs

ucs2_encoder = codecs.getencoder("utf_16be")
ucs2_decoder = codecs.getdecoder("utf_16be")
hex_decoder = codecs.getdecoder("hex_codec")

def pack_ucs2_bytes(s):
    """
    Converts string ``s`` to UCS2

    :rtype: str
    """
    return "".join(["%02X" % ord(c) for c in ucs2_encoder(s)[0]])

def unpack_ucs2_bytes(s):
    """
    Unpacks string ``s`` from UCS2

    :rtype: unicode
    """
    octets = [ord(c) for c in hex_decoder(s)[0]]
    user_data = "".join(chr(o) for o in octets)
    return ucs2_decoder(user_data)[0]

def check_if_ucs2(s):
    """
    Test whether ``s`` is a UCS2 encoded string

    :rtype: bool
    """
    if isinstance(s, str) and s.startswith('00'):
        try:
            unpack_ucs2_bytes(s)
            return True
        except (UnicodeDecodeError, TypeError):
            pass

    return False

def from_u(s):
    """
    Encodes ``s`` to utf-8 if its not already encoded

    :rtype: str
    """
    return (s.encode('utf8') if isinstance(s, unicode) else s)

def from_ucs2(s):
    """
    Converts ``s`` from UCS2 if not already converted

    :rtype: str
    """
    return (unpack_ucs2_bytes(s) if check_if_ucs2(s) else s)

def to_u(s):
    """
    Converts ``s`` to unicode if not already converted

    :rtype: unicode
    """
    return (s if isinstance(s, unicode) else unicode(s, 'utf8'))

