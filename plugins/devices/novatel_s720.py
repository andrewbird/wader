# -*- coding: utf-8 -*-
# Copyright (C) 2008 Warp Networks S.L.
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

# Plugin temporally disabled while we sort out the CDMA part

from wader.common.consts import WADER_CONNTYPE_PCMCIA


class NovatelS720(object):
    """:class:`~core.plugin.DevicePlugin` for Novatel S720"""
    name = "Novatel S720"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = "MERLIN S720"

    __properties__ = {
        'ID_VENDOR_ID': [0x1410],
        'ID_MODEL_ID': [0x1130],
    }

    conntype = WADER_CONNTYPE_PCMCIA
