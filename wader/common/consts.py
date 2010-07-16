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
"""Wader global variables"""

from os import environ
from os.path import join

from dbus import UInt32

# app name
APP_NAME = 'Wader'
APP_SLUG_NAME = 'wader-core'
APP_VERSION = '0.5.4'

# DBus stuff
WADER_SERVICE = 'org.freedesktop.ModemManager'
WADER_OBJPATH = '/org/freedesktop/ModemManager'
WADER_INTFACE = 'org.freedesktop.ModemManager'

WADER_DIALUP_INTFACE = 'org.freedesktop.ModemManager.Dialup'
WADER_DIALUP_SERVICE = 'org.freedesktop.ModemManager.Dialup'
WADER_DIALUP_OBJECT = '/org/freedesktop/ModemManager/DialupManager'
WADER_DIALUP_BASE = '/org/freedesktop/ModemManager/Connections/%d'
WADER_PROFILES_SERVICE = 'org.freedesktop.ModemManager.Profiles'
WADER_PROFILES_OBJPATH = '/org/freedesktop/ModemManager/Profiles'
WADER_PROFILES_INTFACE = WADER_PROFILES_SERVICE
WADER_KEYRING_SERVICE = 'org.freedesktop.ModemManager.Keyring'
WADER_KEYRING_OBJPATH = '/org/freedesktop/ModemManager/Keyring'
WADER_KEYRING_INTFACE = WADER_KEYRING_SERVICE

MDM_INTFACE = 'org.freedesktop.ModemManager.Modem'
SPL_INTFACE = 'org.freedesktop.ModemManager.Modem.Simple'
SMS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Sms'
CTS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Contacts'
NET_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Network'
USD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Ussd'
CRD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Card'
HSO_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Hso'

STATUS_IDLE, STATUS_HOME, STATUS_SEARCHING = 0, 1, 2
STATUS_DENIED, STATUS_UNKNOWN, STATUS_ROAMING = 3, 4, 5

DEV_DISABLED, DEV_AUTHENTICATED, DEV_ENABLED, DEV_CONNECTED = 0, 1, 2, 3

# Used by both w.c.h.option and w.c.h.icera
HSO_NO_AUTH, HSO_PAP_AUTH, HSO_CHAP_AUTH = 0, 1, 2

MM_MODEM_TYPE = {
    UInt32(1): 'GSM',
    UInt32(2): 'CDMA',
}

MM_MODEM_TYPE_REV = dict(GSM=UInt32(1), CDMA=UInt32(2))

MM_IP_METHOD_PPP = UInt32(0)
MM_IP_METHOD_STATIC = UInt32(1)
MM_IP_METHOD_DHCP = UInt32(2)

MM_GSM_ACCESS_TECH_UNKNOWN = 0
MM_GSM_ACCESS_TECH_GSM = 1
MM_GSM_ACCESS_TECH_GSM_COMPAT = 2
MM_GSM_ACCESS_TECH_GPRS = 3
MM_GSM_ACCESS_TECH_EDGE = 4
MM_GSM_ACCESS_TECH_UMTS = 5
MM_GSM_ACCESS_TECH_HSDPA = 6
MM_GSM_ACCESS_TECH_HSUPA = 7
MM_GSM_ACCESS_TECH_HSPA = 8

MM_GSM_ACCESS_TECHNOLOGIES = [
    MM_GSM_ACCESS_TECH_UNKNOWN,
    MM_GSM_ACCESS_TECH_GSM,
    MM_GSM_ACCESS_TECH_GSM_COMPAT,
    MM_GSM_ACCESS_TECH_GPRS,
    MM_GSM_ACCESS_TECH_EDGE,
    MM_GSM_ACCESS_TECH_UMTS,
    MM_GSM_ACCESS_TECH_HSDPA,
    MM_GSM_ACCESS_TECH_HSUPA,
    MM_GSM_ACCESS_TECH_HSPA]

# MM_NETWORK_MODE_* is deprecated
# it will probably go away in NM 0.9/1.0
MM_NETWORK_MODE_UNKNOWN = 0x00000000
MM_NETWORK_MODE_ANY = 0x00000001
MM_NETWORK_MODE_GPRS = 0x00000002
MM_NETWORK_MODE_EDGE = 0x00000004
MM_NETWORK_MODE_UMTS = 0x00000008
MM_NETWORK_MODE_HSDPA = 0x00000010
MM_NETWORK_MODE_2G_PREFERRED = 0x00000020
MM_NETWORK_MODE_3G_PREFERRED = 0x00000040
MM_NETWORK_MODE_2G_ONLY = 0x00000080
MM_NETWORK_MODE_3G_ONLY = 0x00000100
MM_NETWORK_MODE_HSUPA = 0x00000200
MM_NETWORK_MODE_HSPA = 0x00000400

MM_NETWORK_MODE_LAST = MM_NETWORK_MODE_HSPA

MM_NETWORK_MODES = [
    MM_NETWORK_MODE_GPRS,
    MM_NETWORK_MODE_EDGE,
    MM_NETWORK_MODE_UMTS,
    MM_NETWORK_MODE_HSDPA,
    MM_NETWORK_MODE_2G_PREFERRED,
    MM_NETWORK_MODE_3G_PREFERRED,
    MM_NETWORK_MODE_2G_ONLY,
    MM_NETWORK_MODE_3G_ONLY,
    MM_NETWORK_MODE_HSUPA,
    MM_NETWORK_MODE_HSPA]

MM_ALLOWED_MODE_ANY = 0
MM_ALLOWED_MODE_2G_PREFERRED = 1
MM_ALLOWED_MODE_3G_PREFERRED = 2
MM_ALLOWED_MODE_2G_ONLY = 3
MM_ALLOWED_MODE_3G_ONLY = 4

MM_ALLOWED_MODES = [
    MM_ALLOWED_MODE_ANY,
    MM_ALLOWED_MODE_2G_PREFERRED,
    MM_ALLOWED_MODE_3G_PREFERRED,
    MM_ALLOWED_MODE_2G_ONLY,
    MM_ALLOWED_MODE_3G_ONLY]

MM_NETWORK_BAND_UNKNOWN = 0x0   # Unknown or invalid band
MM_NETWORK_BAND_ANY = 0x1       # ANY
MM_NETWORK_BAND_EGSM = 0x2      # 900 MHz
MM_NETWORK_BAND_DCS = 0x4       # 1800 MHz
MM_NETWORK_BAND_PCS = 0x8       # 1900 MHz
MM_NETWORK_BAND_G850 = 0x10     # 850 MHz
MM_NETWORK_BAND_U2100 = 0x20    # WCDMA 2100 MHz
MM_NETWORK_BAND_U1700 = 0x40    # WCDMA 3GPP UMTS1800 MHz
MM_NETWORK_BAND_17IV = 0x80     # WCDMA 3GPP AWS 1700/2100 MHz
MM_NETWORK_BAND_U800 = 0x100    # WCDMA 3GPP UMTS800 MHz
MM_NETWORK_BAND_U850 = 0x200    # WCDMA 3GPP UMTS850 MHz
MM_NETWORK_BAND_U900 = 0x400    # WCDMA 3GPP UMTS900 MHz
MM_NETWORK_BAND_U17IX = 0x800   # WCDMA 3GPP UMTS MHz
MM_NETWORK_BAND_U1900 = 0x1000  # WCDMA 3GPP UMTS MHz

MM_NETWORK_BAND_LAST = MM_NETWORK_BAND_U1900

MM_NETWORK_BANDS = [
    MM_NETWORK_BAND_EGSM,
    MM_NETWORK_BAND_DCS,
    MM_NETWORK_BAND_PCS,
    MM_NETWORK_BAND_G850,
    MM_NETWORK_BAND_U2100,
    MM_NETWORK_BAND_U1700,
    MM_NETWORK_BAND_17IV,
    MM_NETWORK_BAND_U800,
    MM_NETWORK_BAND_U850,
    MM_NETWORK_BAND_U900,
    MM_NETWORK_BAND_U17IX,
    MM_NETWORK_BAND_U1900]

MM_IP_METHOD_PPP = UInt32(0)
MM_IP_METHOD_STATIC = UInt32(1)
MM_IP_METHOD_DHCP = UInt32(2)

MM_SYSTEM_SETTINGS_PATH = '/org/freedesktop/ModemManager/Settings'

# necessary for relocatable bundling on OSX
BASE_DIR = environ.get('WADER_PREFIX', '/')

DATA_DIR = join(BASE_DIR, 'usr', 'share', APP_SLUG_NAME)
WADER_DOC = join(BASE_DIR, 'usr', 'share', 'doc', APP_SLUG_NAME, 'guide')

# paths
RESOURCES_DIR = join(DATA_DIR, 'resources')
TEMPLATES_DIR = join(RESOURCES_DIR, 'config')
EXTRA_DIR = join(RESOURCES_DIR, 'extra')

# databases
MBPI = '/usr/share/mobile-broadband-provider-info/serviceproviders.xml'
NETWORKS_DB = join(DATA_DIR, 'networks.db')
USAGE_DB = join(DATA_DIR, 'usage.db')

# plugins consts
PLUGINS_DIR = join(DATA_DIR, 'plugins')
PLUGINS_DIR = [PLUGINS_DIR,
               join(PLUGINS_DIR, 'oses'),
               join(PLUGINS_DIR, 'contacts'),
               join(PLUGINS_DIR, 'devices')]

PID_PATH = join(BASE_DIR, 'var', 'run', 'wader.pid')
LOG_PATH = join(BASE_DIR, 'var', 'log', 'wader.log')
