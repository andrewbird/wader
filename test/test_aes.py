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
"""Unittests for the aes module"""

from cStringIO import StringIO
import os
import pickle
import random
from twisted.trial import unittest

from wader.common.aes import encryptData, decryptData


def transform_passwd(passwd):
    valid_lengths = [16, 24, 32]
    for l in valid_lengths:
        if l >= len(passwd):
            return passwd.zfill(l)

    msg = "Password '%s' is too long, max length is 32 chars"
    raise Exception(msg % passwd)


def make_gsm_dict(passwd):
    return {'gsm': {'passwd': passwd}}


class TestEncoding(unittest.TestCase):
    """Tests for encoding"""

    def test_decode_fixed(self):

        T = [('b7b96d81cc86e6f9',
                '',
                'cb867e4037a302198ee51523393923996cf56621de3e21ca46c147c7635a'
                '4597287a45f17dd984ccf9195db3b21e404007959d57fdd12594e96cb65d'
                'fc453f6d'),
            ('0000000000497a9b',
                '2ed9eff633',
                'e53100eac23d4afb2a0ed0f3b16b0a35066f71fea80a3559c2d21d368173'
                '8c0042d2f8bdbb4467eea3bf7102922fdb5f14ddc810837bc8ded8fcf40e'
                '717e82c5cee71acbe17d1135b99e5115c6cf881d'),
            ('000000000000d07d',
                '9771d7edad6b',
                '2a682d46c4ce665ba7acc238f11f50c836defd05de1431a2af5ab47dd4f4'
                '6c775a91b26fc087f347d5f1fe592575d3b1681372777e943ffaa2f77e81'
                'e5c5ab6d32fa420c261ecebc72a3daf96e69ba4e'),
            ('39db1d780077cf13',
                '',
                '583c69ee32ced39574654a64701eb36d04e98d052976d840be4691d12a51'
                '7e1839f6208354ca244abcf28d6e9fecbef7c5559417c1e23285802a8ffc'
                'ca907ff7'),
            ('00000000000052e0',
                '17a0b94b488e',
                '15e06ff63bd85c6b06a2d2f6a36128fa0154cdb7778676c5bd589ca0c3ea'
                'ac4b8f179002b69d322b110f10a208e365285f7aff5ada1d36ee6cfc140e'
                '77f1f25b8ea13185b2add3896071a2fbf0bdd051'),
            ('00000000004ccb76',
                '034604574e',
                '3a058a4cb44af041b7e9609e0b05d2607b74e358f2046402671a715ee5c2'
                '453d5beb41acb8a01fd4278ceb2a58d07002ee92b567b3f60d68311aadd4'
                '538715022930390e43fe41853f6587261eae4dde'),
            ('e477fd4e2ab84397',
                '',
                'd9b1ee5dadede634e5e508a9de6d2c5f5179efb5da65dcd4721d8c9fe6d1'
                '011eec6672a93e619413b20960b66b8c2a770ab736f83767434a0e03f392'
                '6fd967ca'),
            ('00000073966b9008',
                '15eed9',
                'f87df3422f9a8e95c89149be782de06ca6c4d4189a2c5686d1186b51ebf2'
                'dad879f15c1eb1943dd6e321e05dcc9759ef25189cc7980e6b3a8ae5ab38'
                'f6fb20e31b4fe49929c8613f699dfe6b2adc71bf'),
            ('0000e34a67f172f8',
                '41dfd679b972',
                '490cc79eed800e217ab62702284d3e5c61022b8ec0459eb54ec1fd2071e1'
                'e486f6a7d895b2ef34553dba1daed165a1d8a61e439cfa83777f1b5a97d0'
                'c8e2ac081ef3fa703083c3db97211b33630ec2b1'),
            ('0000000000000018',
                'f462f7e7aa525d1125cd7f',
                '17bfeab05df5be698372e71c107b5ac750846cc9e5d0259ea706945889a7'
                '70699f2f5229e4ed03f47a5b755d66cceb0d9796ec0e09ed28413986e447'
                '84fa9158a6ed086d98aca1558266b4db6150c1b9fa83b5597ea17559422b'
                'ee95b9272afd'),
            ('0000000986b93eda',
                '785964d244f22e',
                '1459254a9dbe14a088acb911badff5b17d2993541a7080c6cc01de99096b'
                '48a81fed141f38a7843a55a88ad8b065394afde5a8a735b773a266cdbc20'
                '59fa73b2ebd25d47e71350c0e5b5f6bb352a7def'),
            ('0000002ef2b543f79bb97371',
                '447759',
                '55d47083f0cb00b9dd4065530f2ea67eb0065c20d4efe9f0125cf4b47785'
                '6268bd1718d544d3346c7d12d6293a222318890cc3c32ec776e711add688'
                '13a0bb0bdcbdb82e6244fd56f477a578d452b763'),
            ('b5f166646d9dde97',
                '9c082a9c',
                'a3408b3e99b0fced6bda3eb648714169814f2260157c82d28780aacb30b0'
                '9905928fbf5bcfd98188d7dd185e625a3b05bd312e211b4a96f88e796a4a'
                'ee137319afa8a7726f2dc0190c1e3c8377633dfe'),
            ('0000000085532a66',
                'db57406690243f06',
                'c0015c98db59407a43d09401aadef3bdab330d9926cffb8f9d7b0f8bbff5'
                'b07a062b6fe6c2bc77bcd5d55f8c81fc943e772c86666cd875c007804226'
                '3f6a3dcca0acd83483156a744cbafbee0d43c0b3'),
            ('00000000005bd30e',
                '559958a4411bf08e0f',
                '270bba1a98649e37ec0de94d46085fcbbe50f50688f2eb5848bcb5aa601d'
                'c98eb6e714b85c3679d21dd4a59beec82d48f09db11da49283bc261df59b'
                '770c20027ab75c190126875d118c8e659e4a7465'),
            ('00000b78961f4a341ce23df7',
                '4c73',
                'f65de12f497d67e1d65902f4ed34e5c3ef0e881ae3942f29391e0f7fc7f8'
                '4a7bf67dea6b2d7c3e5cbbdb0801ed89703bb3b325b063d96b9eec7a11ed'
                '229361dc')]

        for t in T:
            original = make_gsm_dict(t[1])

            # decode
            pickledobj = decryptData(t[0], t[2].decode('hex'),
                                                            testforpickle=True)
            decrypted = pickle.load(StringIO(pickledobj))

            self.assertEqual(decrypted, original)

    def test_encode_decode(self):
        n_keys = 8
        n_passwds = 8

        LEN = 12

        for keys in range(n_keys):
            length = int(random.random() * LEN)

            key = os.urandom(LEN - length).encode('hex')
            padded_key = transform_passwd(key)

            for passwds in range(n_passwds):
                passwd = os.urandom(length).encode('hex')

                original = make_gsm_dict(passwd)

                # encode
                encrypted = encryptData(padded_key, pickle.dumps(original))

                # decode
                pickledobj = decryptData(padded_key, encrypted)
                decrypted = pickle.load(StringIO(pickledobj))

                self.assertEqual(decrypted, original)
