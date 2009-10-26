# -*- coding: utf-8 -*-
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
"""Some routines to gather information at runtime"""
from os.path import exists

import dbus

import wader.common.consts as consts

def nm07_present():
    return True
    obj = dbus.SystemBus().get_object(consts.NM_SERVICE, consts.NM_OBJPATH)
    try:
        devices = obj.GetDevices()
        return True
    except dbus.DBusException:
        return False

def nm08_present():
    return True
    obj = dbus.SystemBus().get_object(consts.NM_SERVICE, consts.NM_OBJPATH)
    try:
        devices = obj.GetDevices()
        if len(devices):
            return 'NetworkManager' in devices[0]
        else:
            return False
    except dbus.DBusException:
        return False


resolvconf_present = exists('/sbin/resolvconf')
