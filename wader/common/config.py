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
"""
GConf-powered config

This module lives in wader.common so it can be used from applications
that depend on wader-core. Do not try to use it in the core as it will
fail.
"""

from os.path import join

from wader.common.consts import APP_SLUG_NAME
from wader.common._gconf import GConfHelper

CONF_PATH = '/apps/%s' % APP_SLUG_NAME

DEFAULT_KEYS = ['plugins', 'test']


class WaderConfig(GConfHelper):
    """I manage Wader config"""

    def __init__(self, keys=DEFAULT_KEYS, base_path=CONF_PATH):
        # despite the fact that having default mutable types as
        # argument in python, keys will never be modified, only
        # read, so we are safe using it this way.
        super(WaderConfig, self).__init__()
        self.keys = keys
        self.base_path = base_path

    def get(self, section, option, default=None):
        """
        Returns the value at ``section/option``

        Will return ``default`` if undefined
        """
        value = self.client.get(join(self.base_path, section, option))
        if not value:
            return (default if default is not None else "")

        return self.get_value(value)

    def set(self, section, option, value):
        """Sets ``value`` at ``section/option``"""
        path = join(self.base_path, section, option)
        self.set_value(path, value)


config = WaderConfig()
