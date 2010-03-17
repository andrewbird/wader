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
"""Linux-based OS plugin"""

from functools import partial
from os.path import join, exists
import re

import gudev
from zope.interface import implements
from twisted.internet import defer, reactor, utils
from twisted.python import log

from wader.common.interfaces import IHardwareManager
from wader.common.hardware.base import identify_device, probe_ports
from wader.common.plugin import PluginManager
from wader.common import consts
from wader.common.oses.unix import UnixPlugin
from wader.common.startup import setup_and_export_device
from wader.common.serialport import Ports
from wader.common.utils import get_file_data, natsort


IDLE, BUSY = range(2)
ADD_THRESHOLD = 6

MODEL, VENDOR, DRIVER = "ID_MODEL_ID", "ID_VENDOR_ID", "ID_USB_DRIVER"

SUBSYSTEMS = ["tty", "usb", "net"]
REQUIRED_PROPS = [VENDOR, MODEL, DRIVER, "ID_BUS", "DEVNAME"]
BAD_DEVFILE = re.compile('^/dev/(tty\d*?|console|ptmx)$')


class HardwareManager(object):
    """
    I find and configure devices on Linux

    I am resilient to ports assigned in unusual locations
    and devices sharing ids.
    """

    implements(IHardwareManager)

    def __init__(self):
        super(HardwareManager, self).__init__()
        #: dictionary with all my configured clients
        self.clients = {}
        #: reference to StartupController
        self.controller = None
        self._waiting_deferred = None
        # remember the total client count for opath generation
        self._client_count = -1
        self.gudev_client = gudev.Client(SUBSYSTEMS)
        # temporary place to store hotplugged devices to process
        self._hotplugged_devices = []
        self._call = None

        self._connect_to_signals()

    def _connect_to_signals(self):
        self.gudev_client.connect("uevent", self._on_uevent)

    def _on_uevent(self, client, action, device):
        log.msg("UEVENT device: %s  action: %s" % (device.get_sysfs_path(), action))
        if action == 'remove':
            # handle remove
            for opath, plugin in self.clients.items():
                if plugin.sysfs_path == device.get_sysfs_path():
                    self.controller.DeviceRemoved(plugin.opath)
                    self._unregister_client(plugin)

        elif action == 'add':
            # if valid, append it to the list of hotplugged devices
            # for later processing
            if self._is_valid_device(device):
                self._hotplugged_devices.append(device)

            if self._call is None:
                # the first time we set a small delay and whenever a device
                # is added we will reset the call ADD_THRESHOLD seconds
                self._call = reactor.callLater(2,
                                            self._process_hotplugged_devices)
            elif self._call.active():
                # XXX: this can be optimized by substracting x milliseconds
                # for every device added to the reset call. However it
                # introduces some more logic and perhaps should live outside.

                self._call.reset(ADD_THRESHOLD)

    def register_controller(self, controller):
        """
        See `IHardwareManager.register_controller`
        """
        self.controller = controller

    def get_devices(self):
        """See :meth:`wader.common.interfaces.IHardwareManager.get_devices`"""
        # If clients is an empty dict we assume that this is the first
        # time get_devices is executed. If not, we just return the current
        # devices. If get_devices is executed in the middle of a hotplugging
        # event, the "just added" device won't be returned, but it will be
        # processed in a few seconds by _process_hotplugged_devices anyway.
        if self.clients:
            return defer.succeed(self.clients.values())

        devices = []
        # get all the devices under the tty, usb and net subsystems
        for subsystem in SUBSYSTEMS:
            for device in self.gudev_client.query_by_subsystem(subsystem):
                if self._is_valid_device(device):
                    devices.append(device)

        return self._process_found_devices(devices)

    def _process_hotplugged_devices(self):
        # get DevicePlugin out of a list of gudev.Device
        self._process_found_devices(self._hotplugged_devices)
        self._hotplugged_devices, self._call = [], None

    def _process_found_devices(self, devices=None, emit=True):
        """
        Processes gudev ``devices`` and returns ``DevicePlugin``s

        Find devices with a common parent and merge them, identify
        the ones that need it, register and emit a signal if ``emit``
        is True.
        """
        deferreds = []
        for device in self._setup_devices(devices):
            d = identify_device(device)
            d.addCallback(self._register_client, emit=emit)
            deferreds.append(d)

        return defer.gatherResults(deferreds)

    def _is_valid_device(self, device):
        """Checks whether ``device`` is valid"""
        if not device.get_device_file():
            return False

        # before checking all the properties, filter out all the /dev/tty%d
        if BAD_DEVFILE.match(device.get_device_file()):
            return False

        # filter out /dev/usb/foo/bar/foo like too
        parts = device.get_device_file().split('/')
        if len(parts) > 3:
            return False

        # check that it has all the required properties
        # otherwise we are not interested on it
        props = device.get_property_keys()
        for prop in REQUIRED_PROPS:
            if prop not in props:
                return False

        return True

    def _setup_devices(self, devices):
        """Sets up ``devices``"""
        found_devices = {}
        for device in devices:
            props = {}

            for property in REQUIRED_PROPS:
                value = device.get_property(property)
                # values are either string or hex
                try:
                    props[property] = int(value, 16)
                except ValueError:
                    props[property] = value

            # if this properties are present, we should use them as
            # data port and control port
            for mm_prop in ['ID_MM_PORT_TYPE_MODEM', 'ID_MM_PORT_TYPE_AUX']:
                if mm_prop in device.get_property_keys():
                    props[mm_prop] = bool(int(device.get_property(mm_prop)))

            # now find out the device parent
            parent = self._get_last_parent_that_matches_props(device, props)

            if parent in self.clients:
                # this device has already been setup
                return

            if parent in found_devices:
                # we have already found a device with the same parent, update
                # the attributes
                found_devices[parent].update(props)
            else:
                # a new parent has been found, store its sysfs_path as key
                # as all the childs have the same property DEVNAME, we need to
                # create a new and temporal property named DEVICES
                found_devices[parent] = props
                found_devices[parent]['DEVICES'] = []

            if 'DEVNAME' in props:
                # append the device name as usual
                found_devices[parent]['DEVICES'].append(props['DEVNAME'])
                # if any of this is present save them for later use
                for _prop in ['ID_MM_PORT_TYPE_MODEM', 'ID_MM_PORT_TYPE_AUX']:
                    if props.get(_prop, False):
                        found_devices[parent][_prop] = props['DEVNAME']

        return [self._get_device_from_info(sysfs_path, info)
                      for sysfs_path, info in found_devices.items()]

    def _get_last_parent_that_matches_props(self, device, props):
        parent = device.get_parent()
        while 1:
            properties = {}
            for key in parent.get_property_keys():
                properties[key] = parent.get_property(key)
                if key == "PRODUCT":
                    # udev seems to miss the ID_VENDOR_ID and ID_MODEL_ID attrs
                    # and all of the sudden a "PRODUCT" attribute appears with
                    # a value of ID_VENDOR_ID/ID_MODEL_ID/UNKNOWN.
                    vendor, model = parent.get_property(key).split('/')[:2]
                    properties[VENDOR] = int(vendor, 16)
                    properties[MODEL] = int(model, 16)

            if VENDOR in properties and MODEL in properties:
                if (props[VENDOR] != properties[VENDOR] and
                        props[MODEL] != properties[MODEL]):
                    break

            parent = parent.get_parent()
            if parent is None:
                path = device.get_sysfs_path()
                raise ValueError("Could not find %s parent" % path)

        # XXX: need to check with modemmanager if it matches
        return parent.get_sysfs_path()

    def _register_client(self, plugin, emit=False):
        """
        Registers `plugin` in `self.clients` indexes by its object path

        Will emit a DeviceAdded signal if emit is True
        """
        log.msg("registering plugin %s using opath %s" % (plugin, plugin.opath))
        self.clients[plugin.opath] = setup_and_export_device(plugin)

        if emit:
            self.controller.DeviceAdded(plugin.opath)

        return plugin

    def _unregister_client(self, client):
        """Removes client identified by ``opath``"""
        plugin = self.clients.pop(client.opath)
        plugin.close(removed=True)

    def _generate_opath(self):
        self._client_count += 1
        return "/org/freedesktop/ModemManager/Devices/%d" % self._client_count

    def _get_hso_ports(self, ports):
        dport = cport = None
        for port in ports:
            name = port.split('/')[-1]
            path = join('/sys/class/tty', name, 'hsotype')

            if exists(path):
                what = get_file_data(path).strip().lower()
                if what == 'modem':
                    dport = port
                elif what == 'application':
                    cport = port

                if dport and cport:
                    break

        return dport, cport

    def _get_hso_device(self, sysfs_path):
        for device in self.gudev_client.query_by_subsystem("net"):
            if device.get_sysfs_path().startswith(sysfs_path):
                return device.get_property("INTERFACE")

        raise ValueError("Cannot find hso device for device %s" % sysfs_path)

    def _get_device_from_info(self, sysfs_path, info):
        """Returns a `DevicePlugin` out of ``info``"""
        # order the ports before probing
        ports = info['DEVICES']
        natsort(ports)

        query = [info.get(key) for key in [VENDOR, MODEL]]
        plugin = PluginManager.get_plugin_by_vendor_product_id(*query)
        if plugin:
            plugin.sysfs_path = sysfs_path
            plugin.opath = self._generate_opath()
            set_property = partial(plugin.set_property, emit=False)
            # set DBus properties (Modem interface)
            set_property(consts.MDM_INTFACE, 'IpMethod',
                         consts.MM_IP_METHOD_PPP)
            set_property(consts.MDM_INTFACE, 'MasterDevice',
                         'udev:%s' % sysfs_path)
            # XXX: Fix CDMA
            set_property(consts.MDM_INTFACE, 'Type',
                         consts.MM_MODEM_TYPE_REV['GSM'])
            set_property(consts.MDM_INTFACE, 'Driver', info[DRIVER])
            set_property(consts.MDM_INTFACE, 'Enabled', False)
            set_property(consts.MDM_INTFACE, 'UnlockRequired', "")

            # set to unknown
            set_property(consts.NET_INTFACE, 'AccessTechnology', 0)
            # set to -1 so any comparison will fail and will update it
            set_property(consts.NET_INTFACE, 'AllowedMode', -1)

            # preprobe stuff
            if hasattr(plugin, 'preprobe_init'):
                # this plugin requires special initialisation before probing
                plugin.preprobe_init(ports, info)

            # now get the ports
            ports_need_probe = True
            if plugin.get_property(consts.MDM_INTFACE, 'Driver') == 'hso':
                dport, cport = self._get_hso_ports(ports)
                ports_need_probe = False

            elif plugin.get_property(consts.MDM_INTFACE, 'Driver') == 'cdc_acm':
                # MBM device
                # XXX: Not all CDC devices support DHCP, to override see
                #      plugin attribute 'ipmethod'
                # XXX: Also need to support Ericsson devices via 'hso' dialer
                #      so that we can use the plain backend. At least F3607GW
                #      supports a get_ip4_config() style AT command to get
                #      network info, else we need to implement a DHCP client
                # set DBus properties (Modem.Gsm.Hso interface)
                hso_device = self._get_hso_device(sysfs_path)
                set_property(consts.MDM_INTFACE, 'Device', hso_device)

                set_property(consts.MDM_INTFACE, 'IpMethod',
                             consts.MM_IP_METHOD_DHCP)

            if plugin.dialer in 'hso':
                # set DBus properties (Modem.Gsm.Hso interface)
                hso_device = self._get_hso_device(sysfs_path)
                set_property(consts.MDM_INTFACE, 'Device', hso_device)

                if hasattr(plugin, 'ipmethod'):
                    # allows us to specify a method in a driver independant way
                    set_property(consts.MDM_INTFACE, 'IpMethod',
                                 plugin.ipmethod)

            # if this two properties are present, use them right away and
            # do not probe
            if ('ID_MM_PORT_TYPE_MODEM' in info
                    or 'ID_MM_PORT_TYPE_AUX' in info):
                try:
                    dport = info['ID_MM_PORT_TYPE_MODEM']
                    log.msg("%s: ID_MM_PORT_TYPE_MODEM" % dport)
                except KeyError:
                    pass
                try:
                    cport = info['ID_MM_PORT_TYPE_AUX']
                    log.msg("%s: ID_MM_PORT_TYPE_AUX" % cport)
                except KeyError:
                    pass

                ports_need_probe = False

            if ports_need_probe:
                # the ports were not hardcoded nor was an HSO device
                dport, cport = probe_ports(ports)

            if not dport and not cport:
                # this shouldn't happen
                msg = 'No data port and no control port with ports: %s'
                raise RuntimeError(msg % ports)

            if 'Device' not in plugin.get_properties(consts.MDM_INTFACE):
                # do not set it again
                device = dport.split('/')[-1]
                set_property(consts.MDM_INTFACE, 'Device', device)

            plugin.ports = Ports(dport, cport)
            return plugin

        raise RuntimeError("Could not find a plugin with info %s" % info)


def get_hw_manager():
    try:
        return HardwareManager()
    except:
        return None


class LinuxPlugin(UnixPlugin):
    """OSPlugin for Linux-based distros"""

    dialer = None
    hw_manager = get_hw_manager()

    def __init__(self):
        super(LinuxPlugin, self).__init__()

    def is_valid(self):
        raise NotImplementedError()

    def add_default_route(self, iface):
        """See :meth:`wader.common.interfaces.IOSPlugin.add_default_route`"""
        args = ['add', 'default', 'dev', iface]
        return utils.getProcessValue('/sbin/route', args, reactor=reactor)

    def delete_default_route(self, iface):
        """
        See :meth:`wader.common.interfaces.IOSPlugin.delete_default_route`
        """
        args = ['delete', 'default', 'dev', iface]
        return utils.getProcessValue('/sbin/route', args, reactor=reactor)

    def configure_iface(self, iface, ip='', action='up'):
        """See :meth:`wader.common.interfaces.IOSPlugin.configure_iface`"""
        assert action in ['up', 'down']
        if action == 'down':
            args = [iface, action]
        else:
            args = [iface, ip, 'netmask', '255.255.255.255', '-arp', action]

        return utils.getProcessValue('/sbin/ifconfig', args, reactor=reactor)

    def get_iface_stats(self, iface):
        """See :meth:`wader.common.interfaces.IOSPlugin.get_iface_stats`"""
        stats_path = "/sys/class/net/%s/statistics" % iface
        rx_b = join(stats_path, 'rx_bytes')
        tx_b = join(stats_path, 'tx_bytes')
        try:
            return map(int, [get_file_data(rx_b), get_file_data(tx_b)])
        except (IOError, OSError):
            return 0, 0
