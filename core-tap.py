# -*- coding: utf-8 -*-
# Copyright (C) 2006-2011  Vodafone España, S.A.
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
"""tap file for Wader"""

# Make sure the very first thing we do is to set the glib loop as default
import dbus
from dbus.mainloop.glib import DBusGMainLoop
gloop = DBusGMainLoop(set_as_default=True)

import locale
# i10n stuff
locale.setlocale(locale.LC_ALL, '')

import sys
sys.path.insert(0, '/usr/share/wader-core')

from core.startup import get_wader_application

application = get_wader_application()
