# -*- coding: utf-8 -*-
# Copyright (C) 2011  Vodafone España, S.A.
# Copyright (C) 2010  Warp Networks, S.L.
# Author:  Andrew Bird
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

from wader.common.backends import BACKEND_LIST

from core.backends.nm import nm_backend
from core.backends.plain import plain_backend

__backend = None


def get_backend():
    global __backend
    if __backend is not None:
        return __backend

    for name in BACKEND_LIST:
        backend = globals()[name]
        if backend.should_be_used():
            __backend = backend
            return __backend
