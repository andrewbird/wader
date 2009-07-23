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
"""DevicePlugin for OSX"""

import sys

from twisted.internet import defer
from twisted.python import log
from zope.interface import implements

from wader.common import consts
from wader.common.hardware.base import _identify_device
from wader.common.interfaces import IHardwareManager
from wader.common.oses.unix import UnixPlugin
from wader.common.plugin import PluginManager
from wader.common.serialport import Ports
from wader.common.startup import setup_and_export_device

class OSXPlugin(UnixPlugin):
    """OSPlugin for OSX"""

    dialer = None

    def __init__(self):
        super(OSXPlugin, self).__init__()
        self.hw_manager = HardwareManager()

    def get_iface_stats(self, iface):
        """See :meth:`wader.common.interfaces.IOSPlugin.get_iface_stats`"""
        # TODO: implement
        return 0, 0

    def is_valid(self):
        """See :meth:`wader.common.interfaces.IOSPlugin.is_valid`"""
        return sys.platform == 'darwin'


class HardwareManager(object):
    """I find and configure devices"""
    implements(IHardwareManager)

    def __init__(self):
        super(HardwareManager, self).__init__()
        self.controller = None
        self.clients = {}

    def register_controller(self, controller):
        """
        See :meth:`wader.common.interfaces.IHardwareManager.register_controller`
        """
        self.controller = controller

    def get_devices(self):
        """See :meth:`wader.common.interfaces.IHardwareManager.get_devices`"""
        # so pylint does not complain on Linux
        osxserialports = __import__('osxserialports')
        devs_info = [d for d in osxserialports.modems()
                        if 'Modem' in d['suffix']]
        deferreds = []
        for dev in devs_info:
            port = dev['dialin'] if dev['dialin'] else dev['callout']
            d = defer.maybeDeferred(_identify_device, port)
            d.addCallback(self._get_device_from_model, dev)
            deferreds.append(d)

        d = defer.gatherResults(deferreds)
        d.addCallback(self._check_if_devices_are_registered)
        return d

    def _get_device_from_model(self, model, dev_info):
        plugin = PluginManager.get_plugin_by_remote_name(model)
        if plugin:
            props = plugin.props[consts.MDM_INTFACE]
            props['Device'] = dev_info['callout']
            props['Control'] = dev_info['dialin']
            # XXX: Fix MasterDevice
            props['MasterDevice'] = 'iokit:com.vodafone.BMC.NotImplemented'

            # XXX: Fix CDMA
            props['Type'] = consts.MM_MODEM_TYPE_REV['GSM']
            plugin.udi = self._get_udi_from_devinfo(dev_info, model)
            plugin.ports = Ports(dev_info['callout'], dev_info['dialin'])

        return plugin

    def _check_if_devices_are_registered(self, devices):
        for device in devices:
            if device.udi not in self.clients:
                self._register_client(device, device.udi, True)

        return devices

    def _register_client(self, plugin, udi, emit=False):
        """
        Registers `plugin` in `self.clients` using `udi`

        Will emit a DeviceAdded signal if emit is True
        """
        log.msg("registering plugin %s using udi %s" % (plugin, udi))
        self.clients[udi] = setup_and_export_device(plugin)
        if emit:
            self.controller.DeviceAdded(udi)

    def _get_udi_from_devinfo(self, dev_info, model):
        base = dev_info['base'].replace('-', '')
        udi = "/device/%s/%s" % (base, model.replace(' ', ''))
        return udi

