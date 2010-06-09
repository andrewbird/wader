# -*- coding: utf-8 -*-
# Copyright (C) 2006-2010  Vodafone España, S.A.
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA..
"""Misc utilities"""

from __future__ import with_statement
import os
import re
import socket
import struct

from dbus import Array, UInt32
from datetime import datetime
from pytz import timezone

from wader.common import consts


def convert_network_mode_to_access_technology(mode):
    trans_table = {
        consts.MM_NETWORK_MODE_GPRS: consts.MM_GSM_ACCESS_TECH_GPRS,
        consts.MM_NETWORK_MODE_EDGE: consts.MM_GSM_ACCESS_TECH_EDGE,
        consts.MM_NETWORK_MODE_UMTS: consts.MM_GSM_ACCESS_TECH_UMTS,
        consts.MM_NETWORK_MODE_HSDPA: consts.MM_GSM_ACCESS_TECH_HSDPA,
        consts.MM_NETWORK_MODE_HSUPA: consts.MM_GSM_ACCESS_TECH_HSUPA,
    }
    return trans_table.get(mode, consts.MM_GSM_ACCESS_TECH_UNKNOWN)


def convert_network_mode_to_allowed_mode(mode):
    trans_table = {
        consts.MM_NETWORK_MODE_ANY: consts.MM_ALLOWED_MODE_ANY,
        consts.MM_NETWORK_MODE_2G_PREFERRED: consts.MM_ALLOWED_MODE_2G_PREFERRED,
        consts.MM_NETWORK_MODE_3G_PREFERRED: consts.MM_ALLOWED_MODE_3G_PREFERRED,
        consts.MM_NETWORK_MODE_2G_ONLY: consts.MM_ALLOWED_MODE_2G_ONLY,
        consts.MM_NETWORK_MODE_3G_ONLY: consts.MM_ALLOWED_MODE_3G_ONLY,
    }
    return trans_table.get(mode)


def get_bands(bitwised_band):
    """
    Returns all the bitwised bands in ``bitwised_band``

    :rtype: list
    """
    return [band for band in consts.MM_NETWORK_BANDS if band & bitwised_band]


def get_network_modes(bitwised_mode):
    """
    Returns all the bitwised modes in ``bitwised_mode``

    :rtype: list
    """
    return [mode for mode in consts.MM_NETWORK_MODES if mode & bitwised_mode]


def get_allowed_modes(bitwised_mode):
    """
    Returns all the allowed_modes present in ``bitwised_mode``

    :rtype: list
    """
    ret = []
    for mode in get_network_modes(bitwised_mode):
        ret.append(convert_network_mode_to_allowed_mode(mode))

    return ret


def rssi_to_percentage(rssi):
    """
    Converts ``rssi`` to a percentage value

    :rtype: int
    """
    return (rssi * 100) / 31 if rssi < 32 else 0


def convert_ip_to_int(ip):
    """
    Converts ``ip`` to its integer representation

    :param ip: The IP to convert
    :type ip: str
    :rtype: int
    """
    return struct.unpack('I', socket.inet_pton(socket.AF_INET, ip))[0]


def convert_int_to_ip(i):
    """
    Converts ``i`` to its IP representation

    :param i: The integer to convert
    :rtype: str
    """
    # taken from ModemManager/test/test-mm.py
    ip = socket.ntohl(i)
    n1 = ip >> 24 & 0xFF
    n2 = ip >> 16 & 0xFF
    n3 = ip >> 8 & 0xFF
    n4 = ip & 0xFF
    return "%d.%d.%d.%d" % (n1, n2, n3, n4)


def convert_int_to_uint(i):
    """
    Converts ``i`` to unsigned int

    Python lacks the unsigned int type, but NetworkManager uses it
    all over the place, so we need to support it.

    :rtype: unsigned int
    """
    if i < 0:
        i += 0xffffffff + 1
    return i


def patch_list_signature(props, signature='au'):
    """
    Patches empty list signature in ``props`` with ``signature``

    :param props: Dictionary with connection options
    :type props: dict
    :param signature: The signature to use in empty lists
    :rtype: dict
    """
    for section in props:
        for key, val in props[section].iteritems():
            if val == []:
                if key in ['dns']:
                    props[section][key] = Array(val, signature='u')
                else:
                    props[section][key] = Array(val, signature=signature)
            elif key in ['addresses', 'dns', 'routes']:
                value = map(UInt32, map(convert_int_to_uint, val))
                props[section][key] = Array(value, signature='u')

    return props


def flatten_list(x):
    """Flattens ``x`` into a single list"""
    result = []
    for el in x:
        if hasattr(el, "__iter__") and not isinstance(el, basestring):
            result.extend(flatten_list(el))
        else:
            result.append(el)
    return result


def revert_dict(d):
    """
    Returns a reverted copy of ``d``

    :rtype: dict
    """
    ret = {}
    for k, v in d.iteritems():
        ret[v] = k

    return ret


def natsort(l):
    """Naturally sort list ``l`` in place"""
    # extracted from http://nedbatchelder.com/blog/200712.html#e20071211T054956
    convert = lambda text: int(text) if text.isdigit() else text
    l.sort(key=lambda key: map(convert, re.split('([0-9]+)', key)))


def get_file_data(path):
    """
    Returns the data of the file at ``path``

    :param path: The file path
    :rtype: str
    """
    with open(path) as f:
        return f.read()


def save_file(path, data):
    """
    Saves ``data`` in ``path``

    :param path: The file path
    :param data: The data to be saved
    """
    with open(path, 'w') as f:
        f.write(data)


def is_bogus_ip(ip):
    """
    Checks whether ``ip`` is a bogus IP

    :rtype: bool
    """
    return ip in ["10.11.12.13", "10.11.12.14"]


def get_value_and_pop(kw, name, d=None):
    """kw.pop[name] if name in kw, else d. d defaults to None"""
    return (kw.pop(name) if name in kw else d)


def get_tz_aware_now():
    return datetime.now(timezone('UTC'))


def get_tz_aware_mtime(f):
    """
    Gets the mtime on file ``f`` and returns a timezone aware datetime
    :rtype: datetime.datetime
    """
    dt = datetime.utcfromtimestamp(os.stat(f).st_mtime)
    return dt.replace(tzinfo=timezone('UTC'))
