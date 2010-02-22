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
"""Logging Serial Port and related classes"""

from twisted.internet.serialport import SerialPort as _SerialPort
from twisted.python import log


class Port(object):
    """I represent a serial port in Wader"""

    def __init__(self, path):
        self._port_path = path
        self._sport_obj = None

    def get_port_path(self):
        return self._port_path

    def set_port_path(self, path):
        self._port_path = path

    def get_sport_obj(self):
        return self._sport_obj

    def set_sport_obj(self, obj):
        self._sport_obj = obj

    path = property(get_port_path, set_port_path)
    obj = property(get_sport_obj, set_sport_obj)


class Ports(object):
    """I am a pair of :class:`~wader.common.serialport.Port` objects"""

    def __init__(self, dport, cport):
        self.dport = Port(dport)
        self.cport = Port(cport)

    def get_application_port(self):
        """Returns the application port"""
        if self.cport.path:
            return self.cport
        elif self.dport.path:
            return self.dport
        else:
            raise AttributeError("No application port")

    def has_two(self):
        """
        Check if there are two active ports

        :rtype: bool
        """
        return all([self.dport.path, self.cport.path])

    def __repr__(self):
        if not self.cport.path:
            return "dport: %s" % (self.dport.path)

        return "dport: %s cport: %s" % (self.dport.path, self.cport.path)


class SerialPort(_SerialPort, log.Logger):
    """Small wrapper over Twisted's serial port to make it loggable"""

    def __init__(self, protocol, port, reactor, baudrate=115200, timeout=.1):
        super(SerialPort, self).__init__(protocol, port, reactor,
                                         baudrate=baudrate, timeout=timeout)
        self._port = port

    def logPrefix(self):
        """Returns the last part of the port being used"""
        return self._port.split('/')[-1]
