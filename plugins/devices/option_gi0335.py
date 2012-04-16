# -*- coding: utf-8 -*-
# Copyright (C) 2010  Vodafone España, S.A.
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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.option import (OptionHSOWCDMADevicePlugin,
                                          OptionHSOWCDMACustomizer,
                                          OptionHSOWrapper)


class OptionGI0335Wrapper(OptionHSOWrapper):

    def find_contacts(self, pattern):
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                        [c for c in contacts
                           if c.name.lower().startswith(pattern.lower())])
        return d


class OptionGI0335Customizer(OptionHSOWCDMACustomizer):
    wrapper_klass = OptionGI0335Wrapper


class OptionGI0335(OptionHSOWCDMADevicePlugin):
    """:class:`core.plugin.DevicePlugin` for Options's GI0335"""
    name = "Option GI0335"
    version = "0.1"
    author = u"Andrew Bird"
    custom = OptionGI0335Customizer()

    __remote_name__ = "GlobeTrotter HSPA Modem"

    __properties__ = {
          'ID_VENDOR_ID': [0xaf0],
          'ID_MODEL_ID': [0x8300],
    }

    conntype = WADER_CONNTYPE_USB

option_gi0335 = OptionGI0335()
