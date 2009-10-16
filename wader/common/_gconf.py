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
"""GConf helper classes"""

import gconf


class GConfHelper(object):
    """I am the base class for gconf-backed conf system"""

    def __init__(self):
        self.client = gconf.client_get_default()

    def set_value(self, path, value):
        """Sets ``value`` at ``path``"""
        if isinstance(value, basestring):
            self.client.set_string(path, value)
        elif isinstance(value, bool):
            self.client.set_bool(path, value)
        elif isinstance(value, (int, long)):
            self.client.set_int(path, value)
        elif isinstance(value, float):
            self.client.set_float(path, value)
        elif isinstance(value, list):
            self.client.set_list(path, gconf.VALUE_INT, value)

    def get_value(self, value):
        """Gets the value of ``value``"""
        if value.type == gconf.VALUE_STRING:
            return value.get_string()
        elif value.type == gconf.VALUE_INT:
            return value.get_int()
        elif value.type == gconf.VALUE_FLOAT:
            return value.get_float()
        elif value.type == gconf.VALUE_BOOL:
            return value.get_bool()
        elif value.type == gconf.VALUE_LIST:
            _list = value.get_list()
            return [self.get_value(v) for v in _list]
        else:
            msg = "Unsupported type %s for %s"
            raise TypeError(msg % (type(value), value))
