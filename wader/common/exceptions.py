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
"""All the exceptions in Wader"""


class DeviceLockedError(Exception):
    """
    Exception raised after an authentication mess ending up in a device locked
    """


class LimitedServiceNetworkError(Exception):
    """Exception raised when AT+COPS? replied 'Limited Service'"""


class MalformedSMSError(Exception):
    """Exception raised when an error is received decodifying a SMS"""


class NetworkRegistrationError(Exception):
    """
    Exception raised when an error occurred while registering with the network
    """


class PluginInitialisationError(Exception):
    """Exception raised when an error occurred while initialisating a plugin"""


class ProfileNotFoundError(Exception):
    """Exception raised when a profile hasn't been found"""


class UnknownPluginNameError(Exception):
    """
    Exception raised when we don't have a plugin with the given remote name
    """
