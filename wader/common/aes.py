# -*- coding: utf-8 -*-
# Copyright (C) 2011  Vodafone España, S.A.
# Author:  Andrew Bird
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
"""Replacement for the old aes module"""

from M2Crypto.EVP import Cipher

ALGS = {
    16: 'aes_128_cbc',
    24: 'aes_192_cbc',
    32: 'aes_256_cbc'
}


def decryptData(key, encoded, testforpickle=False):
    iv = '\0' * 16
    cipher = Cipher(alg=ALGS[len(key)], key=key, iv=iv, op=0)

    decoded = cipher.update(encoded)
    decoded = decoded + cipher.final()

    # old format encryption seems to have 16 bytes before pickled data
    if testforpickle and not decoded.startswith('(dp'):
        return decoded[16:]
    return decoded


def encryptData(key, data):
    iv = '\0' * 16
    cipher = Cipher(alg=ALGS[len(key)], key=key, iv=iv, op=1)

    encoded = cipher.update(data)
    encoded = encoded + cipher.final()

    return encoded
