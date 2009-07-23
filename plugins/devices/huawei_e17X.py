# -*- coding: utf-8 -*-
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
from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper)

class HuaweiE17XWrapper(HuaweiWCDMAWrapper):
    def get_phonebook_size(self):
        # the E170 that we have around keeps raising GenericErrors whenever
        # is asked for its size, we'll have to cheat till we have time
        # to find a workaround
        d = super(HuaweiE17XWrapper, self).get_phonebook_size()
        d.addErrback(lambda failure: defer.succeed(200))
        return d

    def get_contacts(self):
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
            max = 0
            for m in matches:
                i = int(m.group('id'))
                if i > max:
                    max = i
            return max

        def no_contacts_eb(failure):
            failure.trap(E.NotFound, E.GenericError)
            return 0

        def get_valid_contacts(max):
            if max == 0:
                return defer.succeed([])

            def results_cb(matches):
                return [self._hw_process_contact_match(m) for m in matches]

            return self.send_at('AT^CPBR=1,%d' % max, name='get_contacts',
                             callback=results_cb)

        d = self.send_at('AT+CPBF=""', name='find_contacts',
                           callback=get_max_index_cb)
        d.addErrback(no_contacts_eb)
        d.addCallback(get_valid_contacts)
        return d


class HuaweiE17XCustomizer(HuaweiWCDMACustomizer):
    wrapper_klass = HuaweiE17XWrapper


class HuaweiE17X(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's E17X"""
    name = "Huawei E17X"
    version = "0.1"
    author = u"Jaime Soriano"
    custom = HuaweiE17XCustomizer()

    __remote_name__ = "E17X"

    __properties__ = {
        'usb_device.vendor_id' : [0x12d1],
        'usb_device.product_id' : [0x1003],
    }

