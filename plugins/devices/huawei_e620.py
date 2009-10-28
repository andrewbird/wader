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

import re

from wader.common.hardware.huawei import (HuaweiWCDMADevicePlugin,
                                          HuaweiWCDMACustomizer)
from wader.common.command import build_cmd_dict

E620_CMD_DICT = HuaweiWCDMACustomizer.cmd_dict.copy()
E620_CMD_DICT['get_roaming_ids'] = build_cmd_dict(re.compile(
                                    """
                                    \r\n
                                    \+CPOL:\s(?P<index>\d+),"(?P<netid>\d+)"
                                    """, re.VERBOSE))


class HuaweiE620Customizer(HuaweiWCDMACustomizer):
    cmd_dict = E620_CMD_DICT


class HuaweiE620(HuaweiWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Huawei's E620"""
    name = "Huawei E620"
    version = "0.1"
    author = u"Pablo Martí"
    custom = HuaweiE620Customizer()

    __remote_name__ = "E620"

    __properties__ = {
        'usb_device.vendor_id': [0x12d1],
        'usb_device.product_id': [0x1001],
    }
