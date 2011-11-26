# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
# Author:  Adam King - heavily based on Pablo Marti's U630 plugin
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

import serial

from core.hardware.novatel import (NovatelWCDMADevicePlugin,
                                           NovatelWCDMACustomizer,
                                           NovatelWrapper)


class NovatelU740Wrapper(NovatelWrapper):

    def find_contacts(self, pattern):
        """Returns a list of `Contact` whose name matches pattern"""
        # U740's AT+CPBF function is broken, it always raises a
        # CME ERROR: Not Found
        # We have no option but to use this little hack and emulate AT+CPBF
        # getting all contacts and returning those whose name match pattern
        # this will be slower than AT+CPBF with many contacts but at least
        # works
        d = self.list_contacts()
        d.addCallback(lambda contacts: [c for c in contacts
                         if c.name.lower().startswith(pattern.lower())])
        return d


class NovatelU740Customizer(NovatelWCDMACustomizer):
    wrapper_klass = NovatelU740Wrapper


class NovatelU740(NovatelWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Novatel's U740"""
    name = "Novatel U740"
    version = "0.1"
    author = "Adam King"
    custom = NovatelU740Customizer()

    __remote_name__ = "Merlin U740 (HW REV [0:33])"

    __properties__ = {
        'ID_VENDOR_ID': [0x1410],
        'ID_MODEL_ID': [0x1400, 0x1410],
    }

    def preprobe_init(self, ports, info):
        # Novatel secondary port needs to be flipped from DM to AT mode
        # before it will answer our AT queries. So the primary port
        # needs this string first or auto detection of ctrl port fails.
        # Note: Early models/firmware were DM only
        ser = serial.Serial(ports[0], timeout=1)
        ser.write('AT$NWDMAT=1\r\n')
        ser.close()

novatelu740 = NovatelU740()
