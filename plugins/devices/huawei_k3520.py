# -*- coding: utf-8 -*-
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

from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWrapper, HuaweiWCDMACustomizer)


class HuaweiK3520Wrapper(HuaweiWrapper):
    def get_contacts(self):
        def get_contacts_cb(contacts):
            d = self.set_charset("UCS2")
            d.addCallback(lambda _: contacts)
            return d

        d = self.set_charset("IRA")
        d.addCallback(lambda ign:
                super(HuaweiK3520Wrapper, self).get_contacts())
        return d

    def find_contacts(self, pattern):
        d = self.get_contacts()
        d.addCallback(lambda contacts:
                        [c for c in contacts if c.name.startswith(pattern)])
        return d


class HuaweiK3520Customizer(HuaweiWCDMACustomizer):
    wrapper_klass = HuaweiK3520Wrapper


class HuaweiK3520(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's K3520"""
    name = "Huawei K3520"
    version = "0.1"
    author = u"Pablo Martí"
    custom = HuaweiK3520Customizer()

    __remote_name__ = "K3520"

    __properties__ = {
        'usb_device.vendor_id': [0x12d1],
        'usb_device.product_id': [0x1001],
    }
