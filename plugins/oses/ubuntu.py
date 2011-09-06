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
"""Ubuntu OSPlugin"""

import re
from os.path import exists

from twisted.internet.utils import getProcessValue

from wader.common.oses.linux import LinuxPlugin
from wader.common.utils import get_file_data

VERS_REGEX = '^DISTRIB_RELEASE=\s*(?P<version>\d+\.\d+)\s*$'

class UbuntuBasedDistro(LinuxPlugin):
    """A plugin to be used on Ubuntu systems"""

    def is_valid(self):
        if not exists('/etc/lsb-release'):
            return False

        lsb = get_file_data('/etc/lsb-release')
        if 'Ubuntu' in lsb:
            match = re.search(VERS_REGEX, lsb,  re.MULTILINE)
            if match:
                vers = match.group('version').replace('.','')
                try:
                    self.version = int(vers)
                except ValueError:
                    pass

            return True

        return False

    def update_dns_cache(self):
        if exists("/usr/sbin/nscd"):
            return getProcessValue("/usr/sbin/nscd", ["-i", "hosts"])

    def get_additional_wvdial_ppp_options(self):
        options = "replacedefaultroute\n"
        #if hasattr(self, 'version'):
        #    if self.version <= 904:
        #        options += "usepeerdns\n"
        return options

ubuntu = UbuntuBasedDistro()
