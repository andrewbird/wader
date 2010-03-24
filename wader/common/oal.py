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
"""
OS Abstraction Layer

OS provides an abstraction layer so path differences between OSes/distros
won't affect Wader
"""

_os_obj = None


def get_os_object():
    """
    Returns a ``OSPlugin`` instance corresponding to current OS used

    If the OS is unknown it will return None
    """
    global _os_obj
    if _os_obj is not None:
        return _os_obj

    from wader.common.plugin import PluginManager
    from wader.common.interfaces import IOSPlugin

    for osplugin in PluginManager.get_plugins(IOSPlugin):
        if osplugin.is_valid():
            osplugin.initialize()
            _os_obj = osplugin
            return _os_obj

    return None
