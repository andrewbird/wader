# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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


from wader.common.hardware.novatel import NovatelWCDMADevicePlugin

class NovatelU630(NovatelWCDMADevicePlugin):
    """:class:`~wader.common.plugin.DevicePlugin` for Novatel's U630"""
    name = "Novatel U630"
    version = "0.1"
    author = u"Pablo Martí"

    __remote_name__ = "Merlin U630 (HW REV Rev 2)"

    __properties__ = {
        'pcmcia.manf_id': [0x00a4],
        'pcmcia.card_id': [0x0276],
    }

    # Unfortunately it is not possible to switch the Second port from DM
    # to AT mode on the x6xx models, so we have to run with only one port

novatelu630 = NovatelU630()
