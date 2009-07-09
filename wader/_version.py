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

from wader.common.consts import APP_VERSION, APP_NAME
from twisted.python import versions

try:
    major, minor, rev = map(int, APP_VERSION.split('.'))
    version = versions.Version(APP_NAME, major, minor, rev)
except (TypeError, ValueError):
    major, minor, rev, micro = map(int, APP_VERSION.split('.'))
    version = versions.Version(APP_NAME, major, minor, rev, micro)
