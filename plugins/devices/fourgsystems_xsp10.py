# -*- coding: utf-8 -*-
# Copyright (C) 2012  Sphere Systems Ltd
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

from wader.common import consts

from core.hardware.longcheer import (LongcheerWCDMACustomizer,
                                     LongcheerWCDMADevicePlugin,
                                     LongcheerWCDMAWrapper)


class FourGSystemsXSP10Wrapper(LongcheerWCDMAWrapper):

    def find_contacts(self, pattern):
        """Returns a list of `Contact` whose name matches pattern"""

        # AT+CPBF function is broken, it seems to cause a modem firmware crash
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                        [c for c in contacts
                            if c.name.lower().startswith(pattern.lower())])
        return d


class FourGSystemsXSP10Customizer(LongcheerWCDMACustomizer):
    wrapper_klass = FourGSystemsXSP10Wrapper


class FourGSystemsXSP10(LongcheerWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for 4GSystems' XSStick P10"""
    name = "XSStick P10"
    version = "0.1"
    author = u"Andrew Bird"
    custom = FourGSystemsXSP10Customizer()

    __remote_name__ = "XS Stick P10+"

    __properties__ = {
        'ID_VENDOR_ID': [0x1c9e],
        'ID_MODEL_ID': [0x9603],
    }

    conntype = consts.WADER_CONNTYPE_USB

fourgsystemsxsp10 = FourGSystemsXSP10()
