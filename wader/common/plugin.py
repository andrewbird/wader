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
"""Plugin system for Wader"""

from zope.interface import implements
from twisted.python import log
from twisted.plugin import IPlugin, getPlugins

from wader.common.consts import MDM_INTFACE, HSO_INTFACE, CRD_INTFACE
from wader.common.daemon import build_daemon_collection
import wader.common.exceptions as ex
import wader.common.interfaces as interfaces
from wader.common.utils import flatten_list
from wader.common.sim import SIMBaseClass

class DevicePlugin(object):
    """Base class for all plugins"""

    implements(IPlugin, interfaces.IDevicePlugin)
    __properties__ = {}
    # at what speed should we talk with this device?
    baudrate = 115200
    # Class that will initialize the SIM, by default SIMBaseClass
    sim_klass = SIMBaseClass
    # Response of AT+CGMM
    __remote_name__ = ""
    # instance of a custom adapter class if device needs customization
    custom = None
    # instance of the exporter class that will export AT methods
    exporter = None
    # dialer
    dialer = 'default'

    def __init__(self):
        super(DevicePlugin, self).__init__()
        # sim instance
        self.sim = None
        # serial connection reference
        self.sconn = None
        # is this device enabled?
        self.enabled = False
        # properties for org.freedesktop.DBus.Properties interface
        self.props = {}
        # collection of daemons
        self.daemons = None
        # DBus UDI
        self.udi = None
        self.root_udi = None
        # onyl used in devices that like to share ids, like
        # huawei's exxx family. It should have at least a
        # 'default' key mapping to a safe device that can be
        # used to identify the rest of the family
        self.mapping = {}
        # dictionary with org.freedesktop.DBus.Properties
        self.props = { MDM_INTFACE : {}, HSO_INTFACE : {}, CRD_INTFACE : {} }
        self.ports = None

    def __repr__(self):
        args = (self.__class__.__name__, self.ports)
        return "<%s %s>" % args

    def close(self, remove_from_conn=False):
        """Closes the plugin and frees all the associated resources"""
        log.msg("Closing plugin %s" % self)

        if self.sconn and self.sconn.transport:
            self.sconn.transport.unregisterProducer()

        try:
            if self.ports.cport.obj:
                self.ports.cport.obj.connectionLost("Closing connection")
                self.ports.cport.obj.loseConnection("Bye!")
                self.ports.cport.obj = None
        except:
            log.err()

        if self.daemons is not None and self.daemons.running:
            self.daemons.stop_daemons()

        try:
            if self.exporter and remove_from_conn:
                self.exporter.remove_from_connection()
        except LookupError, e:
            log.err(e)

    def initialize(self, init_obj=None):
        """Initializes the SIM"""
        def on_init(size):
            if not self.daemons:
                self.daemons = build_daemon_collection(self)

            self.daemons.start_daemons()
            d = self.sconn.init_properties()
            d.addCallback(lambda _: size)
            return d

        self.sim = self.sim_klass(self.sconn)
        d = self.sim.initialize()
        d.addCallback(on_init)
        return d

    def patch(self, other):
        """Patch myself in-place with the settings of another plugin"""
        if not isinstance(other, DevicePlugin):
            raise ValueError("Cannot patch myself with a %s" % type(other))

        self.udi = other.udi
        self.root_udi = other.root_udi
        self.ports = other.ports
        self.props = other.props.copy()
        self.baudrate = other.baudrate


class RemoteDevicePlugin(DevicePlugin):
    """
    Base class from which all the RemoteDevicePlugins should inherit from
    """
    implements(IPlugin, interfaces.IRemoteDevicePlugin)


BASE_PATH_DICT = {}

class OSPlugin(object):
    """Base class from which all the OSPlugins should inherit from"""
    implements(IPlugin, interfaces.IOSPlugin)
    dialer = None
    hw_manager = None

    def __init__(self):
        super(OSPlugin, self).__init__()

    def get_timezone(self):
        """
        Returns the timezone

        :rtype: str
        """
        raise NotImplementedError()

    def get_tzinfo(self):
        """Returns a :class:`pytz.timezone` out the timezone"""
        from pytz import timezone
        zone = self.get_timezone()
        try:
            return timezone(zone)
        except:
            # we're not catching this exception because some dated pytz
            # do not include UnknownTimeZoneError, if get_tzinfo doesn't works
            # we just return None as its a valid tzinfo and we can't do more
            return None

    def get_iface_stats(self, iface):
        """
        Returns ``iface`` network statistics

        :rtype: tuple
        """
        raise NotImplementedError()

    def is_valid(self):
        """Returns True if we are on the given OS/Distro"""
        raise NotImplementedError()

    def initialize(self):
        """Initializes the plugin"""
        pass


import wader.plugins
class PluginManager(object):
    """I manage WaderCdfL's plugins"""

    @classmethod
    def get_plugins(cls, interface=IPlugin, package=wader.plugins):
        """
        Returns all the plugins under ``package`` that implement ``interface``
        """
        return getPlugins(interface, package)

    @classmethod
    def get_plugin_by_remote_name(cls, name,
                                  interface=interfaces.IDevicePlugin):
        """
        Get a plugin by its remote name

        :raise UnknownPluginNameError: When we don't know about the plugin
        """
        for plugin in cls.get_plugins(interface, wader.plugins):
            if not hasattr(plugin, '__remote_name__'):
                continue

            if plugin.__remote_name__ == name:
                return plugin

            if hasattr(plugin, 'mapping'):
                if name in plugin.mapping:
                    return plugin.mapping[name]()

        raise ex.UnknownPluginNameError(name)

    @classmethod
    def get_plugin_by_vendor_product_id(cls, product_id, vendor_id):
        """Get a plugin by its product and vendor ids"""
        log.msg("get_plugin_by_id called with 0x%X and 0x%X" % (product_id,
                                                            vendor_id))
        for plugin in cls.get_plugins(interfaces.IDevicePlugin):
            props = flatten_list(plugin.__properties__.values())
            if int(product_id) in props and int(vendor_id) in props:
                if not plugin.mapping:
                    # regular plugin
                    return plugin

                # device has multiple personalities...
                # this will just return the default plugin for
                # the mapping, we keep a reference to the mapping
                # once the device is properly identified by
                # wader.common.hardware.base::identify_device
                _plugin = plugin.mapping['default']()
                _plugin.mapping = plugin.mapping
                return _plugin

        return None

