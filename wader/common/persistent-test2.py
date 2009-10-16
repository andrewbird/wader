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

conn = sqlite.connect('sample.db')
curs = conn.cursor()

curs.execute("""CREATE TABLE network (
    networkID             INTEGER PRIMARY KEY AUTOINCREMENT,
    networkName           TEXT,
    country               TEXT) """)

curs.execute("""CREATE TABLE messages (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    smsc                       TEXT,
    mmsc                       TEXT,
    type                       TEXT,
    networkID                  INTEGER NOT NULL,
    FOREIGN KEY(networkID) REFERENCES network(nedworkID))""")
#thread_id integer not null constraint fk_thread_id references thread(id) on delete cascade);

curs.execute("""CREATE TABLE accessPointName (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    apn                        TEXT,
    userName               TEXT,
    passWord                TEXT,
    dns1                       TEXT,
    dns2                       TEXT,
    type                        TEXT,
    networkID               INTEGER NOT NULL CONSTRAINT fk_networkID REFERENCES network(nedworkID) ON DELETE CASCADE) """)

curs.execute("INSERT INTO people (first_name, last_name, date_of_birth) VALUES ('David', 'Bailey', '1938-1-2')")
curs.execute("INSERT INTO network (networkID, networkName, country) VALUES ('23415', 'Vodafone UK', 'United Kingdom')")
curs.execute("INSERT INTO messages (smsc , mmsc, type, networkID ) VALUES ('+44778501600523415', 'www.vodafone.com', 'contract', '23415')")
curs.execute("INSERT INTO messages (smsc , mmsc, type, networkID ) VALUES ('+44778501600523415', 'www.vodafone.com', 'prepaid', '23415')")
curs.execute("INSERT INTO accessPointName (apn , userName, passWord, dns1, dns2, type, networkID  ) VALUES ('internet', 'web', 'web', 'none', 'none', 'contract', '23415')")
curs.execute("INSERT INTO accessPointName (apn , userName, passWord, dns1, dns2, type, networkID  ) VALUES ('pp.internet', 'web', 'web', 'none', 'none', 'prepaid', '23415')")

conn.commit()

curs.execute("SELECT * FROM PEOPLE")
curs.fetchall()
