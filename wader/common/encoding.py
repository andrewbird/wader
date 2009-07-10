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
    return codecs.utf_16_be_decode(s.decode('hex'))[0]

def unpack_ucs2_bytes_in_ts31101_80(s):
    """
    Returns a string from ``s`` which is encoded in TS 31.101 (Annex A) type 80

    Check out the function comments
    """

    # Below is the detail from there, but we expect the first two hex
    # chars(80) to have been removed already.

    # If the first byte in the alpha string is '80', then the remaining
    # bytes are 16 bit UCS2 characters, with the more significant byte (MSB)
    # of the UCS2 character coded in the lower numbered byte of the alpha
    # field, and the less significant byte (LSB) of the UCS2 character is
    # coded in the higher numbered alpha field byte, i.e. byte 2 of the
    # alpha field contains the more significant byte (MSB) of the first UCS2
    # character, and byte 3 of the alpha field contains the less significant
    # byte (LSB) of the first UCS2 character (as shown below). Unused bytes
    # shall be set to 'FF', and if the alpha field is an even number of bytes
    # in length, then the last (unusable) byte shall be set to 'FF'.
    #
    # example string '058300440586FF'

    vl = len(s) - len(s) % 4
    vs = s[:vl]
    try:
        t = unpack_ucs2_bytes(vs)
    except:
        t = vs # show the invalid unicode

    return t

def unpack_ucs2_bytes_in_ts31101_81(s):
    """
    Returns a string from ``s`` which is encoded in TS 31.101 (Annex A) type 81

    Check out the function comments
    """
    # Below is the detail from there, but we expect the first two hex
    # chars(81) to have been removed already.
    # If the first byte of the alpha string is set to '81', then the second
    # byte contains a value indicating the number of characters in the string,
    # and the third byte contains an 8 bit number which defines bits 15 to 8
    # of a 16 bit base pointer, where bit 16 is set to zero, and bits 7 to 1
    # are also set to zero. These sixteen bits constitute a base pointer
    # to a "half-page" in the UCS2 code space, to be used with some or all of
    # the remaining bytes in the string. The fourth and subsequent bytes in
    # the string contain codings as follows; if bit 8 of the byte is set to
    # zero, the remaining 7 bits of the byte contain a GSM Default Alphabet
    # character, whereas if bit 8 of the byte is set to one, then the
    # remaining seven bits are an offset value added to the 16 bit base
    # pointer defined earlier, and the resultant 16 bit value is a UCS2 code
    # point, and completely defines a UCS2 character.
    #
    # example string '0602A46563746F72FF'

    num = ord(s[:2].decode('hex'))
    base = (ord(s[2:4].decode('hex')) & 0x7f) << 7 # bits 15..8
    chars = s[4:4+num*2]

    t = ''
    for i in range(num):
        j = i*2
        c_hex = chars[j:j+2]
        c_chr = c_hex.decode('hex')
        c_ord = ord(c_chr)

        if c_ord & 0x80 == 0:
            t += c_chr
        else:
            t += unichr(base + (c_ord & 0x7f))
    return t

def unpack_ucs2_bytes_in_ts31101_82(s):
    """
    Returns a string from ``s`` which is encoded in TS 31.101 (Annex A) type 82

    Check out the function comments
    """

    # Below is the detail from there, but we expect the first two hex
    # chars(82) to have been removed already.
    # If the first byte of the alpha string is set to '82', then the
    # second byte contains a value indicating the number of characters
    # in the string, and the third and fourth bytes contain a 16 bit number
    # which defines the complete 16 bit base pointer to a "half-page" in the
    # UCS2 code space, for use with some or all of the remaining bytes in the
    # string. The fifth and subsequent bytes in the string contain codings as
    # follows; if bit 8 of the byte is set to zero, the remaining 7 bits of
    # the byte contain a GSM Default Alphabet character, whereas if bit 8 of
    # the byte is set to one, the remaining seven bits are an offset value
    # added to the base pointer defined in bytes three and four, and the
    # resultant 16 bit value is a UCS2 code point, and defines a UCS2 character
    #
    # example string '0505302D82D32D31'

    num = ord(s[:2].decode('hex'))
    base = ord(s[2:4].decode('hex')) << 8 # bits 16..9
    base += ord(s[4:6].decode('hex'))     # bits  8..1
    chars = s[6:6+num*2]

    t = ''
    for i in range(num):
        j = i*2
        c_hex = chars[j:j+2]
        c_chr = c_hex.decode('hex')
        c_ord = ord(c_chr)

        if c_ord & 0x80 == 0:
            t += c_chr
        else:
            t += unichr(base + (c_ord & 0x7f))
    return t

def check_if_ucs2(text):
    """
    Test whether ``s`` is a UCS2 encoded string

    :rtype: bool
    """
    if isinstance(text, str) and (len(text) % 4 == 0):
        try:
            unpack_ucs2_bytes(text)
        except (UnicodeDecodeError, TypeError):
            return False
        else:
            return True

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

