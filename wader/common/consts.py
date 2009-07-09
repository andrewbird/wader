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

from os.path import join

from dbus import UInt32

from wader.common.utils import revert_dict

# app name
APP_NAME = 'Wader'
APP_SLUG_NAME = 'wader-core'
APP_VERSION = '0.3.6'

# DBus stuff
WADER_SERVICE = 'org.freedesktop.ModemManager'
WADER_OBJPATH = '/org/freedesktop/ModemManager'
WADER_INTFACE = 'org.freedesktop.ModemManager'
PROPS_INTFACE = 'org.freedesktop.DBus.Properties'

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
SMS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.SMS'
CTS_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Contacts'
NET_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Network'
CRD_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Card'
HSO_INTFACE = 'org.freedesktop.ModemManager.Modem.Gsm.Hso'

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_OBJPATH = '/org/freedesktop/NetworkManager'
NM_INTFACE = 'org.freedesktop.NetworkManager'
NM_GSM_INTFACE = NM_INTFACE + '.Device.Gsm'

NM_USER_SETTINGS = 'org.freedesktop.NetworkManagerUserSettings'
NM_SYSTEM_SETTINGS = 'org.freedesktop.NetworkManagerSettings'
NM_SYSTEM_SETTINGS_OBJ = '/org/freedesktop/NetworkManagerSettings'
NM_SYSTEM_SETTINGS_CONNECTION = NM_SYSTEM_SETTINGS + '.Connection'
NM_SYSTEM_SETTINGS_SECRETS = NM_SYSTEM_SETTINGS_CONNECTION + '.Secrets'

GCONF_PROFILES_BASE = '/system/networking/connections'

STATUS_IDLE, STATUS_HOME, STATUS_SEARCHING = 0, 1, 2
STATUS_DENIED, STATUS_UNKNOWN, STATUS_ROAMING = 3, 4, 5

NM_CONNECTED, NM_DISCONNECTED = 8, 3

NM_PASSWD = 'passwd' # NM_SETTINGS_GSM_PASSWORD

MM_MODEM_TYPE = {
    UInt32(1) : 'GSM',
    UInt32(2) : 'CDMA',
}

MM_IP_METHOD_PPP = UInt32(0)
MM_IP_METHOD_STATIC = UInt32(1)
MM_IP_METHOD_DHCP = UInt32(2)

MM_NETWORK_MODE_ANY          = 0
MM_NETWORK_MODE_GPRS         = 1
MM_NETWORK_MODE_EDGE         = 2
MM_NETWORK_MODE_UMTS         = 3
MM_NETWORK_MODE_HSDPA        = 4
MM_NETWORK_MODE_2G_PREFERRED = 5
MM_NETWORK_MODE_3G_PREFERRED = 6
MM_NETWORK_MODE_2G_ONLY      = 7
MM_NETWORK_MODE_3G_ONLY      = 8
MM_NETWORK_MODE_HSUPA        = 9
MM_NETWORK_MODE_HSPA         = 10

MM_NETWORK_MODE_LAST = MM_NETWORK_MODE_HSPA

MM_NETWORK_BAND_EGSM  = 1    # 900 MHz
MM_NETWORK_BAND_DCS   = 2    # 1800 MHz
MM_NETWORK_BAND_PCS   = 4    # 1900 MHz
MM_NETWORK_BAND_G850  = 8    #  850 MHz
MM_NETWORK_BAND_U2100 = 16   # WCDMA 2100 MHz               (Class I)
MM_NETWORK_BAND_U1700 = 32   # WCDMA 3GPP UMTS1800 MHz      (Class III)
MM_NETWORK_BAND_17IV  = 64   # WCDMA 3GPP AWS 1700/2100 MHz (Class IV)
MM_NETWORK_BAND_U800  = 128  # WCDMA 3GPP UMTS800 MHz       (Class VI)
MM_NETWORK_BAND_U850  = 256  # WCDMA 3GPP UMTS850 MHz       (Class V)
MM_NETWORK_BAND_U900  = 512  # WCDMA 3GPP UMTS900 MHz       (Class VIII)
MM_NETWORK_BAND_U17IX = 1024 # WCDMA 3GPP UMTS MHz          (Class IX)
MM_NETWORK_BAND_U1900 = 2048 # WCDMA 3GPP UMTS MHz          (Class IX)
MM_NETWORK_BAND_ANY   = 65535

MM_NETWORK_BAND_LAST = MM_NETWORK_BAND_U1900

MM_MODEM_TYPE_REV = revert_dict(MM_MODEM_TYPE)

MM_IP_METHOD_PPP = UInt32(0)
MM_IP_METHOD_STATIC = UInt32(1)
MM_IP_METHOD_DHCP = UInt32(2)

MM_SYSTEM_SETTINGS_PATH = '/org/freedesktop/ModemManager/Settings'

DATA_DIR = join('/usr', 'share', '%s' % APP_SLUG_NAME)
WADER_DOC = join('/usr', 'share', 'doc', '%s' % APP_SLUG_NAME, 'guide')

# paths
RESOURCES_DIR = join(DATA_DIR, 'resources')
TEMPLATES_DIR = join(RESOURCES_DIR, 'config')
EXTRA_DIR = join(RESOURCES_DIR, 'extra')

# network database
NETWORKS_DB = join(DATA_DIR, 'networks.db')

# TEMPLATES
WVTEMPLATE = join(TEMPLATES_DIR, 'wvdial.conf.tpl')

# plugins consts
PLUGINS_DIR = join(DATA_DIR, 'plugins')
PLUGINS_DIR = [PLUGINS_DIR, join(PLUGINS_DIR, 'oses'),
               join(PLUGINS_DIR, 'devices')]

# static dns stuff
WADER_DNS_LOCK = join('/tmp', 'wader-conn.lock')

# wader-core-ctl stuff
PID_PATH = '/var/run/wader.pid'
LOG_PATH = '/var/log/wader.log'
