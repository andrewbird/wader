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

        self.staticdns = props['ipv4']['ignore-auto-dns']
        if self.staticdns:
            if len(props['ipv4']['dns']):
                dns1 = props['ipv4']['dns'][0]
                self.dns1 = convert_int_to_ip(dns1)
            if len(props['ipv4']['dns']) > 1:
                dns2 = props['ipv4']['dns'][1]
                self.dns2 = convert_int_to_ip(dns2)

        # finally, get the secrets
        try:
            self.password = self._get_profile_secrets(profile)
        except:
            log.err()
        else:
            if not self.password:
                if self.username != '*':
                    log.err("No password in profile, yet username is defined")
                else:
                    log.err("no password in profile, asumming '*' can be used")
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
        self.opath = opath
        self.device = device
        self.ctrl = ctrl

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
        self.dialers = {}
        self.ctrl = ctrl
        self._connect_to_signals()

    def _device_removed_cb(self, udi):
        """Executed when a udi goes away"""
        if udi in self.dialers:
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
        if nm07_present:
            dialer_klass = NMDialer
        else:
            # NM 0.6.X
            dialer_klass = HSODialer if device.dialer == 'hso' else WVDialDialer

        return dialer_klass(device, opath, ctrl=self.ctrl)

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

        def after_configuring_device_connect():
            self.dialers[opath] = dialer

            d = defer.maybeDeferred(dialer.configure, conf)
            d.addCallback(lambda ign: dialer.connect())
            d.addErrback(log.err)
            d.chainDeferred(deferred)

        if dialer.__class__.__name__ == 'NMDialer':
            after_configuring_device_connect()
        else:
            d = self.configure_radio_parameters(device_opath, conf)
            d.addCallback(lambda ign: reactor.callLater(CONFIG_DELAY,
                                            after_configuring_device_connect))
        return deferred

    def deactivate_connection(self, device_path):
        """Stops connection of device ``device_path``"""
        if device_path in self.dialers:
            dialer = self.dialers[device_path]
            d = dialer.disconnect()
            def unexport_dialer(path):
                try:
                    dialer.remove_from_connection()
                except LookupError, e:
                    log.err(e)

                return path

            d.addCallback(unexport_dialer)
            return d

        raise KeyError("Dialup %s not handled" % device_path)

    def stop_connection(self, device_path):
        """Stops connection attempt of device ``device_path``"""
        if device_path not in self.dialers:
            raise KeyError("Dialup %s not handled" % device_path)

        dialer = self.dialers[device_path]
        return dialer.stop()

    def get_stats(self, device_path):
        """Get the traffic statistics for device ``device_path``"""
        dialer = self.dialers[device_path]
        return osobj.get_iface_stats(dialer.iface)

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
        try:
            d = self.stop_connection(device_path)
        except KeyError:
            d = defer.succeed(True)

        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(consts.WADER_DIALUP_INTFACE,
            in_signature='o', out_signature='(uu)')
    def GetStats(self, device_path):
        """See :meth:`DialerManager.get_stats`"""
        return self.get_stats(device_path)

