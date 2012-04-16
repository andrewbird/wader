# -*- coding: utf-8 -*-
# Copyright (C) 2009-2010  Vodafone España, S.A.
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
from wader.common.encoding import pack_ucs2_bytes
from core.command import ATCmd
from core.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer,
                                          HuaweiWCDMAWrapper)


class HuaweiB970Wrapper(HuaweiWCDMAWrapper):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMAWrapper` for the B970
    """

    def _add_contact(self, name, number, index):
        """
        Adds a contact to the SIM card
        """
        raw = 0
        try:     # are all ascii chars
            name.encode('ascii')
        except:  # write in TS31.101 type 80 raw format
            # B970 doesn't need the "FF" suffix
            # AT^CPBW=1,"28780808",129,"80534E4E3A",1
            name = '80%s' % pack_ucs2_bytes(name)
            raw = 1

        category = 145 if number.startswith('+') else 129
        args = (index, number, category, name, raw)
        cmd = ATCmd('AT^CPBW=%d,"%s",%d,"%s",%d' % args, name='add_contact')

        return self.queue_at_cmd(cmd)


class HuaweiB970Customizer(HuaweiWCDMACustomizer):
    """
    :class:`~core.hardware.huawei.HuaweiWCDMACustomizer` for the B970
    """
    wrapper_klass = HuaweiB970Wrapper


class HuaweiB970(HuaweiWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Huawei's B970"""
    name = "Huawei B970"
    version = "0.1"
    author = u"Andrew Bird"
    custom = HuaweiB970Customizer()

    __remote_name__ = "B970"

    __properties__ = {
        'ID_VENDOR_ID': [0x12d1],
        'ID_MODEL_ID': [0x1003],
    }

    conntype = WADER_CONNTYPE_USB
