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

from time import time
from os.path import join, exists

import dbus
import serial
from zope.interface import implements
from twisted.internet import defer, reactor, utils, error
from twisted.python import log

from wader.common._dbus import DBusComponent
from wader.common.interfaces import IHardwareManager
from wader.common.plugin import PluginManager
from wader.common import consts
from wader.common.oses.unix import UnixPlugin
from wader.common.startup import setup_and_export_device
from wader.common.serialport import Ports
from wader.common.utils import get_file_data, natsort, flatten_list

IDLE, BUSY = range(2)
ADD_THRESHOLD = 10.


def probe_port(port):
    """
    Check whether `port` exists and works

    :rtype: bool
    """
    try:
        ser = serial.Serial(port, timeout=.01)
        try:
            ser.write('AT+CGMR\r\n')
        except OSError, e:
            log.err(e, "Error identifying device in port %s" % port)
            return False
        if not ser.readline():
            # Huawei E620 with driver option registers three serial
            # ports and the middle one wont raise any exception while
            # opening it even thou its a dummy port.
            return False

        return True
    except serial.SerialException, e:
        return False
    finally:
        if 'ser' in locals():
            ser.close()


def probe_ports(ports):
    """
    Obtains the data and control ports out of ``ports``

    :rtype: tuple
    """
    dport = cport = None
    while ports:
        port = ports.pop(0)
        if probe_port(port):
            if dport is None:
                # data port tends to the be the first one
                dport = port
            elif cport is None:
                # control port the next one
                cport = port
                break

    return dport, cport


def extract_info(props):
    """
    Extracts the bus-related information from Hal's ``props``

    :param props: Hal dict
    :rtype: dict
    """
    info = {}
    if 'usb.vendor_id' in props:
        info['usb_device.vendor_id'] = props['usb.vendor_id']
        info['usb_device.product_id'] = props['usb.product_id']
    elif 'usb_device.vendor_id' in props:
        info['usb_device.vendor_id'] = props['usb_device.vendor_id']
        info['usb_device.product_id'] = props['usb_device.product_id']
    elif 'pcmcia.manf_id' in props:
        info['pcmcia.manf_id'] = props['pcmcia.manf_id']
        info['pcmcia.card_id'] = props['pcmcia.card_id']
    elif 'pci.vendor_id' in props:
        info['pci.vendor_id'] = props['pci.vendor_id']
        info['pci.product_id'] = props['pci.product_id']
    else:
        raise RuntimeError("Unknown bus for device %s" % props['info.udi'])

    return info


class HardwareManager(DBusComponent):
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
        self.mode = IDLE
        # list with the added udis during a hotplugging event
        self.added_udis = []
        # last time of an action
        self.last_action = None
        self.call_id = None
        # list of waiting get_devices petitions
        self._waiting = []

        self._connect_to_signals()

    def _connect_to_signals(self):
        self.manager.connect_to_signal('DeviceAdded', self._dev_added_cb)
        self.manager.connect_to_signal('DeviceRemoved', self._dev_removed_cb)

    def register_controller(self, controller):
        """
        See :meth:`wader.common.interfaces.IHardwareManager.register_controller`
        """
        self.controller = controller

    def get_devices(self):
        """See :meth:`wader.common.interfaces.IHardwareManager.get_devices`"""
        # only enter here if its the very first time
        if self.mode == IDLE and not self.clients:
            self.mode = BUSY
            parent_udis = self._get_parent_udis()
            d = self._get_devices_from_udis(parent_udis)
            d.addCallback(self._check_if_devices_are_registered)
            return d

        elif self.mode == IDLE:
            return defer.succeed(self.clients.values())

        # we are waiting for an on-going process started already
        # we queue the request and will be callbacked when the
        # data is ready
        d = defer.Deferred()
        self._waiting.append(d)
        return d

    def _transition_to_idle(self, ignored=None):
        self.mode = IDLE

    def _get_device_from_udi(self, udi):
        """Returns a device built out of the info extracted from ``udi``"""
        context = self._get_child_udis_from_udi(udi)
        info = extract_info(self.get_properties_from_udi(udi))
        ports = self._get_ports_from_udi(udi, context=context)
        device = self._get_device_from_info_and_ports(info, udi, ports,
                                                      context=context)
        return device

    def _get_devices_from_udis(self, udis):
        """
        Returns a list of devices built out of the info extracted from ``udis``
        """
        from wader.common.hardware.base import identify_device
        unknown_devs = map(self._get_device_from_udi, udis)
        deferreds = map(identify_device, unknown_devs)
        return defer.gatherResults(deferreds)

    def _get_modem_path(self, dev_udi):
        """Returns the object path of the modem device child of ``dev_udi``"""

        def is_child_of(parent_udi, child_udi):
            cur_udi = child_udi
            while 1:
                try:
                    p = self.get_properties_from_udi(cur_udi)['info.parent']
                    if p == parent_udi:
                        return True
                except KeyError:
                    return False
                else:
                    cur_udi = p

        for udi in self.manager.FindDeviceByCapability("modem"):
            if is_child_of(dev_udi, udi):
                return udi

        raise RuntimeError("Couldn't find the modem path of %s" % dev_udi)

    def _get_hso_modem_path(self, udi):
        child_udis = flatten_list(self._get_child_udis_from_udi(udi))
        obj = dbus.SystemBus().get_object(consts.NM_SERVICE, consts.NM_OBJPATH)
        devices = obj.GetDevices(dbus_interface=consts.NM_INTFACE)

        while devices:
            udi = devices.pop()
            # if nm08_present
            # this will break BMC, beware!
            if 'NetworkManager' in udi:
                # NM 0.8
                device = dbus.SystemBus().get_object(consts.NM_SERVICE, udi)
                try:
                    mdm_udi = device.Get(consts.NM_DEVICE, 'Udi',
                                         dbus_interface=dbus.PROPERTIES_IFACE)
                    if mdm_udi and mdm_udi in child_udis:
                        return mdm_udi
                except:
                    log.err()
            else:
                # NM <= 0.7.1
                if 'serial.device' in self.get_properties_from_udi(udi):
                    if udi in child_udis:
                        return udi

    def _get_driver_name(self, udi, context=None):
        """Returns the info.linux.driver of `udi`"""

        def do_get_driver_name(key, _udi, props):
            if key in props[_udi]:
                name = props[_udi][key]
                if name not in ['usb', 'usb-storage', 'pci', 'pcmcia']:
                    return name

        if context:
            childs, device_props = context
        else:
            childs, device_props = self._get_child_udis_from_udi(udi)

        # extend the list of childs with the parent udi itself, devices
        # such as Option Nozomi won't work otherwise
        childs.extend([udi])

        for _udi in childs:
            name = do_get_driver_name('info.linux.driver', _udi, device_props)
            if name:
                return name

        raise RuntimeError("Could not find the driver name of device %s" % udi)

    def _get_network_device(self, udi, context=None):
        if context:
            childs, dp = context
        else:
            childs, dp = self._get_child_udis_from_udi(udi)

        for _udi in childs:
            properties = dp[_udi]
            if 'net.interface' in properties:
                return properties['net.interface']

        raise KeyError("Couldn't find net.interface in device %s" % udi)

    def _get_parent_udis(self):
        """Returns the root udi of all the devices with modem capabilities"""
        return set(map(self._get_parent_udi,
                       self.manager.FindDeviceByCapability("modem")))

    def _get_parent_udi(self, udi):
        """Returns the absolute parent udi of ``udi``"""
        OD = 'serial.originating_device'

        def get_parent(props):
            return (props[OD] if OD in props else props['info.parent'])

        current_udi = udi
        while 1:
            properties = self.get_properties_from_udi(current_udi)
            try:
                info = extract_info(properties)
                break
            except RuntimeError:
                current_udi = get_parent(properties)

        # now that we have an id to lookup for, lets repeat the process till we
        # get another RuntimeError
        def find_out_if_contained(_info, properties):
            """
            Returns `True` if `_info` values are contained in `props`

            As hal likes to swap between usb.vendor_id and usb_device.vendor_id
            I have got a special case where I will retry
            """

            def compare_dicts(d1, d2):
                for key in d1:
                    try:
                        return d1[key] == d2[key]
                    except KeyError:
                        return False

            if compare_dicts(_info, properties):
                # we got a straight map
                return True

            # hal likes to swap between usb_device.vendor_id and usb.vendor_id
            if 'usb_device.vendor_id' in _info:
                # our last chance, perhaps its swapped
                newinfo = {'usb.vendor_id' : _info['usb_device.vendor_id'],
                           'usb.product_id' : _info['usb_device.product_id']}
                return compare_dicts(newinfo, properties)

            # the original compare_dicts failed, so return False
            return False

        last_udi = current_udi
        while 1:
            properties = self.get_properties_from_udi(current_udi)
            if not find_out_if_contained(info, properties):
                break

            last_udi, current_udi = current_udi, get_parent(properties)

        return last_udi

    def _check_if_devices_are_registered(self, devices, to_idle=True):
        for device in devices:
            if device.udi not in self.clients:
                self._register_client(device, device.udi, emit=True)

        for deferred in self._waiting:
            deferred.callback(devices)

        self._waiting = []

        if to_idle:
            # back to IDLE
            self._transition_to_idle()

        return devices

    def _register_client(self, plugin, udi, emit=False):
        """
        Registers `plugin` in `self.clients` by its `udi`

        Will emit a DeviceAdded signal if emit is True
        """
        log.msg("registering plugin %s using udi %s" % (plugin, udi))
        self.clients[udi] = setup_and_export_device(plugin)

        if emit:
            self.controller.DeviceAdded(udi)

    def _unregister_client(self, udi):
        """Removes client identified by ``udi``"""
        plugin = self.clients.pop(udi)
        plugin.close(removed=True)

    def _dev_added_cb(self, udi):
        self.mode = BUSY
        self.last_action = time()

        assert udi not in self.added_udis
        self.added_udis.append(udi)

        try:
            if not self.call_id or self.call_id.called:
                self.call_id = reactor.callLater(ADD_THRESHOLD,
                                             self._process_added_udis)
            else:
                self.call_id.reset(ADD_THRESHOLD)
        except (error.AlreadyCalled, error.AlreadyCancelled):
            log.err(None, "Error on _device_added_cb")
            # call has already been fired
            self._cleanup_udis()

            self._transition_to_idle()

    def _dev_removed_cb(self, udi):
        if self.mode == BUSY:
            # we're in the middle of a hotpluggin event and the udis that
            # we just added to self.added_udis are disappearing!
            # whats going on? Some devices such as the Huawei E870 will
            # add some child udis, and will remove them once libusual kicks
            # in, so we need to wait for at most ADD_THRESHOLD seconds
            # since the last removal/add to find out what really got added
            if udi in self.added_udis:
                self.added_udis.remove(udi)
                return

        if udi in self.clients:
            self._unregister_client(udi)
            self.controller.DeviceRemoved(udi)

    def _cleanup_udis(self):
        self.added_udis = []
        if self.call_id and not self.call_id.called:
            self.call_id.cancel()

        self.call_id = None

    def _process_added_udis(self):
        # obtain the parent udis of all the devices with modem capabilities
        parent_udis = self._get_parent_udis()
        # we're only interested on devices not being handled and just added
        not_handled_udis = set(self.clients.keys()) ^ parent_udis
        just_added_udis = not_handled_udis & set(self.added_udis)
        # get devices out of UDIs and register them emitting DeviceAdded
        d = self._get_devices_from_udis(just_added_udis)
        d.addCallback(self._check_if_devices_are_registered)

        # cleanup
        self._cleanup_udis()

    def _get_hso_ports(self, ports):
        dport = cport = None
        BASE = '/sys/class/tty'

        for port in ports:
            name = port.split('/')[-1]
            path = join(BASE, name, 'hsotype')
            if not exists(path):
                continue

            what = get_file_data(path).strip().lower()
            if what == 'modem' and dport is None:
                dport = port
            elif what == 'application' and cport is None:
                cport = port

            if dport and cport:
                break

        return dport, cport

    def _get_child_udis_from_udi(self, udi):
        """Returns the paths of ``udi`` childs and the properties used"""
        device_props = self.get_devices_properties()
        dev_udis = sorted(device_props.keys(), key=len)
        dev_udis2 = dev_udis[:]
        childs = []
        while dev_udis:
            _udi = dev_udis.pop()
            if _udi != udi and 'info.parent' in device_props[_udi]:
                par_udi = device_props[_udi]['info.parent']

                if par_udi == udi or par_udi in childs:
                    childs.append(_udi)

        while dev_udis2:
            _udi = dev_udis2.pop()
            if _udi != udi and 'info.parent' in device_props[_udi]:
                par_udi = device_props[_udi]['info.parent']

                if par_udi == udi or (par_udi in childs and
                                            _udi not in childs):
                    childs.append(_udi)

        return childs, device_props

    def _get_ports_from_udi(self, parent_udi, context=None):
        """Returns all the ports that ``parent_udi`` has registered"""
        if context:
            childs, dp = context
        else:
            childs, dp = self._get_child_udis_from_udi(parent_udi)

        if childs:
            serial_devs = [dp[_udi]['serial.device']
                            for _udi in childs if 'serial.device' in dp[_udi]]
            ports = map(str, set(serial_devs))
            natsort(ports)
            return ports

        raise RuntimeError("Couldn't find any child of device %s" % parent_udi)

    def _get_device_from_info_and_ports(self, info, root_udi, ports,
                                        context=None):
        """Returns a `DevicePlugin` out of ``info`` and ``ports``"""
        plugin = PluginManager.get_plugin_by_vendor_product_id(*info.values())

        if plugin:
            # set its udi
            try:
                plugin.udi = self._get_modem_path(root_udi)
            except RuntimeError, e:
                log.err(e, "Error while getting modem path")
                plugin.udi = root_udi

            plugin.root_udi = root_udi
            # set DBus properties (Modem interface)
            props = plugin.props[consts.MDM_INTFACE]
            props['IpMethod'] = consts.MM_IP_METHOD_PPP
            # XXX: Fix MasterDevice
            props['MasterDevice'] = 'udev:/sys/devices/not/implemented'
            # XXX: Fix CDMA
            props['Type'] = consts.MM_MODEM_TYPE_REV['GSM']
            props['Driver'] = self._get_driver_name(root_udi, context)

            # preprobe stuff
            if hasattr(plugin, 'preprobe_init'):
                # this plugin requires special initialisation before probing
                plugin.preprobe_init(ports, extract_info(info))

            # now get the ports
            ports_need_probe = True
            if props['Driver'] == 'hso':
                # set DBus properties (Modem.Gsm.Hso interface)
                hso_props = plugin.props[consts.HSO_INTFACE]
                net_device = self._get_network_device(root_udi, context)
                hso_props['NetworkDevice'] = net_device
                props['IpMethod'] = consts.MM_IP_METHOD_STATIC
                # XXX: Fix HSO Device
                props['Device'] = 'hso0'
                dport, cport = self._get_hso_ports(ports)
                ports_need_probe = False
                # Fix modem udi path
                modem_udi = self._get_hso_modem_path(plugin.udi)
                if modem_udi:
                    plugin.udi = modem_udi

            elif 'cdc' in props['Driver']:
                # MBM device
                props['IpMethod'] = consts.MM_IP_METHOD_DHCP
                # XXX: Fix MBM Device
                props['Device'] = 'usb0'

            if hasattr(plugin, 'hardcoded_ports'):
                # if the device has the hardcoded_ports attribute that means
                # that it allocates the data and control port in a funky way
                # and thus the indexes are hardcoded.
                dport_idx, cport_idx = plugin.hardcoded_ports
                dport = ports[dport_idx]
                cport = ports[cport_idx] if cport_idx is not None else None
            elif ports_need_probe:
                # the ports were not hardcoded nor was an HSO device
                dport, cport = probe_ports(ports)

            if not dport and not cport:
                # this shouldn't happen
                msg = 'No data port and no control port with ports: %s'
                raise RuntimeError(msg % ports)

            if 'Device' not in props:
                # do not set it again
                props['Device'] = dport.split('/')[-1]

            plugin.ports = Ports(dport, cport)
            return plugin

        raise RuntimeError("Couldn't find a plugin with info %s" % info)


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

    def add_dns_info(self, (dns1, dns2), iface=None):
        """See :meth:`wader.common.interfaces.IOSPlugin.add_dns_info`"""
        name = self.__class__.__name__
        log.err(NotImplementedError,
                "add_dns_info not implemented in plugin %s" % name)

    def delete_dns_info(self, (dns1, dns2), iface=None):
        """See :meth:`wader.common.interfaces.IOSPlugin.delete_dns_info`"""
        name = self.__class__.__name__
        log.err(NotImplementedError,
                "delete_dns_info not implemented in plugin %s" % name)

    def configure_iface(self, iface, ip='', action='up'):
        """See :meth:`wader.common.interfaces.IOSPlugin.configure_iface`"""
        assert action in ['up', 'down']
        if action == 'down':
            args = [iface, action]
        else:
            args = [iface, ip, 'netmask', '255.255.255.255', action]

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
