# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
# Author: Andrew Bird
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

import wader.common.aterrors as E
import wader.common.consts as consts
from wader.common.command import build_cmd_dict, ATCmd
from wader.common.hardware.ericsson import (EricssonDevicePlugin,
                                            EricssonWrapper,
                                            EricssonCustomizer,
                                            ERINFO_2G_GPRS, ERINFO_2G_EGPRS,
                                            ERINFO_3G_UMTS, ERINFO_3G_HSDPA)


F3507G_CMD_DICT = EricssonCustomizer.cmd_dict.copy()
# *ERINFO: 0,0,2
F3507G_CMD_DICT['get_network_mode'] = build_cmd_dict(
                '\r\n\*ERINFO:\s(?P<mode>\d),(?P<gsm>\d),(?P<umts>\d)\r\n')


class EricssonF3507GWrapper(EricssonWrapper):

    def get_network_mode(self):

        def get_network_mode_cb(resp):
            gsm = int(resp[0].group('gsm'))
            umts = int(resp[0].group('umts'))

            if gsm == ERINFO_2G_GPRS:
                return consts.MM_NETWORK_MODE_GPRS
            elif gsm == ERINFO_2G_EGPRS:
                return consts.MM_NETWORK_MODE_EDGE
            elif umts == ERINFO_3G_UMTS:
                return consts.MM_NETWORK_MODE_UMTS
            elif umts == ERINFO_3G_HSDPA:
                return consts.MM_NETWORK_MODE_HSDPA

            raise E.GenericError("unknown network mode: %d, %d" % (gsm, umts))

        cmd = ATCmd('AT*ERINFO?', name='get_network_mode')
        d = self.queue_at_cmd(cmd)
        d.addCallback(get_network_mode_cb)
        return d


class EricssonF3507GCustomizer(EricssonCustomizer):
    cmd_dict = F3507G_CMD_DICT
    wrapper_klass = EricssonF3507GWrapper



class EricssonF3507G(EricssonDevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin} for Ericsson's F3507G"""
    name = "Ericsson F3507G"
    version = "0.1"
    author = u"Andrew Bird"
    custom = EricssonF3507GCustomizer()

    __remote_name__ = "F3507g"

    __properties__ = {
        'usb_device.vendor_id': [0x0bdb],
        'usb_device.product_id': [0x1900, 0x1902],
    }

ericssonF3507G = EricssonF3507G()
