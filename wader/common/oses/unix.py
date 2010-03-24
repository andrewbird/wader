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
"""OSPlugin for Unix-based OSes"""

from wader.common.plugin import OSPlugin
from wader.common.resolvconf import NamedManager
from wader.common.utils import get_file_data


class UnixPlugin(OSPlugin):
    """Plugin for Unix"""

    def __init__(self):
        super(UnixPlugin, self).__init__()
        self.named_manager = NamedManager()

    def add_dns_info(self, dns, iface=None):
        """See :meth:`wader.common.interfaces.IOSPlugin.add_dns_info`"""
        self.named_manager.add_dns_info(dns)
        self.update_dns_cache()

    def delete_dns_info(self, dns, iface=None):
        """See :meth:`wader.common.interfaces.IOSPlugin.delete_dns_info`"""
        self.named_manager.delete_dns_info(dns)
        self.update_dns_cache()

    def is_valid(self):
        # DO NOT modify this unless you know what you are doing. This plugin
        # is the parent class of LinuxPlugin/OSXPlugin/*BSDPlugin/etc. This
        # is not a final implementation as there's no such thing as a Unix OS.
        return False

    def get_iface_stats(self, iface):
        raise NotImplementedError()

    def get_timezone(self):
        return get_file_data('/etc/timezone').replace('\n', '')

    def update_dns_cache(self):
        raise NotImplementedError()
