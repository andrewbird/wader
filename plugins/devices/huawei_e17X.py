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

from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWrapper)

class HuaweiE17XWrapper(HuaweiWrapper):
    def get_phonebook_size(self):
        # the E170 that we have around keeps raising GenericErrors whenever
        # is asked for its size, we'll have to cheat till we have time
        # to find a workaround
        d = super(HuaweiE17XWrapper, self).get_phonebook_size()
        d.addErrback(lambda failure: defer.succeed(250))
        return d

    def get_contacts(self):
        # we return a list with all the contacts that match '', i.e. all
        return self.find_contacts('')


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

