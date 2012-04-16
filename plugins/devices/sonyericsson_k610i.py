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

from wader.common.consts import WADER_CONNTYPE_USB
from core.hardware.sonyericsson import SonyEricssonCustomizer
from core.plugin import DevicePlugin
from core.middleware import WCDMAWrapper


class K610iWrapper(WCDMAWrapper):

    def set_charset(self, charset):
        if charset == 'UCS2':
            d = super(K610iWrapper, self).set_charset('IRA')
        else:
            d = super(K610iWrapper, self).set_charset(charset)

        d.addCallback(lambda ignord: self.device.sim.set_charset(charset))
        return d


class SonyEricssonK610iCustomizer(SonyEricssonCustomizer):
    wrapper_klass = K610iWrapper


class SonyEricssonK610iUSB(DevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for Sony Ericsson k610i"""
    name = "Sony Ericsson K610i"
    version = "0.1"
    author = u"Jaime Soriano"
    custom = SonyEricssonK610iCustomizer()

    __remote_name__ = "AAD-3022041-BV"

    __properties__ = {
        'ID_VENDOR_ID': [0x0fce],
        'ID_MODEL_ID': [0xd046],
    }

    conntype = WADER_CONNTYPE_USB

sonyericsson_k610iUSB = SonyEricssonK610iUSB()
