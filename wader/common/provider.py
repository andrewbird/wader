# -*- coding: utf-8 -*-
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
"""Data providers"""
from __future__ import with_statement

import datetime
import sqlite3
import os
import sys
from time import mktime
from calendar import timegm

from pytz import timezone, country_names
from xml.dom.minidom import parse

from wader.common.consts import EXTRA_DIR, MBPI, NETWORKS_DB
from wader.common.sms import Message as _Message
from wader.common.utils import (get_value_and_pop, get_tz_aware_now,
                                get_tz_aware_mtime)

if sqlite3.version_info >= (2, 4, 1):
    # Starting in 2.4.1, the str type is not accepted anymore, therefore,
    # we convert all str objects to Unicode
    sqlite3.register_adapter(str, lambda s: s.decode('utf-8'))

SMS_SCHEMA = """
create table message (
    id integer primary key autoincrement,
    date integer not null,
    number text not null,
    text text,
    flags integer,
    thread_id integer not null constraint fk_thread_id references thread(id) on delete cascade);

create table thread (
    id integer primary key autoincrement,
    date integer default 0,                 -- updated by trigger
    number text not null,                   -- specified in creation
    message_count integer default 0,        -- updated by trigger
    snippet text,                           -- updated by trigger
    read integer default 0,                 -- updated by trigger
    folder_id integer not null constraint fk_folder_id references folder(id) on delete cascade);

create table folder (
    id integer primary key autoincrement,
    name text not null);

create table version (
    version integer default 1);

create index message_flags_index on message(flags);
create index message_thread_index on message(thread_id, id);
create index thread_folder_index on thread(folder_id, id);

-- delete on cascade thread -> message
create trigger fkd_thread_message before delete on "thread"
    when exists (select 1 from "message" where old."id" == "thread_id")
begin
    delete from "message" where "thread_id" = old."id";
end;

-- delete on cascade folder -> thread
create trigger fkd_folder_thread before delete on "folder"
    when exists (select 1 from "thread" where old."id" == "folder_id")
begin
    delete from "thread" where "folder_id" = old."id";
end;

-- prevent insertion of messages with an invalid thread_id
create trigger fki_message_thread before insert on "message"
    when new."thread_id" is not null and not exists (select 1 from "thread" where new."thread_id" == "id")
begin
    select raise(abort, 'constraint fki_message_thread failed: thread_id does not exist in thread table');
end;

-- update snippet, message_count and date of thread upon message insertion
create trigger fki_update_thread_values after insert on "message"
    when new."thread_id" is not null and exists (select 1 from "thread" where new."thread_id" == "id")
begin
    update "thread"
    set
        snippet = substr(new."text", 0, 100),
        message_count = (select message_count from thread where id = new."thread_id") + 1,
        date = strftime('%s', 'now')
    where id = new."thread_id";
    update "thread"
    set
        read = (select read from thread where id = new."thread_id") + 1
    where id = new."thread_id" and msg_is_read(new."flags");
end;

create trigger fku_mark_message_read after update on "message"
    when not msg_is_read(old."flags") and msg_is_read(new."flags")
begin
    update "thread"
    set
        read = (select read from thread where id = new."thread_id") + 1
    where id = new."thread_id";
end;

create trigger fku_mark_message_unread after update on "message"
    when msg_is_read(old."flags") and not msg_is_read(new."flags")
begin
    update "thread"
    set
        read = (select read from thread where id = new."thread_id") - 1
    where id = new."thread_id";
end;

-- prevent thread.id updates when there are messages associated to it
create trigger fku_thread_message after update of id on "thread"
    when exists (select 1 from "message" where old."id" == "thread_id")
begin
    select raise(abort, 'constraint fku_thread_message failed: can not update thread.id as there are messages associated to it');
end;

-- prevent message.thread_id updates with non existing thread.id
create trigger fku_message_thread before update of thread_id on "message"
    when new."thread_id" is not null and not exists (select 1 from "thread" where new."thread_id" == "id")
begin
    select raise(abort, 'constraint fku_message_thread failed: can not update message.thread_id with non existing thread_id');
end;

create trigger fki_thread_folder before insert on "thread"
    when new."folder_id" is not null and not exists (select 1 from "folder" where new."folder_id" == "id")
begin
    select raise(abort, 'constraint fki_thread_folder failed: folder_id does not exist in folder table');
end;

create trigger fku_folder_thread after update of id on "folder"
    when exists (select 1 from "thread" where old."id" == "folder_id")
begin
    select raise(abort, 'constraint fku_folder_thread failed: can not update folder.id as there are threads associated to it');
end;

create trigger fku_thread_folder before update of folder_id on "thread"
    when new."folder_id" is not null and not exists (select 1 from "folder" where new."folder_id" == "id")
begin
    select raise(abort, 'constraint fku_thread_folder failed: can not update thread.folder_id as it does not exist');
end;

-- decrease thread.message_count after deleting a message
create trigger fkd_update_message_count after delete on "message"
    when old."thread_id" is not null
begin
    update "thread"
    set message_count = (select message_count from thread where id = old.thread_id) - 1
    where id = old."thread_id";
end;
"""

NETWORKS_SCHEMA = """
create table network_info(
    id text primary key,
    name text,
    country text);

create table apn(
    id integer primary key autoincrement,
    apn text not null,
    username text,
    password text,
    dns1 text,
    dns2 text,
    type text,
    auth text,
    smsc text,
    mmsc text,
    wap1 text,
    wap2 text,
    wap_apn text,
    wap_username text,
    wap_password text,
    network_id integer not null
        constraint fk_mi_network_id references network_info(id) on delete cascade);

create table sources_info (
    objs integer default 0,
    mbpi integer default 0);

create table version (
    version integer default 1);

-- delete on cascade network_info -> apn
create trigger fkd_network_info_apn before delete on "network_info"
    when exists (select 1 from "apn" where old."id" == "network_id")
begin
  delete from "apn" where "network_id" = old."id";
end;

-- prevent insert on apn with unknown network_id
create trigger fki_apns_with_unknown_network_id before insert on "apn"
    when new."network_id" is not null and not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;

-- prevent update of network_info_id if there are APNs associated to old id
create trigger fku_prevent_apn_network_info_network_id_bad_update after update of id on "network_info"
    when exists (select 1 from "apn" where old."id" == "network_id")
begin
  select raise(abort, 'constraint failed');
end;

-- prevent update of apn.network_id if it does not exists
create trigger fku_prevent_apn_network_id_bad_update before update of network_id on "apn"
    when new."network_id" is not null and not exists (select 1 from "network_info" where new."network_id" == "id")
begin
  select raise(abort, 'constraint failed');
end;
"""

USAGE_SCHEMA = """
create table usage(
    id integer primary key autoincrement,
    start_time datetime not null,
    end_time datetime not null,
    bytes_recv integer not null,
    bytes_sent integer not null,
    umts boolean);

create table version (
    version integer default 1);
"""

# constants
INBOX, OUTBOX, DRAFTS = 1, 2, 3
UNREAD, READ = 0x01, 0x02

# tmp log file location
BCM_STARTUP_FILE = "/tmp/bcm-core-provider.output"

# GSM spec
# 0 - Unread message that has been received
# 1 - Read message that has been received
# 2 - Unsent message that has been stored
# 3 - Sent message that has been stored
# 4 - Any message

TYPE_CONTRACT, TYPE_PREPAID = 'Contract', 'Prepaid'


# functions
def nick_debug(s):
    if 0:
        with open(BCM_STARTUP_FILE, 'w', 0) as f:
            f.write("%s\n" % s)


def message_read(flags):
    """
    Returns a bool indicating whether the message had been read or not
    """
    # second bit is the "was read" flag
    return (int(flags) & READ) >> 1


def adapt_datetime(_datetime):
    if _datetime.tzinfo is None:
        # Naive object - Force to UTC, previous behaviour was to use mktime to
        #                localize. We should raise an exception, but the problem
        #                is that if done in the adapter, the error seen is very
        #                obscure and I expect difficult to relate to the cause.
        return timegm(_datetime.timetuple())

    return timegm(_datetime.astimezone(timezone('UTC')).timetuple())


def convert_datetime(ts):
    return datetime.datetime.fromtimestamp(float(ts), timezone('UTC'))


sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)


def date_to_datetime(date):
    # takes a date which is in local time and returns a timezone aware datetime
    timestamp = mktime(date.timetuple())
    return datetime.datetime.fromtimestamp(timestamp, timezone('UTC'))


# common classes
class DBError(Exception):
    """Base class for DB related errors"""


class DBProvider(object):
    """Base class for the DB providers"""

    def __init__(self, path, schema, **kw):
        self.conn = sqlite3.connect(path, isolation_level=None, **kw)
        c = self.conn.cursor()
        try:
            c.executescript(schema)
        except sqlite3.OperationalError:
            # ignore error, the database already exists
            pass

    def close(self):
        """Closes the provider and frees resources"""
        self.conn.close()


# data usage
class UsageItem(object):
    """I represent data usage in the DB"""

    def __init__(self, index=None, bytes_recv=None, bytes_sent=None,
                 end_time=None, start_time=None, umts=None):
        self.index = index
        self.bytes_recv = bytes_recv
        self.bytes_sent = bytes_sent
        self.end_time = end_time
        self.start_time = start_time
        self.umts = umts

    def __repr__(self):
        args = (str(self.end_time - self.start_time), self.bytes_recv,
                self.bytes_sent)
        return "<UsageItem time: %s bytes_recv: %d  bytes_sent: %d>" % args

    def __eq__(self, other):
        if other.index is not None and self.index is not None:
            return self.index == other.index

        raise ValueError("Cannot compare myself with %s" % other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def total(self):
        return self.bytes_recv + self.bytes_sent

    def is_3g(self):
        return self.umts

    def is_gprs(self):
        return not self.umts

    @classmethod
    def from_row(cls, row):
        return cls(index=row[0], start_time=row[1], end_time=row[2],
                   bytes_recv=int(row[3]), bytes_sent=int(row[4]),
                   umts=bool(row[5]))


class UsageProvider(DBProvider):
    """DB usage provider"""

    def __init__(self, path):
        super(UsageProvider, self).__init__(path, USAGE_SCHEMA,
                                        detect_types=sqlite3.PARSE_DECLTYPES)

    def add_usage_item(self, start, end, bytes_recv, bytes_sent, umts):
        c = self.conn.cursor()
        args = (None, start, end, bytes_recv, bytes_sent, umts)
        c.execute("insert into usage(id, start_time, end_time, bytes_recv,"
                  "bytes_sent, umts) values (?,?,?,?,?,?)", args)

        return UsageItem(umts=umts, start_time=start, end_time=end,
                         bytes_recv=bytes_recv, bytes_sent=bytes_sent,
                         index=c.lastrowid)

    def delete_usage_item(self, item):
        c = self.conn.cursor()
        c.execute("delete from usage where id=?", (item.index,))

    def get_usage_for_day(self, day):
        """
        Returns all `UsageItem` for ``day``

        :type day: ``datetime.date``
        """
        c = self.conn.cursor()

        if not isinstance(day, datetime.date):
            raise ValueError("Don't know what to do with %s" % day)

        tomorrow = day + datetime.timedelta(days=1)
        args = (date_to_datetime(day), date_to_datetime(tomorrow))
        c.execute("select * from usage where start_time >= ? and end_time < ?",
                  args)

        return [UsageItem.from_row(row) for row in c.fetchall()]

    def get_usage_for_month(self, month):
        """
        Returns all ``UsageItem`` for ``month``

        :type month: ``datetime.date``
        """
        c = self.conn.cursor()

        if not isinstance(month, datetime.date):
            raise ValueError("Don't know what to do with %s" % month)

        first_current_month_day = month.replace(day=1)
        if month.month < 12:
            _month = month.month + 1
            _year = month.year
        else:
            _month = 1
            _year = month.year + 1

        first_next_month_day = month.replace(day=1, month=_month, year=_year)

        args = (date_to_datetime(first_current_month_day),
                date_to_datetime(first_next_month_day))
        c.execute("select * from usage where start_time >= ? and start_time < ?",
                  args)
        return [UsageItem.from_row(row) for row in c.fetchall()]

    def get_total_usage(self, month=None):
        c = self.conn.cursor()

        if month is None:
            sql = "select * from usage"
            c.execute(sql)
        else:
            if not isinstance(month, datetime.date):
                raise ValueError("Don't know what to do with %s" % month)

            sql = "select * from usage where start_time >= ?"
            c.execute(sql, (date_to_datetime(month),))

        return [UsageItem.from_row(row) for row in c.fetchall()]


# networks
class NetworkOperator(object):
    """I represent a network operator in the DB"""

    def __init__(self, netid=None, apn=None, username=None, password=None,
                 dns1=None, dns2=None, type=None, auth=None, smsc=None,
                 mmsc=None, country=None, name=None, wap_apn=None,
                 wap_username=None, wap_password=None, wap1=None, wap2=None):
        self.netid = netid
        self.apn = apn
        self.username = username
        self.password = password
        self.dns1 = dns1
        self.dns2 = dns2
        self.type = type
        self.auth = auth
        self.wap_apn = wap_apn
        self.wap_username = wap_username
        self.wap_password = wap_password
        self.wap1 = wap1
        self.wap2 = wap2
        self.smsc = smsc
        self.mmsc = mmsc
        self.country = country
        self.name = name

    def __repr__(self):
        args = (self.name.capitalize(), self.country.capitalize(),
                self.netid, str(self.type))
        if self.wap2:
            args += (self.wap2,)

        return "<NetworkOperator %s>" % repr(args)

    @classmethod
    def from_row(cls, row, netid):
        return cls(netid=[netid], name=row[0], country=row[1], apn=row[2],
                     username=row[3], password=row[4], dns1=row[5],
                     dns2=row[6], type=row[7], smsc=row[8], mmsc=row[9],
                     wap1=row[10], wap2=row[11], wap_apn=row[12],
                     wap_username=row[13], wap_password=row[14], auth=row[15])



class NetworkProvider(DBProvider):
    """DB network provider"""

    def __init__(self, path=NETWORKS_DB):
        super(NetworkProvider, self).__init__(path, NETWORKS_SCHEMA)

    def is_current(self):
        c = self.conn.cursor()
        try:
            c.execute("select * from sources_info")
            row = c.fetchone()
            objs_mtime = convert_datetime(row[0])
            mbpi_mtime = convert_datetime(row[1])

            objs = os.path.join(EXTRA_DIR, 'networks.py')
            if ((objs_mtime != get_tz_aware_mtime(objs)) or
                (mbpi_mtime != get_tz_aware_mtime(MBPI))):
                return False
        except (TypeError, sqlite3.OperationalError):
            # it does not exist
            return False

        return True

    def get_network_by_id(self, imsi):
        """
        Returns all the :class:`NetworkOperator` registered for ``imsi``

        :rtype: list
        """
        if not isinstance(imsi, basestring):
            raise TypeError("argument must be a string subclass")

        if len(imsi) < 14:
            raise ValueError("Pass the whole imsi")

        for n in [7, 6, 5]:
            result = self._get_network_by_id(imsi[:n])
            if result:
                return result

        return []

    def _get_network_by_id(self, netid):
        c = self.conn.cursor()
        c.execute("select n.name, n.country, a.apn, a.username,"
                  "a.password, a.dns1, a.dns2, a.type, a.smsc, "
                  "a.mmsc, a.wap1, a.wap2, a.wap_apn, "
                  "a.wap_username, a.wap_password, a.auth "
                  "from network_info n inner join apn a on "
                  "n.id = a.network_id where n.id=?", (netid,))

        ret = [NetworkOperator.from_row(row, netid) for row in c.fetchall()]
        return ret

    def populate_networks(self):
        """
        Populates the networks database using default methods (currently
        a list of network objects, and from the mobile-broadband-provider-info).
        It turns off autocommit during import for speed
        """
        nick_debug("provider.py - populate_networks")

        try:
            # only will succeed on development
            networks = __import__('resources/extra/networks')
        except ImportError:
            try:
                # this fails on feisty but not on gutsy
                networks = __import__(os.path.join(EXTRA_DIR, 'networks'))
            except ImportError:
                sys.path.insert(0, EXTRA_DIR)
                import networks

        def is_valid(item):
            return not item.startswith(("__", "Base", "NetworkOperator"))

        # turn off autocommit
        self.conn.isolation_level = 'DEFERRED'

        nick_debug("provider.py - populate_networks: "
                   "conn.isolation_level: %s" % self.conn.isolation_level)

        self.populate_networks_from_objs([getattr(networks, item)()
                for item in dir(networks) if is_valid(item)])

        self.populate_networks_from_mbpi()

        # update timestamps
        objs = os.path.join(EXTRA_DIR, 'networks.py')
        args = (get_tz_aware_mtime(objs), get_tz_aware_mtime(MBPI))
        self.conn.cursor().execute("insert into sources_info values (?,?)", args)

        self.conn.commit()
        self.conn.isolation_level = None

    def populate_networks_from_objs(self, networks):
        """
        Populate the network database with ``networks``

        :param networks: NetworkOperator instances
        :type networks: iter
        """

        nick_debug("provider.py - populate_networks_from_objs")

        c = self.conn.cursor()

        for network in networks:
            for netid in network.netid:
                # check if this network object exists in the database
                c.execute("select 1 from network_info where id=?", (netid,))
                try:
                    c.fetchone()[0]
                except TypeError:
                    # it does not exist
                    args = (netid, network.name, network.country)
                    c.execute("insert into network_info values (?,?,?)", args)

                # check if the APN info exists in the database
                args = (network.apn, network.username, network.password,
                        network.dns1, network.dns2, network.type,
                        network.smsc, network.mmsc, network.wap1, network.wap2,
                        network.wap_apn)
                c.execute("select id from apn where apn=? and username=? "
                          "and password=? and dns1=? and dns2=? "
                          "and type=? and smsc=? and mmsc=? "
                          "and wap1=? and wap2=? and wap_apn=?", args)
                try:
                    c.fetchone()[0]
                except TypeError:
                    # it does not exist
                    args = (None, network.apn, network.username,
                            network.password, network.dns1, network.dns2,
                            network.type, network.auth, network.smsc,
                            network.mmsc, network.wap1, network.wap2,
                            network.wap_apn, network.wap_username,
                            network.wap_password, netid)
                    c.execute("insert into apn values (?,?,?,?,?,?,?,?,?,"
                              "?,?,?,?,?,?,?)", args)

    def populate_networks_from_mbpi(self, xmlfile=MBPI):
        """
        Populate the network database with info from``xmlfile``

        :param xmlfile: the path to the mobile-broadband-provider-info xml file
        """
        nick_debug("provider.py - populate_networks_from_mdpi")
        nick_debug("provider.py - populate_networks_from_mdpi: xmlfile for  "
                   "mbpi is: %s" % repr(xmlfile))

        def getAttributeValue(element, name):
            if element is None or not hasattr(element, 'attributes'):
                return ''
            attr = element.attributes[name]
            if not attr:
                return ''
            return attr.value.strip()

        def getElementsByTagNameNoDescend(parent, name):
            ret = []
            for node in parent.childNodes:
                if node.nodeType == node.ELEMENT_NODE and \
                    (name == "*" or node.tagName == name):
                    ret.append(node)
            return ret

        def getValue(elementlist, index=0):
            if elementlist is None or index >= len(elementlist):
                return ''
            if not elementlist[index].firstChild:
                return ''
            return elementlist[index].firstChild.data.strip()

        root = parse(xmlfile)
        svcs = getElementsByTagNameNoDescend(root, "serviceproviders")[0]

        version = getAttributeValue(svcs, "format")
        if version != '2.0':
            raise(TypeError)

        c = self.conn.cursor()

        for gsm in svcs.getElementsByTagName("gsm"):

            provider = gsm.parentNode
            country = provider.parentNode

            countrycode = getAttributeValue(country, "code")
            if countrycode == '':
                continue
            elif countrycode == 'gb': # TZ DB is just plain wrong
                countryname = 'United Kingdom'
            else:
                countryname = country_names[countrycode]

            # we need to be more specific about path to 'provider/name'
            # as apn also has a subtag called 'name'
            tag = getElementsByTagNameNoDescend(provider, "name")
            provname = getValue(tag)

            for networkid in getElementsByTagNameNoDescend(gsm, "network-id"):
                mcc = getAttributeValue(networkid, "mcc")
                mnc = getAttributeValue(networkid, "mnc")
                netid = mcc + mnc

                # check if this network object exists in the database
                c.execute("select 1 from network_info where id=?", (netid,))
                try:
                    c.fetchone()[0]
                except TypeError:
                    # it does not exist
                    args = (netid, provname, countryname)
                    c.execute("insert into network_info values (?,?,?)", args)

                for apn in getElementsByTagNameNoDescend(gsm, "apn"):
                    apnname = getAttributeValue(apn, "value")
                    if apnname == '':
                        continue

                    tag = getElementsByTagNameNoDescend(apn, "name")
                    _type = getValue(tag)
                    if len(_type):
                        typename = u'MBPI - ' + _type
                    else:
                        typename = u'MBPI - ' + provname

                    tag = getElementsByTagNameNoDescend(apn, "username")
                    username = getValue(tag)

                    tag = getElementsByTagNameNoDescend(apn, "password")
                    password = getValue(tag)

                    tag = getElementsByTagNameNoDescend(apn, "dns")
                    dns1 = getValue(tag, 0)
                    dns2 = getValue(tag, 1)

                    # check if info exists in the database for this network,
                    # we are authorititive for VF Networks, and we don't want
                    # duplicates of the others either
                    args = (netid, apnname, username, password, dns1, dns2, typename)
                    c.execute("select id from apn where network_id=? and "
                              "("
                                   "(not type like 'MBPI%')"
                                   " or "
                                   "(apn=? and username=? and password=? and"
                                   " dns1=? and dns2=? and type=?)"
                              ")", args)
                    try:
                        c.fetchone()[0]
                    except TypeError:
                        # it does not exist
                        args = (None, apnname, username, password, dns1, dns2,
                                typename, None, None, None, None, None, None,
                                None, None, netid)
                        c.execute("insert into apn values (?,?,?,?,?,?,?,?,"
                                  "?,?,?,?,?,?,?,?)", args)


# SMS
class Folder(object):
    """I am a container for threads and messages"""

    def __init__(self, name, index=None):
        self.name = name
        self.index = index

    def __repr__(self):
        return "<Folder index: %d name: %s>" % (self.index, self.name)

    def __eq__(self, other):
        return self.index == other.index

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_row(cls, row):
        """Returns a :class:`Folder` out of ``row``"""
        return cls(row[1], row[0])

    def to_row(self):
        """Returns a tuple object ready to be inserted in the DB"""
        return (self.index, self.name)


inbox_folder = Folder("Inbox", 1)
outbox_folder = Folder("Outbox", 2)
drafts_folder = Folder("Drafts", 3)


class Message(_Message):
    """I am a :class:`_Message` that belongs to a thread and has flags"""

    def __init__(self, *args, **kw):
        self.flags = get_value_and_pop(kw, 'flags', READ)
        self.thread = get_value_and_pop(kw, 'thread')
        super(Message, self).__init__(*args, **kw)

    def __repr__(self):
        args = (self.index, self.thread.index)
        return "<Message index %d thread_id %d>" % args

    def to_row(self):
        """Returns a tuple ready to be added to the provider DB"""
        return (self.index, self.datetime, self.number,
                self.text, self.flags, self.thread.index)

    @classmethod
    def from_row(cls, row, thread=None):
        # XXX: calling converter manually as DB 'date' type is integer
        return cls(row[2], row[3], index=row[0], flags=row[4],
                   _datetime=convert_datetime(row[1]),
                   thread=thread)


class Thread(object):
    """I represent an SMS thread in the DB"""

    def __init__(self, _datetime, number, index=None, message_count=1,
                 snippet='', read=1, folder=None):
        super(Thread, self).__init__()
        self.datetime = _datetime
        self.number = number
        self.index = index
        self.message_count = message_count
        self.snippet = snippet
        self.read = read
        self.folder = folder

    def __repr__(self):
        return "<Thread %d>" % self.index

    def __eq__(self, other):
        return self.index == other.index

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def from_row(cls, row, folder=None):
        """Returns a :class:`Thread` out of ``row``"""
        # XXX: calling converter manually as DB 'date' type is integer
        return cls(convert_datetime(row[1]),
                   row[2], index=row[0],
                   message_count=row[3], snippet=row[4], read=row[5],
                   folder=folder)

    def to_row(self):
        """Returns a tuple ready to be inserted in the DB"""
        return (self.index, self.datetime, self.number,
                self.message_count, self.snippet, self.read, self.folder.index)


class SmsProvider(DBProvider):
    """DB Sms provider"""

    def __init__(self, path):
        super(SmsProvider, self).__init__(path, SMS_SCHEMA)
        self.conn.create_function('msg_is_read', 1, message_read)

    def add_folder(self, folder):
        """
        Adds ``folder`` to the DB and returns the object updated with index
        """
        c = self.conn.cursor()
        c.execute("insert into folder values (?, ?)", folder.to_row())
        folder.index = c.lastrowid
        return folder

    def add_thread(self, thread):
        """
        Adds ``thread`` to the DB and returns the object updated with index
        """
        c = self.conn.cursor()
        c.execute("insert into thread values (?, ?, ?, ?, ?, ?, ?)",
                  thread.to_row())
        thread.index = c.lastrowid
        return thread

    def add_sms(self, sms, folder=inbox_folder):
        """
        Adds ``sms`` to the DB and returns the object updated with index

        :param folder: Folder where this SMS will be added
        """
        c = self.conn.cursor()
        if sms.thread is None:
            # create a new thread for this sms
            thread = self.get_thread_by_number(sms.number, folder=folder)
            sms.thread = thread

        c.execute("insert into message values (?, ?, ?, ?, ?, ?)",
                  sms.to_row())
        sms.index = c.lastrowid
        return sms

    def delete_folder(self, folder):
        """Deletes ``folder`` from the DB"""
        # Folders 1, 2, 3 can not be deleted (Inbox, Outbox, Drafts)
        if folder.index <= 3:
            raise DBError("Folder %d can not be deleted" % folder.index)

        c = self.conn.cursor()
        c.execute("delete from folder where id=?", (folder.index,))

    def delete_sms(self, sms):
        """Deletes ``sms`` from the DB"""
        c = self.conn.cursor()
        c.execute("delete from message where id=?", (sms.index,))

    def delete_thread(self, thread):
        """Deletes ``thread`` from the DB"""
        c = self.conn.cursor()
        c.execute("delete from thread where id=?", (thread.index,))

    def _get_folder_by_id(self, index):
        """Returns the :class:`Folder` identified by ``index``"""
        c = self.conn.cursor()
        c.execute("select * from folder where id=?", (index,))
        try:
            return Folder.from_row(c.fetchone())
        except TypeError:
            raise DBError("Folder %d does not exist" % index)

    def _get_thread_by_id(self, index):
        """Returns the :class:`Thread` identified by ``index``"""
        c = self.conn.cursor()
        c.execute("select * from thread where id=?", (index,))
        try:
            row = c.fetchone()
            folder = self._get_folder_by_id(row[6])
            return Thread.from_row(row, folder=folder)
        except TypeError:
            raise DBError("Thread %d does not exist" % index)

    def get_thread_by_number(self, number, folder=inbox_folder):
        """
        Returns the :class:`Thread` that belongs to ``number`` under ``folder``

        :rtype: :class:`Thread`
        """
        c = self.conn.cursor()
        sql = "select * from thread where number like ? and folder_id=?"
        c.execute(sql, ("%%%s%%" % number, folder.index))
        if c.rowcount == 1:
            # there already exists a thread for this number under folder
            return Thread.from_row(c.fetchone())
        elif c.rowcount < 1:
            # create thread for this number
            thread = Thread(get_tz_aware_now(), number, folder=folder)
            return self.add_thread(thread)
        elif c.rowcount > 1:
            raise DBError("Too many threads associated to number %s" % number)

        raise DBError("No thread found for number %s" % number)

    def list_folders(self):
        """
        List all the :class:`Folder` objects in the DB

        :rtype: iter
        """
        c = self.conn.cursor()
        c.execute("select * from folder")
        return (Folder.from_row(row) for row in c.fetchall())

    def list_from_folder(self, folder):
        """
        List all the :class:`Thread` objects that belong to ``folder``

        :rtype: iter
        """
        c = self.conn.cursor()
        sql = "select * from thread where folder_id=? order by date desc"
        c.execute(sql, (folder.index,))
        return (Thread.from_row(row, folder=folder) for row in c.fetchall())

    def list_from_thread(self, thread):
        """
        List all the :class:`Message` objects that belong to ``thread``

        :rtype: iter
        """
        c = self.conn.cursor()
        sql = "select * from message where thread_id=? order by date desc"
        c.execute(sql, (thread.index,))
        return (Message.from_row(row, thread=thread) for row in c.fetchall())

    def list_threads(self):
        """
        List all the :class:`Thread` objects in the DB

        :rtype: iter
        """
        c = self.conn.cursor()
        c.execute("select * from thread order by date desc")
        for row in c:
            folder = self._get_folder_by_id(row[6])
            yield Thread.from_row(row, folder=folder)

    def list_sms(self):
        """
        List all the :class:`Message` objects in the DB

        :rtype: iter
        """
        c = self.conn.cursor()
        c.execute("select * from message order by date desc")
        for row in c:
            thread = self._get_thread_by_id(row[5])
            yield Message.from_row(row, thread=thread)

    def move_to_folder(self, src, dst):
        """
        Moves ``src`` to ``dst``

        :return: The updated ``src`` object
        """
        if not isinstance(dst, Folder):
            raise TypeError("dst must be a Folder instance")

        if isinstance(src, Thread):
            return self._move_thread_to_folder(src, dst)
        elif isinstance(src, Message):
            return self._move_sms_to_folder(src, dst)
        else:
            raise TypeError("src must be a Thread or a Folder instance")

    def update_sms_flags(self, sms, flags):
        """Updates ``sms`` with ``flags``"""
        c = self.conn.cursor()
        c.execute("update message set flags=? where id=?", (flags, sms.index))
        sms.flags = flags
        return sms

    def _move_sms_to_folder(self, sms, folder):
        c = self.conn.cursor()
        sql = "select id from thread where number like ? and folder_id=?"
        c.execute(sql, ("%%%s%%" % sms.number, folder.index))
        if c.rowcount == 1:
            # there already exists a thread for that number in folder
            thread = self._get_thread_by_id(c.fetchone()[0])
            c.execute("update message set thread_id=? where id=?",
                      (thread.index, sms.index))
            sms.thread = thread
            return sms
        elif c.rowcount < 1:
            # create thread for this number
            thread = self.add_thread(
                    Thread(sms.datetime, sms.number, folder=folder))
            c.execute("update message set thread_id=? where id=?",
                      (thread.index, sms.index))
            sms.thread = thread
            return sms
        else:
            msg = "Too many threads associated to number %s"
            raise DBError(msg % sms.number)

    def _move_thread_to_folder(self, thread, folder):
        c = self.conn.cursor()
        c.execute("update thread set folder_id=? where id=?",
                  (folder.index, thread.index))
        thread.folder = folder
        return thread
