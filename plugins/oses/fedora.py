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
"""Fedora OSPlugin"""

from os.path import exists
import re

from wader.common.oses.linux import LinuxPlugin
from wader.common.utils import get_file_data

class FedoraBasedDistro(LinuxPlugin):
    """
    OSPlugin for Fedora-based distros
    """

    #XXX: Almost duplicated code with Suse plugin
    def get_timezone(self):
        timezone_re = re.compile('ZONE="(?P<tzname>[\w/]+)"')
        sysconf_clock_file = get_file_data('/etc/sysconfig/clock')
        search_dict = timezone_re.search(sysconf_clock_file).groupdict()
        return search_dict['tzname']

    def is_valid(self):
        paths = ['/etc/redhat-release', '/etc/fedora-release']
        return any(map(exists, paths))

fedora = FedoraBasedDistro()
