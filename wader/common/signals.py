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
"""
Wader signals

Signals used internally in Wader. Some of them implement ModemManager API
"""

# SIGNALS
SIG_CALL = 'CallReceived'
SIG_CONNECTED = 'Connected'
SIG_CREG = 'CregReceived'
SIG_DEVICE_ADDED = 'DeviceAdded'
SIG_DEVICE_REMOVED = 'DeviceRemoved'
SIG_DIAL_STATS = 'DialStats'
SIG_DISCONNECTED = 'Disconnected'
SIG_INVALID_DNS = 'InvalidDNS'
SIG_NETWORK_MODE = 'NetworkMode'
SIG_REG_INFO = 'RegistrationInfo'
SIG_RSSI = 'SignalQuality'
SIG_SMS = 'SmsReceived'
SIG_MMS = 'MMSReceived'
SIG_SMS_COMP = 'Completed'
SIG_SMS_DELV = 'Delivered'
SIG_TIMEOUT = 'Timeout'
