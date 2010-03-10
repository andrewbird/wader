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

from os.path import exists
import tempfile

from twisted.internet import reactor
from twisted.internet.utils import getProcessValue

from wader.common.oses.linux import LinuxPlugin
from wader.common.utils import save_file, get_file_data, create_dns_lock
from wader.common.consts import APP_NAME, WADER_DNS_LOCK


resolvconf_present = exists('/sbin/resolvconf')


dns_template = """
nameserver\t%s
nameserver\t%s
"""


class UbuntuBasedDistro(LinuxPlugin):
    """A plugin to be used on Ubuntu systems"""

    def add_dns_info(self, (dns1, dns2), iface=None):
        if not resolvconf_present:
            # resolvconf package is not present, we will resort to
            # using pppd's ip-{up,down}.d infrastructure. 95vmc-up
            # will handle this for us.
            create_dns_lock(dns1, dns2, WADER_DNS_LOCK)
        else:
            path = tempfile.mkstemp('resolv.conf', APP_NAME)[1]
            save_file(path, dns_template % (dns1, dns2))

            args = [iface, path]
            return getProcessValue('/usr/bin/wader-resolvconf-helper',
                                   args, reactor=reactor)

    def delete_dns_info(self, dnsinfo, iface=None):
        if not resolvconf_present:
            # 95vmc-down will handle this for us
            return

        args = ['-d', iface]
        return getProcessValue('/sbin/resolvconf', args, reactor=reactor)

    def is_valid(self):
        if not exists('/etc/lsb-release'):
            return False

        return 'Ubuntu' in get_file_data('/etc/lsb-release')

ubuntu = UbuntuBasedDistro()
