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
"""Dialer module abstracts the differences between dialers on different OSes"""

from math import floor
from time import time

try:
    from glib import timeout_add_seconds, source_remove
except ImportError:
    from gobject import timeout_add_seconds, source_remove

import dbus
from dbus.service import Object, BusName, method, signal
from zope.interface import implements
from twisted.internet import defer, reactor
from twisted.python import log

from wader.common._dbus import DBusExporterHelper
import wader.common.consts as consts
from wader.common.interfaces import IDialer
from wader.common.oal import osobj
from wader.common.runtime import nm07_present
from wader.common.utils import convert_int_to_ip

CONFIG_DELAY = 3


class DialerConf(object):
    """I contain all the necessary information to connect to Internet"""
    uuid = ""
    apn = None
    username = None
    password = None
    pin = None
    connection = None
    band = None
    network_type = None
    autoconnect = False
    staticdns = False
    dns1 = None
    dns2 = None
    refuse_pap = True
    refuse_chap = True

    def __init__(self, opath):
        super(DialerConf, self).__init__()
        self.opath = opath
        self._from_dbus_path(opath)

    def __repr__(self):
        msg = '<DialerConf instance apn: %s, user: %s, passwd: %s>'
        args = (self.apn, self.username, self.password)
        return msg % args

    def __str__(self):
        return self.__repr__()

    def _get_profile_secrets(self, profile):
        tag, hints, ask = 'gsm', [consts.NM_PASSWD], False
        resp = profile.GetSecrets(tag, hints, ask,
                  dbus_interface=consts.NM_SYSTEM_SETTINGS_SECRETS)

        if not resp:
            # if we don't get secrets without asking, lets try asking
            resp = profile.GetSecrets(tag, hints, True,
                    dbus_interface=consts.NM_SYSTEM_SETTINGS_SECRETS)

        if consts.NM_PASSWD in resp[tag]:
            return resp[tag][consts.NM_PASSWD]

    def _from_dbus_path(self, opath):
        profile = dbus.SystemBus().get_object(consts.WADER_PROFILES_SERVICE,
                                              opath)
        props = profile.GetSettings(
                       dbus_interface=consts.NM_SYSTEM_SETTINGS_CONNECTION)

        self.uuid = props['connection']['uuid']
        self.apn = props['gsm']['apn']
        try:
            self.username = props['gsm']['username']
        except KeyError:
            log.err("no username in profile, asumming '*' can be used")
            self.username = '*'

        if 'autoconnect' in props['connection']:
            self.autoconnect = props['connection']['autoconnect']
        if 'band' in props['gsm']:
            self.band = props['gsm']['band']
        if 'network-type' in props['gsm']:
            self.network_type = props['gsm']['network-type']

        if 'ipv4' in props:
            self.staticdns = props['ipv4'].get('ignore-auto-dns', False)
            if self.staticdns:
                if len(props['ipv4']['dns']):
                    dns1 = props['ipv4']['dns'][0]
                    self.dns1 = convert_int_to_ip(dns1)
                if len(props['ipv4']['dns']) > 1:
                    dns2 = props['ipv4']['dns'][1]
                    self.dns2 = convert_int_to_ip(dns2)
        else:
            self.staticdns = False

        # get authentication options
        if 'ppp' in props:
            # if refuse-{ch,p}ap is not present it means we will use it!
            self.refuse_pap = props['ppp'].get('refuse-pap', False)
            self.refuse_chap = props['ppp'].get('refuse-chap', False)

        # get the secrets
        try:
            self.password = self._get_profile_secrets(profile)
        except:
            log.err()
        else:
            if not self.password:
                if self.username != '*':
                    log.err("No password in profile, yet username is defined")
                else:
                    log.err("no password in profile, assuming '*' can be used")
                    self.password = '*'


class Dialer(Object):
    """
    Base dialer class

    Override me for new OSes
    """

    implements(IDialer)
    config = None
    protocol = None

    def __init__(self, device, opath, ctrl=None):
        self.bus = dbus.SystemBus()
        name = BusName(consts.WADER_DIALUP_SERVICE, bus=self.bus)
        super(Dialer, self).__init__(bus_name=name, object_path=opath)
        self.device = device
        self.opath = opath
        self.ctrl = ctrl
        # iface name
        self.iface = None
        # timeout_add_seconds task ID
        self.__time = 0
        self.__rx_bytes = 0
        self.__tx_bytes = 0
        self.stats_id = None

    def _emit_dial_stats(self):
        stats = self.get_stats()
        self.device.exporter.DialStats(stats)

        # make sure this is repeatedly called
        return True

    def close(self, path=None):
        # remove the emit stats task
        if self.stats_id is not None:
            source_remove(self.stats_id)
            self.stats_id = None
        # remove from DBus bus
        try:
            self.remove_from_connection()
        except LookupError, e:
            log.err(e)

        return path

    def configure(self, config):
        """
        Configures ``self.device`` with ``config``

        This method should perform any necessary actions to connect to
        Internet like generating configuration files, modifying any necessary
        files, etc.

        :param config: `DialerConf` instance
        """

    def connect(self):
        """Connects to Internet"""

    def get_stats(self):
        """
        Returns a tuple with the connection statistics for this dialer

        :return: (in_bytes, out_bytes)
        """
        if self.iface is not None:
            now = time()
            rx_bytes, tx_bytes = osobj.get_iface_stats(self.iface)
            # if any of these three are not 0, it means that this is at
            # least the second time this method is executed, thus we
            # should have cached meaningful data
            if self.__rx_bytes or self.__tx_bytes or self.__time:
                rx_delta = rx_bytes - self.__rx_bytes
                tx_delta = tx_bytes - self.__tx_bytes
                interval = now - self.__time
                raw_rx_rate = int(floor(rx_delta / interval))
                raw_tx_rate = int(floor(tx_delta / interval))
                rx_rate = raw_rx_rate if raw_rx_rate >= 0 else 0
                tx_rate = raw_tx_rate if raw_tx_rate >= 0 else 0
            else:
                # first time this is executed, we cannot reliably compute
                # the rate. It is better to lie just once
                rx_rate = tx_rate = 0

            self.__rx_bytes, self.__tx_bytes = rx_bytes, tx_bytes
            self.__time = now

            return rx_bytes, tx_bytes, rx_rate, tx_rate

    def stop(self):
        """Stops a hung connection attempt"""

    def disconnect(self):
        """Disconnects from Internet"""

    @signal(dbus_interface=consts.WADER_DIALUP_INTFACE, signature='')
    def Connected(self):
        log.msg("emitting Connected signal")

    @signal(dbus_interface=consts.WADER_DIALUP_INTFACE, signature='')
    def Disconnected(self):
        log.msg("emitting Disconnected signal")

    @signal(dbus_interface=consts.WADER_DIALUP_INTFACE, signature='as')
    def InvalidDNS(self, dns):
        log.msg("emitting InvalidDNS(%s)" % dns)


class DialerManager(Object, DBusExporterHelper):
    """
    I am responsible of all dial up operations

    I provide a uniform API to make data calls using different
    dialers on heterogeneous operating systems.
    """

    def __init__(self, ctrl):
        self.bus = dbus.SystemBus()
        name = BusName(consts.WADER_DIALUP_SERVICE, bus=self.bus)
        super(DialerManager, self).__init__(bus_name=name,
                                    object_path=consts.WADER_DIALUP_OBJECT)
        self.index = 0
        # dict with the stablished connections, key is the object path of
        # the connection and the value is the dialer being used.
        self.connections = {}
        # dict with the ongoing connection attempts, key is the device
        # path and the value is the used dialer. The rationale of using
        # the device path and not the connection opath is that the latter
        # is returned when the connection is stablished, while the former
        # is available from the first moment. It has the downer of only
        # being able to stop one connection attempt per device.
        self.connection_attempts = {}
        self.ctrl = ctrl
        self._connect_to_signals()

    def _device_removed_cb(self, udi):
        """Executed when a udi goes away"""
        if udi in self.connections:
            log.msg("Device %s removed! deleting dialer instance" % udi)
            try:
                self.deactivate_connection(udi)
            except KeyError:
                pass

    def _connect_to_signals(self):
        self.bus.add_signal_receiver(self._device_removed_cb,
                                     "DeviceRemoved",
                                     consts.WADER_INTFACE)

    def get_dialer(self, dev_opath, opath):
        """
        Returns an instance of the dialer that will be used to connect

        :param dev_opath: DBus object path of the device to use
        :param opath: DBus object path of the dialer
        """
        from wader.common.dialers.wvdial import WVDialDialer
        from wader.common.dialers.hsolink import HSODialer
        from wader.common.dialers.nm_dialer import NMDialer

        device = self.ctrl.hm.clients[dev_opath]
        if nm07_present():
            klass = NMDialer
        else:
            # NM 0.6.X
            klass = HSODialer if device.dialer == 'hso' else WVDialDialer

        return klass(device, opath, ctrl=self.ctrl)

    def get_next_opath(self):
        """Returns the next free object path"""
        self.index += 1
        return consts.WADER_DIALUP_BASE % self.index

    def configure_radio_parameters(self, device_path, conf):
        """Configures ``device_path`` using ``conf``"""
        if not all([conf.band, conf.network_type]):
            return defer.succeed(True)

        plugin = self.ctrl.hm.clients[device_path]

        deferred = defer.Deferred()

        if conf.band is not None and conf.network_type is None:
            d = plugin.sconn.set_band(conf.band)
        elif conf.band is None and conf.network_type is not None:
            d = plugin.sconn.set_network_mode(conf.network_type)
        else: # conf.band != None and conf.network_type != None
            d = plugin.sconn.set_band(conf.band)
            d.addCallback(lambda _:
                    plugin.sconn.set_network_mode(conf.network_type))

        d.addCallback(lambda _:
                reactor.callLater(CONFIG_DELAY, deferred.callback, True))

        return deferred

    def activate_connection(self, profile_opath, device_opath):
        """
        Start a connection with device ``device_opath`` using ``profile_opath``
        """
        deferred = defer.Deferred()
        conf = DialerConf(profile_opath)
        opath = self.get_next_opath()
        dialer = self.get_dialer(device_opath, opath)
        self.connection_attempts[device_opath] = dialer

        def start_traffic_monitoring(opath):
            dialer.stats_id = timeout_add_seconds(1, dialer._emit_dial_stats)
            # transfer the dialer from connection_attempts dict to connections dict
            self.connections[opath] = dialer
            if device_opath in self.connection_attempts:
                self.connection_attempts.pop(device_opath)
            deferred.callback(opath)

        def after_configuring_device_connect():
            d = dialer.configure(conf)
            d.addCallback(lambda ign: dialer.connect())
            d.addCallback(start_traffic_monitoring)

        if dialer.__class__.__name__ == 'NMDialer':
            after_configuring_device_connect()
        else:
            d = self.configure_radio_parameters(device_opath, conf)
            d.addCallback(lambda ign: reactor.callLater(CONFIG_DELAY,
                                            after_configuring_device_connect))
        return deferred

    def deactivate_connection(self, device_opath):
        """Stops connection of device ``device_opath``"""
        if device_opath in self.connections:
            dialer = self.connections.pop(device_opath)

            d = dialer.disconnect()
            d.addCallback(dialer.close)
            return d

        raise KeyError("Dialup %s not handled" % device_opath)

    def stop_connection(self, device_opath):
        """Stops connection attempt of device ``device_opath``"""
        dialer = self.connection_attempts.pop(device_opath)
        d = dialer.stop()
        d.addCallback(dialer.close)
        return d

    @method(consts.WADER_DIALUP_INTFACE, in_signature='oo', out_signature='o',
            async_callbacks=('async_cb', 'async_eb'))
    def ActivateConnection(self, profile_path, device_path,
                            async_cb, async_eb):
        """See :meth:`DialerManager.activate_connection`"""
        d = self.activate_connection(profile_path, device_path)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE, in_signature='o', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def DeactivateConnection(self, device_path, async_cb, async_eb):
        """See :meth:`DialerManager.deactivate_connection`"""
        d = self.deactivate_connection(device_path)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE, in_signature='o', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def StopConnection(self, device_path, async_cb, async_eb):
        """See :meth:`DialerManager.stop_connection`"""
        d = self.stop_connection(device_path)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE,
            in_signature='o', out_signature='(uu)')
    def GetStats(self, opath):
        """Get the traffic statistics for connection ``opath``"""
        dialer = self.connections[opath]
        return dialer.get_stats()[:2]
