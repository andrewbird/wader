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

from wader.common.hardware.option import (OptionHSOWCDMADevicePlugin,
                                          OptionHSOWCDMACustomizer,
                                          OptionWrapper)

class OptionK3760Wrapper(OptionWrapper):

    def find_contacts(self, pattern):
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                        [c for c in contacts
                           if c.name.lower().startswith(pattern.lower())])
        return d


class OptionK3760Customizer(OptionHSOWCDMACustomizer):
    wrapper_klass = OptionK3760Wrapper


class OptionK3760(OptionHSOWCDMADevicePlugin):
    """:class:`wader.common.plugin.DevicePlugin` for Options's K3760"""
    name = "Option K3760"
    version = "0.1"
    author = u"Pablo Martí"
    custom = OptionK3760Customizer()

    dialer = 'hso'

    __remote_name__ = "GlobeTrotter HSUPA Modem"

    __properties__ = {
          'usb_device.vendor_id' : [0xaf0],
          'usb_device.product_id': [0x7501],
    }

option_k3760 = OptionK3760()

