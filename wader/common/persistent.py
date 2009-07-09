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
"""Data persistance for Wader"""

from sqlite3 import dbapi2 as sqlite

import wader.common.consts as consts

class NetworkOperator(object):

    def __init__(self, netid, country, name, apn,
                 username, password, dns1, dns2):
        self.netid = netid
        self.country = country
        self.name = name
        self.apn = apn
        self.username = username
        self.password = password
        self.dns1 = dns1
        self.dns2 = dns2

    def __repr__(self):
        return "<NetworkOperator %s>" % self.netid

    def get_args(self):
        return (self.netid, self.country, self.name, self.apn,
                self.username, self.password, self.dns1, self.dns2)


def adapt_netoperator(oper):
    return "%s;%s;%s;%s;%s;%s;%s;%s" % oper.get_args()

def convert_netoperator(s):
    return NetworkOperator(*s.split(';'))

sqlite.register_adapter(NetworkOperator, adapt_netoperator)
sqlite.register_converter("netoperator", convert_netoperator)


def get_connection(path):
    return sqlite.connect(path, detect_types=sqlite.PARSE_DECLTYPES)

def populate_networks(network_list, path=consts.NETWORKS_DB):
    conn = get_connection(path)
    try:
        conn.execute("create table networks(n netoperator)")
    except sqlite.OperationalError:
        return

    cur = conn.cursor()
    # some network operators might come with multiple netids, this will
    # create a new one for each one of them
    for net in network_list:
        for netid in net.netid:
            oper = NetworkOperator(netid, net.country, net.name, net.apn,
                          net.username, net.password, net.dns1, net.dns2)
            cur.execute("insert into networks values (?)", (oper,))
    conn.commit()
    conn.close()

def get_network_by_id(netid, path=consts.NETWORKS_DB):
    netid = str(netid)
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("select n from networks")

    ret = None
    for oper in cur.fetchall():
        oper = oper[0]
        if oper.netid == netid:
            ret = oper
            break

    conn.close()
    return ret

