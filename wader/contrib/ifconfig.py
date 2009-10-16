# -*- coding: utf-8 -*-
# Author: MonkeeSage at gmail.com
# Modified by Pablo Martí   13/04/2007
#   added support for SIOCGIFDSTADDR
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
Python ifconfig

This is not portable across different OSes
"""

# seen at [0] with no license, added support for SIOCGIFDSTADDR. I'm
# releasing it under the GPL
# http://mail.python.org/pipermail/python-list/2007-March/429176.html

import fcntl
import platform
import socket
import struct

def _ifinfo(sock, addr, ifname):
    iface = struct.pack('256s', ifname[:15])
    info = fcntl.ioctl(sock.fileno(), addr, iface)
    if addr == 0x8927:
        hwaddr = []
        for char in info[18:24]:
            hwaddr.append(hex(ord(char))[2:])
        return ':'.join(hwaddr)
    else:
        return socket.inet_ntoa(info[20:24])

def ifconfig(ifname):
    ifreq = {'ifname': ifname}
    infos = {}
    osys = platform.system()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if osys == 'Linux':
        # offsets defined in /usr/include/linux/sockios.h on linux 2.6
        infos['addr'] = 0x8915    # SIOCGIFADDR
        infos['brdaddr'] = 0x8919 # SIOCGIFBRDADDR
        infos['hwaddr'] = 0x8927  # SIOCSIFHWADDR
        infos['netmask'] = 0x891b # SIOCGIFNETMASK
        infos['raddr'] = 0x8917   # SIOCGIFDSTADDR
    elif 'BSD' in osys: # ???
        infos['addr'] = 0x8915
        infos['brdaddr'] = 0x8919
        infos['hwaddr'] = 0x8927
        infos['netmask'] = 0x891b
        infos['raddr'] = 0x8917
    try:
        for k, v in infos.items():
            ifreq[k] = _ifinfo(sock, v, ifname)
    except:
        pass

    sock.close()
    return ifreq
