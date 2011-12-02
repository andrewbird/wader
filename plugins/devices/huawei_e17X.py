# -*- coding: utf-8 -*-
# Copyright (C) 2010-2011  Vodafone España, S.A.
# Author:  Jaime Soriano
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

from twisted.internet import defer

import wader.common.aterrors as E
from wader.common import consts
from core.hardware.base import build_band_dict
from core.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper,
                                          HUAWEI_BAND_DICT)


class HuaweiE17XWrapper(HuaweiWCDMAWrapper):

    def get_phonebook_size(self):
        # the E170 that we have around keeps raising Generals whenever
        # is asked for its size, we'll have to cheat till we have time
        # to find a workaround
        d = super(HuaweiE17XWrapper, self).get_phonebook_size()
        d.addErrback(lambda failure: defer.succeed(200))
        return d

    def list_contacts(self):
        # Return a list of all the contacts without knowing the phonebook size
        #
        # 1. We first find the highest index of what's there already
        # 2. We can't use the results of the AT+CPBF='' search because it
        #    returns rubbish for valid contacts stored on the SIM by other
        #    devices. That means any contact not written by an E172 using
        #    AT+CPBW is invalid without this method.
        # 3. Now we can use the derived range to use the Huawei proprietary
        #    command to return the proper results.

        def get_max_index_cb(matches):
            indexes = map(int, [m.group('id') for m in matches])
            return max(indexes)

        def no_contacts_eb(failure):
            failure.trap(E.NotFound, E.General)
            return 0

        def get_valid_contacts(_max):
            if not _max:
                return defer.succeed([])

            def results_cb(matches):
                return [self._regexp_to_contact(m) for m in matches]

            return self.send_at('AT^CPBR=1,%d' % _max, name='list_contacts',
                                callback=results_cb)

        d = self.send_at('AT+CPBF=""', name='find_contacts',
                         callback=get_max_index_cb)
        d.addErrback(no_contacts_eb)
        d.addCallback(get_valid_contacts)
        return d

    def send_ussd(self, ussd):
        return self._send_ussd_ucs2_mode(ussd)


class HuaweiE17XCustomizer(HuaweiWCDMACustomizer):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMACustomizer` for the E17X
    """
    wrapper_klass = HuaweiE17XWrapper

    # GSM/GPRS/EDGE 850/900/1800 MHz
    # HSDPA/UMTS 2100 MHz
    band_dict = build_band_dict(
                  HUAWEI_BAND_DICT,
                  [consts.MM_NETWORK_BAND_ANY,

                   consts.MM_NETWORK_BAND_G850,#  850
                   consts.MM_NETWORK_BAND_EGSM,#  900
                   consts.MM_NETWORK_BAND_DCS, # 1800

                   consts.MM_NETWORK_BAND_U2100])


class HuaweiE17X(HuaweiWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Huawei's E17X"""
    name = "Huawei E17X"
    version = "0.1"
    author = u"Jaime Soriano"
    custom = HuaweiE17XCustomizer()

    __remote_name__ = "E17X"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1003],
    }
