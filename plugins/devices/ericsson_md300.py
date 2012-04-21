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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.ericsson import (EricssonDevicePlugin,
                                            EricssonWrapper,
                                            EricssonCustomizer,
                                            ERICSSON_CONN_DICT)
from wader.common.utils import revert_dict


ERICSSON_CONN_DICT_REV = revert_dict(ERICSSON_CONN_DICT)


class EricssonMD300Wrapper(EricssonWrapper):

    def get_network_mode(self):

        def get_radio_status_cb(mode):
            if mode in ERICSSON_CONN_DICT_REV:
                return ERICSSON_CONN_DICT_REV[mode]

            raise KeyError("Unknown network mode %d" % mode)

        d = self.get_radio_status()
        d.addCallback(get_radio_status_cb)
        return d


class EricssonMD300Customizer(EricssonCustomizer):
    wrapper_klass = EricssonMD300Wrapper


class EricssonMD300(EricssonDevicePlugin):
    """:class:`~core.plugin.DBusDevicePlugin` for Ericsson's MD300"""
    name = "Ericsson MD300"
    version = "0.1"
    author = u"Andrew Bird"
    custom = EricssonMD300Customizer()

    __remote_name__ = "MD300"

    __properties__ = {
        'ID_VENDOR_ID': [0x0fce],
        'ID_MODEL_ID': [0xd0cf],
    }

    conntype = WADER_CONNTYPE_USB

ericssonMD300 = EricssonMD300()
