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

from wader.common.consts import APP_NAME

import sys
sys.path.insert(0, '/usr/share/wader-core')

from core.startup import (create_skeleton_and_do_initial_setup,
                          get_wader_application)
# it will just return if its not necessary
create_skeleton_and_do_initial_setup()

# check if we have an OSPlugin for this OS/Distro
from core.oal import get_os_object
if get_os_object() is None:
    message = 'OS/Distro not registered'
    details = """
The OS/Distro under which you are running %s
is not registered in the OS database. Check the documentation for what
you can do in order to support your OS/Distro
""" % APP_NAME
    raise SystemExit("%s\n%s" % (message, details))

application = get_wader_application()
