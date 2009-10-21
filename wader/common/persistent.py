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
"""Data persistence for Wader"""

from sqlite3 import dbapi2 as sqlite

import wader.common.consts as consts

SCHEMA = """
create table network_info(
    id integer primary key autoincrement,
    name text,
    country text);

create table apn(
    id integer primary key autoincrement,
    apn text not null,
    username text,
    password text,
    dns1 text,
    dns2 text,
    type integer,
    network_id integer not null
        constraint fk_apn_network_id references network_info(id) on delete cascade);

create table message_information(
    id integer primary key autoincrement,
    smsc text,
    mmsc text,
    type integer,
    network_id integer not null
        constraint fk_mi_network_id references network_info(id) on delete cascade);

create table version (
    version integer default 1);

-- delete on cascade network_info -> apn
create trigger fkd_network_info_apn before delete on "network_info" when
    exists (select 1 from "apn" where old."id" == "network_id")
begin
  delete from "apn" where "network_id" = old."id";
end;

-- delete on cascade network_info -> nessage_information
create trigger fkd_network_info_message_information before delete on "network_info" when
    exists (select 1 from "message_information" where old."id" == "network_id")
begin
  delete from "message_information" where "network_id" = old."id";
end;

create trigger genfkey1_insert_referencing before insert on "apn" when
    new."network_id" is not null and not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;
create trigger genfkey1_update_referenced after
    update of id on "network_info" when
    exists (select 1 from "apn" where old."id" == "network_id")
begin
  select raise(abort, 'constraint failed');
end;
create trigger genfkey1_update_referencing before
    update of network_id on "apn" when
    new."network_id" is not null and
    not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;
create trigger genfkey2_insert_referencing before insert on "message_information" when
    new."network_id" is not null and not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;
create trigger genfkey2_update_referenced after
    update of id on "network_info" when
    exists (select 1 from "message_information" where old."id" == "network_id")
begin
  select raise(abort, 'constraint failed');
end;
create trigger genfkey2_update_referencing before
    update of network_id on "message_information" when
    new."network_id" is not null and
    not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;
"""

TYPE_CONTRACT, TYPE_PREPAID = 1, 2


class AccessPointName(object):
    """I represent an APN in the DB"""

    def __init__(self, apn, username, password, dns1, dns2, _type,
                 network=None, index=None):
        self.apn = apn
        self.username = username
        self.password = password
        self.dns1 = dns1
        self.dns2 = dns2
        self.type = _type
        self.network = network
        self.index = index

    def __repr__(self):
        return "<AccessPointName %d, %s>" % (self.index, self.apn)

    @classmethod
    def from_row(cls, row, network):
        return cls(row[1], row[2], row[3], row[4], row[5], row[6],
                   network.index, index=row[0])

    def to_row(self):
        """Returns a tuple representation ready to be inserted in DB"""
        return (self.index, self.apn, self.username, self.password, self.dns1,
                self.dns2, self.type, self.network.index)


class Network(object):
    """I represent a network in the DB"""

    def __init__(self, name, country, index=None):
        self.name = name
        self.country = country
        self.index = index

    def __repr__(self):
        return "<Network %d, %s>" % (self.index, self.name)

    @classmethod
    def from_row(cls, row):
        return cls(row[1], row[2], index=row[0])

    def to_row(self):
        """Returns a tuple representation ready to be inserted in DB"""
        return self.index, self.name, self.country


class MessageInformation(object):
    """I represent the message info associated with a network"""

    def __init__(self, smsc, mmsc, _type, network=None, index=None):
        self.smsc = smsc
        self.mmsc = mmsc
        self.type = _type
        self.network = network
        self.index = index

    def __repr__(self):
        return "<MessageInformation %d>" % self.index

    @classmethod
    def from_row(cls, row, network):
        return cls(row[1], row[2], row[3], network, index=row[0])

    def to_row(self):
        """Returns a tuple representation ready to be inserted in DB"""
        return self.index, self.smsc, self.mmsc, self.type, self.network.index


def populate_networks(network_list, path=consts.NETWORKS_DB):
    pass


def get_network_by_id(netid, path=consts.NETWORKS_DB):
    pass
