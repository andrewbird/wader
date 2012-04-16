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

from wader.common.consts import WADER_CONNTYPE_PCMCIA
from core.hardware.option import (OptionWCDMADevicePlugin,
                                          OptionWCDMACustomizer,
                                          OptionWrapper)


class OptionEtnaWrapper(OptionWrapper):

    def get_roaming_ids(self):
        # FW 2.8.0Hd while panik if AT+CPOL is sent while in UCS2, we will
        # switch to IRA, perform the operation and switch back to UCS2
        self.set_charset("IRA")
        d = super(OptionEtnaWrapper, self).get_roaming_ids()

        def get_roaming_ids_cb(rids):
            d2 = self.set_charset("UCS2")
            d2.addCallback(lambda _: rids)
            return d2

        d.addCallback(get_roaming_ids_cb)
        return d

    def find_contacts(self, pattern):
        """Returns a list of `Contact` whose name matches pattern"""
        # ETNA's AT+CPBF function is broken, it always raises a
        # CME ERROR: Not Found (at least with the following firmware rev:
        # FW 2.8.0Hd (Date: Oct 11 2007, Time: 10:20:29))
        # we have no option but to use this little hack and emulate AT+CPBF
        # getting all contacts and returning those whose name match pattern
        # this will be slower than AT+CPBF with many contacts but at least
        # works
        d = self.list_contacts()
        d.addCallback(lambda contacts:
                        [c for c in contacts
                            if c.name.lower().startswith(pattern.lower())])
        return d


class OptionEtnaCustomizer(OptionWCDMACustomizer):
    wrapper_klass = OptionEtnaWrapper


class OptionEtna(OptionWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Options's Etna"""
    name = "Option Etna"
    version = "0.1"
    author = u"Pablo Martí"
    custom = OptionEtnaCustomizer()

    __remote_name__ = "GlobeTrotter HSUPA Modem"

    __properties__ = {
          'ID_VENDOR_ID': [0x0af0],
          'ID_MODEL_ID': [0x7001],
    }

    conntype = WADER_CONNTYPE_PCMCIA

optionetna = OptionEtna()
