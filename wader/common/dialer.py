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

from gobject import timeout_add_seconds, source_remove
import dbus
from dbus.service import Object, BusName, method, signal
from zope.interface import implements
from twisted.python import log
from twisted.internet import reactor, task
from twisted.internet import defer

from wader.common._dbus import DBusExporterHelper
from wader.common.aterrors import CallIndexError
import wader.common.consts as consts
from wader.common.interfaces import IDialer
from wader.common.oal import get_os_object
from wader.common.utils import convert_int_to_ip


CONFIG_DELAY = RECONNECTION_DELAY = 3
SECRETS_TIMEOUT = 3


class DialerConf(object):
    """I contain all the necessary information to connect to Internet"""
    uuid = ""
    apn = None
    context = None
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

    def __init__(self):
        super(DialerConf, self).__init__()
        self.opath = None

    def __repr__(self):
        msg = '<DialerConf apn: %s, user: %s, passwd: %s>'
        args = (self.apn, self.username, self.password)
        return msg % args

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def get_profile_secrets(profile):
        resp = profile.GetSecrets('gsm', ['password'], False,
                                  timeout=SECRETS_TIMEOUT)
        if not resp:
            # if we don't get secrets without asking, lets try asking
            resp = profile.GetSecrets('gsm', ['password'], True,
                                      timeout=SECRETS_TIMEOUT)

        return resp['gsm']['passwd']

    @classmethod
    def from_dict(cls, settings):
        """Returns a new `:class:DialerConf` out of ``settings``"""
        ret = cls()
        # connection
        ret.uuid = settings['connection']['uuid']
        ret.autoconnect = settings['connection'].get('autoconnect', False)
        # gsm
        ret.apn = settings['gsm']['apn']
        ret.username = settings['gsm'].get('username', '')
        ret.password = settings['gsm'].get('password')
        ret.band = settings['gsm'].get('band')
        ret.network_type = settings['gsm'].get('network-type')
        # ipv4 might not be present
        if 'ipv4' in settings:
            ret.staticdns = settings['ipv4'].get('ignore-auto-dns', False)
            if settings['ipv4'].get('dns'):
                dns1 = settings['ipv4']['dns'][0]
                ret.dns1 = convert_int_to_ip(dns1)
                if len(settings['ipv4']['dns']) > 1:
                    dns2 = settings['ipv4']['dns'][1]
                    ret.dns2 = convert_int_to_ip(dns2)
        # ppp might not be present
        if 'ppp' in settings:
            # get authentication options
            ret.refuse_pap = settings['ppp'].get('refuse-pap', True)
            ret.refuse_chap = settings['ppp'].get('refuse-chap', True)

        return ret

    @classmethod
    def from_dbus_path(cls, opath):
        """Returns a new `:class:DialerConf` out of ``opath``"""
        profile = dbus.SystemBus().get_object(consts.WADER_PROFILES_SERVICE,
                                              opath)
        ret = DialerConf.from_dict(profile.GetSettings())
        ret.opath = opath

        # get the secrets
        try:
            ret.password = DialerConf.get_profile_secrets(profile)
        except Exception, e:
            log.err("Error fetching profile password, "
                    "setting password to ''. Reason: %s" % e)
            ret.password = ''

        return ret


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
        except LookupError:
            # it's safe to ignore this exception
            pass

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
            rx_bytes, tx_bytes = get_os_object().get_iface_stats(self.iface)
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
        self._client_count = -1
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
        # dict with the cached connections, key is the device path and the
        # value is the used configuration. This is used to save the state
        # of previous connections interrupted by a MMS connection.
        self.connection_state = {}
        self.ctrl = ctrl
        self._connect_to_signals()

    def _device_removed_cb(self, opath):
        """Executed when a device goes away"""
        if opath in self.connections:
            log.msg("Device %s removed! deleting dialer instance" % opath)
            try:
                self.deactivate_connection(opath)
            except KeyError:
                pass

    def _connect_to_signals(self):
        self.bus.add_signal_receiver(self._device_removed_cb,
                                     "DeviceRemoved",
                                     consts.WADER_INTFACE)

    def get_dialer(self, dev_opath, opath, plain=False):
        """
        Returns an instance of the dialer that will be used to connect

        :param dev_opath: DBus object path of the device to use
        :param opath: DBus object path of the dialer
        """
        from wader.common.backends import get_backend, plain_backend
        device = self.ctrl.hm.clients[dev_opath]

        if plain:
            dialer_klass = plain_backend.get_dialer_klass(device)
        else:
            dialer_klass = get_backend().get_dialer_klass(device)

        return dialer_klass(device, opath, ctrl=self.ctrl)

    def get_next_opath(self):
        """Returns the next free object path"""
        self._client_count += 1
        return consts.WADER_DIALUP_BASE % self._client_count

    def activate_connection(self, profile_opath, device_opath):
        """
        Start a connection with device ``device_opath`` using ``profile_opath``
        """
        conf = DialerConf.from_dbus_path(profile_opath)
        # build dialer
        dialer = self.get_dialer(device_opath, self.get_next_opath())
        return self.do_activate_connection(conf, dialer)

    def do_activate_connection(self, conf, dialer):
        device_opath = dialer.device.opath
        self.connection_attempts[device_opath] = dialer, conf
        device = self.ctrl.hm.clients[device_opath]

        conn_id = device.sconn.state_dict.get('conn_id')
        if conn_id is None:
            raise CallIndexError("conn_id is None")

        conf.context = conn_id

        def start_traffic_monitoring(conn_opath):
            dialer.stats_id = timeout_add_seconds(1, dialer._emit_dial_stats)
            # transfer the dialer from connection_attempts to connections dict
            self.connections[conn_opath] = dialer, conf
            if device_opath in self.connection_attempts:
                self.connection_attempts.pop(device_opath)

            # announce that a new connection is active
            self.ConnectionChanged(conn_opath, True)
            return conn_opath

        d = dialer.configure(conf)
        d.addCallback(lambda ign: dialer.connect())
        d.addCallback(start_traffic_monitoring)
        return d

    def activate_mms_connection(self, settings, device_opath):
        """
        Starts a MMS connection with device ``device_opath`` using ``settings``
        """
        if device_opath in self.connection_state:
            # this should never happen
            log.err("activate_mms_connection: internal error, "
                    "device_opath is already stored")
            # XXX: What exception should be used here?
            return defer.fail()

        # handle the case where a connection is already stablished
        for conn_opath, (dialer, conf) in self.connections.items():
            if dialer.device.opath == device_opath:
                self.connection_state[device_opath] = dialer, conf
                d = dialer.disconnect()
                d.addCallback(dialer.close)
                break
        else:
            # handle the case where a connection attempt is going on
            if device_opath in self.connection_attempts:
                dialer, conf = self.connection_attempts[device_opath]
                self.connection_state[device_opath] = dialer, conf
                d = dialer.disconnect()
                d.addCallback(dialer.close)
            else:
                # if there was no connection/conn attempt, there's nothing to handle
                d = defer.succeed(True)

        def prepare_connection_and_activate(_):
            conf = DialerConf.from_dict(settings)
            # we want the plain dialer, pass True
            dialer = self.get_dialer(device_opath, self.get_next_opath(), True)
            return task.deferLater(reactor, RECONNECTION_DELAY,
                                   self.do_activate_connection, conf, dialer)

        d.addCallback(prepare_connection_and_activate)
        return d

    def deactivate_connection(self, conn_opath):
        """Stops connection of device ``device_opath``"""
        if conn_opath not in self.connections:
            raise KeyError("Dialup %s not handled" % conn_opath)

        dialer, _ = self.connections.pop(conn_opath)

        def on_disconnect(opath):
            self.ConnectionChanged(conn_opath, False)
            return dialer.close(opath)

        d = dialer.disconnect()
        d.addCallback(on_disconnect)

        device_opath = dialer.device.opath
        if device_opath not in self.connection_state:
            return d

        # there was a connection going on before, restore it
        dialer, conf = self.connection_state.pop(device_opath)
        return task.deferLater(reactor, RECONNECTION_DELAY,
                               self.do_activate_connection, conf, dialer)

    def stop_connection(self, device_opath):
        """Stops connection attempt of device ``device_opath``"""
        dialer, _ = self.connection_attempts.pop(device_opath)
        d = dialer.stop()
        d.addCallback(dialer.close)
        return d

    @method(consts.WADER_DIALUP_INTFACE, in_signature='oo', out_signature='o',
            async_callbacks=('async_cb', 'async_eb'))
    def ActivateConnection(self, profile_path, device_opath,
                            async_cb, async_eb):
        """See :meth:`DialerManager.activate_connection`"""
        d = self.activate_connection(profile_path, device_opath)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE, in_signature='a{sv}o',
            out_signature='o', async_callbacks=('async_cb', 'async_eb'))
    def ActivateMmsConnection(self, settings, device_opath, async_cb, async_eb):
        """See :meth:`DialerManager.activate_mms_connection`"""
        d = self.activate_mms_connection(settings, device_opath)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE, in_signature='o', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def DeactivateConnection(self, device_opath, async_cb, async_eb):
        """See :meth:`DialerManager.deactivate_connection`"""
        d = self.deactivate_connection(device_opath)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE, in_signature='o', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def StopConnection(self, device_opath, async_cb, async_eb):
        """See :meth:`DialerManager.stop_connection`"""
        d = self.stop_connection(device_opath)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @signal(consts.WADER_DIALUP_INTFACE, signature='ob')
    def ConnectionChanged(self, conn_opath, active):
        log.msg("ConnectionChanged(%s, %s)" % (conn_opath, active))
