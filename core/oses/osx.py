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

from functools import partial
import sys

from twisted.internet import defer
from twisted.python import log, reflect
from zope.interface import implements

from wader.common.consts import (MDM_INTFACE, MM_MODEM_TYPE_REV,
                                 NET_INTFACE, MM_IP_METHOD_PPP)
from core.hardware.base import _identify_device
from wader.common.interfaces import IHardwareManager
from core.oses.unix import UnixPlugin
from core.plugin import PluginManager
from core.serialport import Ports
from core.startup import setup_and_export_device


class OSXPlugin(UnixPlugin):
    """OSPlugin for OSX"""

    dialer = None

    def __init__(self):
        super(OSXPlugin, self).__init__()
        self.hw_manager = HardwareManager()

    def get_iface_stats(self, iface):
        """See :meth:`wader.common.interfaces.IOSPlugin.get_iface_stats`"""
        # XXX: implementation missing
        return 0, 0

    def is_valid(self):
        """See :meth:`wader.common.interfaces.IOSPlugin.is_valid`"""

        # XXX: Disable OSX support until we can find the provenance of the C
        #      module, or replace it with something else.
        return False

        return sys.platform == 'darwin'

    def update_dns_cache(self):
        # XXX: implementation missing
        pass


class HardwareManager(object):
    """I find and configure devices"""

    implements(IHardwareManager)

    def __init__(self):
        super(HardwareManager, self).__init__()
        self.controller = None
        self._device_count = -1
        self.clients = {}

    def register_controller(self, controller):
        """
        See `IHardwareManager.register_controller`
        """
        self.controller = controller

    def get_devices(self):
        """See :meth:`wader.common.interfaces.IHardwareManager.get_devices`"""
        # so pylint does not complain on Linux
        osxserialports = reflect.namedAny('core.oses.osxserialports')
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
            device = dev_info['callout'].split('/')[-1]
            set_property = partial(plugin.set_property, emit=True)
            set_property(MDM_INTFACE, 'Device', device)
            # XXX: Fix MasterDevice
            set_property(MDM_INTFACE, 'MasterDevice',
                        'iokit:com.vodafone.BMC.NotImplemented')
            # XXX: Fix CDMA
            set_property(MDM_INTFACE, 'Type', MM_MODEM_TYPE_REV['GSM'])
            set_property(MDM_INTFACE, 'Driver', 'notimplemented')
            set_property(MDM_INTFACE, 'IpMethod', MM_IP_METHOD_PPP)
            set_property(MDM_INTFACE, 'Enabled', False)
            set_property(MDM_INTFACE, 'UnlockRequired', "")

            # set to unknown
            set_property(NET_INTFACE, 'AccessTechnology', 0)
            # set to -1 so any comparison will fail and will update it
            set_property(NET_INTFACE, 'AllowedMode', -1)

            plugin.opath = self._generate_opath()
            plugin.ports = Ports(dev_info['callout'], dev_info['dialin'])

        return plugin

    def _check_if_devices_are_registered(self, devices):
        for device in devices:
            if device.opath not in self.clients:
                self._register_client(device, emit=True)

        return devices

    def _register_client(self, plugin, emit=False):
        """
        Registers `plugin` in `self.clients`

        Will emit a DeviceAdded signal if emit is True
        """
        log.msg("registering plugin %s with opath %s" % (plugin, plugin.opath))
        self.clients[plugin.opath] = setup_and_export_device(plugin)
        if emit:
            self.controller.DeviceAdded(plugin.opath)

    def _generate_opath(self):
        self._device_count += 1
        return '/org/freedesktop/ModemManager/Devices/%d' % self._device_count
