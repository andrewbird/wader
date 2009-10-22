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
"""
Profile-related classes

A profile, also known as a connection in NM-lingo, is a group of
settings to be used to dial up. This group of classes should be used
from the user session, that is why they are defined and not instantiated.
"""

from collections import defaultdict
import os
import time
from uuid import uuid1
import socket

import dbus
from dbus.service import BusName, Object, method, signal
import gconf
from twisted.python import log

from wader.common._dbus import DelayableDBusObject, delayable
from wader.common._gconf import GConfHelper
from wader.common.consts import (NM_USER_SETTINGS, NM_SYSTEM_SETTINGS_OBJ,
                                 NM_SYSTEM_SETTINGS,
                                 NM_SYSTEM_SETTINGS_SECRETS,
                                 NM_SYSTEM_SETTINGS_CONNECTION,
                                 GCONF_PROFILES_BASE,
                                 MM_SYSTEM_SETTINGS_PATH,
                                 WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH)
import wader.common.exceptions as ex
from wader.common.secrets import ProfileSecrets
from wader.common.utils import (convert_ip_to_int, patch_list_signature,
                                convert_int_to_uint)
from wader.common.provider import NetworkProvider


class Profile(GConfHelper, DelayableDBusObject):
    """I am a group of settings required to dial up"""

    def __init__(self, opath, gpath, secrets_gpath, props):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        GConfHelper.__init__(self)
        DelayableDBusObject.__init__(self, bus_name, opath)

        self.opath = opath
        self.gpath = gpath
        self.props = props

        self.secrets = ProfileSecrets(self, secrets_gpath)

    def _write(self, props):
        for key, value in props.iteritems():
            new_path = os.path.join(self.gpath, key)
            self.set_value(new_path, value)

        self.client.suggest_sync()

    def _load_info(self):
        self.props = {}

        if self.client.dir_exists(self.gpath):
            self._load_dir(self.gpath, self.props)

        if 'dns' in self.props['ipv4']:
            dns = map(convert_int_to_uint, self.props['ipv4']['dns'])
            self.props['ipv4']['dns'] = dns

    def _load_dir(self, directory, info):
        entries = self.client.all_entries(directory)
        for entry in entries:
            key = os.path.basename(entry.key)
            info[key] = self.get_value(entry.value)

        dirs = self.client.all_dirs(directory)
        for _dir in dirs:
            dirname = os.path.basename(_dir)
            info[dirname] = {}
            self._load_dir(_dir, info[dirname])

    def get_settings(self):
        """Returns the profile settings"""
        return patch_list_signature(self.props.copy())

    def get_secrets(self, tag, hints=None, ask=True):
        """
        Returns the secrets associated with the profile

        :param tag: The section to use
        :param hints: what specific setting are we interested in
        :param ask: Should we ask the user if there is no secret?
        """
        secrets = self.secrets.get(ask)
        if secrets:
            return secrets
        else:
            return {}

    def get_timestamp(self):
        """Returns the last time this profile was used"""
        try:
            return self.get_settings()['connection']['timestamp']
        except KeyError:
            return None

    def is_good(self):
        """Has this profile been successfully used?"""
        return bool(self.get_timestamp())

    def on_open_keyring(self, tag):
        """Callback to be executed when the keyring has been opened"""
        secrets = self.secrets.get()
        if secrets:
            self.GetSecrets.reply(self, result=(secrets,))
        else:
            self.KeyNeeded(self, tag)

    def set_secrets(self, tag, secrets):
        """
        Sets or updates the secrets associated with the profile

        :param tag: The section to use
        :param secrets: The new secret to store
        """
        self.secrets.update(secrets)
        self.GetSecrets.reply(self, result=(secrets,))

    def update(self, props):
        """Updates the profile with settings ``props``"""
        self._write(props)
        self._load_info()

        self.Updated(patch_list_signature(self.props))

    def remove(self):
        """Removes the profile"""
        self.client.recursive_unset(self.gpath,
                                     gconf.UNSET_INCLUDING_SCHEMA_NAMES)
        # emit Removed and unexport from DBus
        self.Removed()
        self.remove_from_connection()

    @method(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            in_signature='', out_signature='a{sa{sv}}')
    def GetSettings(self):
        """See :meth:`get_settings`"""
        return self.get_settings()

    @signal(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            signature='os')
    def KeyNeeded(self, conn_path, tag):
        msg = "KeyNeeded emitted for connection: %s tag: %s"
        log.msg(msg % (conn_path, tag))

    @delayable
    @method(dbus_interface=NM_SYSTEM_SETTINGS_SECRETS,
            in_signature='sasb', out_signature='a{sa{sv}}')
    def GetSecrets(self, tag, hints, ask):

        def ask_user():
            self.GetSecrets.delay_reply()
            self.KeyNeeded(self, tag)

        if ask:
            ask_user()
        else:
            if self.secrets.is_using_keyring():
                secrets = self.get_secrets(tag, hints, ask=False)
            else:
                secrets = self.get_secrets(tag, hints, ask=True)

            if secrets and tag in secrets:
                return secrets
            elif self.secrets.is_using_keyring():
                ask_user()
            else:
                self.secrets.register_open_callback(
                    lambda: self.on_open_keyring(tag))
                # will emit KeyNeeded if on_open_keyring does not return
                # sound secrets
                self.GetSecrets.delay_reply()

    @method(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            in_signature='sa{sv}', out_signature='')
    def SetSecrets(self, tag, secrets):
        """See :meth:`set_secrets`"""
        self.set_secrets(tag, secrets)

    @method(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            in_signature='a{sa{sv}}', out_signature='')
    def Update(self, options):
        """See :meth:`update`"""
        self.update(options)

    @method(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            in_signature='', out_signature='')
    def Delete(self):
        """See :meth:`remove`"""
        log.msg("Delete received")
        self.remove()

    @signal(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            signature='a{sa{sv}}')
    def Updated(self, options):
        log.msg("Updated emitted")

    @signal(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION,
            signature='')
    def Removed(self):
        log.msg("Removed emitted")


class ProfileManager(Object, GConfHelper):
    """I manage profiles in the system"""

    def __init__(self, gpath):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        Object.__init__(self, bus_name, WADER_PROFILES_OBJPATH)
        GConfHelper.__init__(self)

        self.gpath = gpath
        self.profiles = {}
        self.nm_profiles = {}
        self.nm_manager = None
        self.index = 0

        self._init_nm_manager()

    def _init_nm_manager(self):
        try:
            obj = self.bus.get_object(NM_USER_SETTINGS, NM_SYSTEM_SETTINGS_OBJ)
            self.nm_manager = dbus.Interface(obj, NM_SYSTEM_SETTINGS)
        except dbus.DBusException, e:
            log.err(e, "nm-applet seems to be not around")
            # XXX: handle the case where nm-applet is not around
        else:
            # connect to signals
            self._connect_to_signals()
            # cache existing profiles
            for opath in self.nm_manager.ListConnections():
                self._on_new_nm_profile(opath)

    def _connect_to_signals(self):
        self.nm_manager.connect_to_signal("NewConnection",
                       self._on_new_nm_profile, NM_SYSTEM_SETTINGS)

    def nm_is_available(self):
        return self.nm_manager is not None

    def _on_new_nm_profile(self, opath):
        obj = self.bus.get_object(NM_USER_SETTINGS, opath)
        props = obj.GetSettings(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION)
        if 'gsm' in props:
            self._add_nm_profile(obj, props)

    def _add_nm_profile(self, obj, props):
        uuid = props['connection']['uuid']
        assert uuid not in self.nm_profiles, "Adding twice the same profile?"
        self.nm_profiles[uuid] = obj

        # handle when a NM profile has been externally added
        if uuid not in self.profiles:
            try:
                profile = self._get_profile_from_nm_connection(uuid)
            except ex.ProfileNotFoundError:
                log.msg("Removing non existing NM profile %s" % uuid)
                del self.nm_profiles[uuid]
            else:
                self.profiles[uuid] = profile
                self.NewConnection(profile.opath)

    def _get_next_dbus_opath(self):
        self.index += 1
        return os.path.join(MM_SYSTEM_SETTINGS_PATH, str(self.index))

    def _get_next_free_gpath(self):
        """Returns the next unused slot of /system/networking/connections"""
        all_dirs = list(self.client.all_dirs(GCONF_PROFILES_BASE))
        if not all_dirs:
            index = 0
        else:
            dirs = sorted(map(int, [_dir.split('/')[-1] for _dir in all_dirs]))
            index = dirs[-1] + 1

        return os.path.join(GCONF_PROFILES_BASE, str(index))

    def _get_profile_from_nm_connection(self, uuid):
        for gpath in self.client.all_dirs(GCONF_PROFILES_BASE):
            # filter out wlan connections
            if self.client.dir_exists(os.path.join(gpath, 'gsm')):
                path = os.path.join(gpath, 'connection', 'uuid')
                value = self.client.get(path)
                if value and uuid == self.get_value(value):
                    return self._get_profile_from_gconf_path(gpath)

        msg = "NM profile identified by uuid %s could not be found"
        raise ex.ProfileNotFoundError(msg % uuid)

    def _get_profile_from_gconf_path(self, gconf_path):
        props = defaultdict(dict)
        for path in self.client.all_dirs(gconf_path):
            for entry in self.client.all_entries(path):
                section, key = entry.get_key().split('/')[-2:]
                props[section][key] = self.get_value(entry.get_value())

        return Profile(self._get_next_dbus_opath(), gconf_path,
                       self.gpath, dict(props))

    def _do_set_profile(self, path, props):
        if not props['ipv4']['ignore-auto-dns']:
            props['ipv4']['dns'] = []

        for key in props:
            for name in props[key]:
                value = props[key][name]
                _path = os.path.join(path, key, name)

                self.set_value(_path, value)

        self.client.suggest_sync()

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        gconf_path = self._get_next_free_gpath()
        uuid = props['connection']['uuid']

        self._do_set_profile(gconf_path, props)
        profile = Profile(self._get_next_dbus_opath(), gconf_path,
                          self.gpath, props)
        self.profiles[uuid] = profile
        self.NewConnection(profile.opath)

    def get_profile_by_uuid(self, uuid):
        """
        Returns the :class:`Profile` identified by ``uuid``

        :param uuid: The uuid of the profile
        :raise ProfileNotFoundError: If no profile was found
        """
        if not self.profiles:
            # initialise just in case
            self.get_profiles()

        try:
            return self.profiles[uuid]
        except KeyError:
            raise ex.ProfileNotFoundError("No profile with uuid %s" % uuid)

    def get_profile_by_object_path(self, opath):
        """Returns a :class:`Profile` out of its object path ``opath``"""
        for profile in self.profiles.values():
            if profile.opath == opath:
                return profile

        raise ex.ProfileNotFoundError("No profile with object path %s" % opath)

    def get_profile_options_from_imsi(self, imsi):
        """Generates a new :class:`Profile` from ``imsi``"""
        provider = NetworkProvider()
        network = provider.get_network_by_id(imsi)
        provider.close()

        if not network:
            raise ex.ProfileNotFoundError("No profile for IMSI %s" % imsi)

        # XXX: use the first NetworkOperator object for now
        network = network[0]

        props = {}

        # gsm
        props['gsm'] = {'band' : 0,
                        'username' : network.username,
                        'password' : network.password,
                        'network-type' : 0,
                        'number' : '*99#',
                        'apn' : network.apn,
                        'name' : 'gsm'}
        # ppp
        props['ppp'] = dict(name='ppp')
        # serial
        props['serial'] = dict(baud=115200,
                              name='serial')
        # connection
        props['connection'] = dict(id=network.name,
                                  autoconnect=False,
                                  timestamp=time.time(),
                                  type='gsm',
                                  name='connection',
                                  uuid=str(uuid1()))

        ignore_auto_dns = True
        try:
            dns = map(convert_ip_to_int, [network.dns1, network.dns2])
        except (socket.error, TypeError):
            # if the DNS are None, this will raise TypeError
            ignore_auto_dns = False
            dns = []

        props['ipv4'] = {'addresses' : [],
                         'dns' : dns,
                         'ignore-auto-dns': ignore_auto_dns,
                         'method' : 'auto',
                         'name' : 'ipv4',
                         'routes' : []}
        return props

    def get_profiles(self):
        """Returns all the profiles in the system"""
        if not self.profiles:
            for path in self.client.all_dirs(GCONF_PROFILES_BASE):
                # filter out wlan connections
                if self.client.dir_exists(os.path.join(path, 'gsm')):
                    profile = self._get_profile_from_gconf_path(path)
                    uuid = profile.get_settings()['connection']['uuid']
                    self.profiles[uuid] = profile

        return self.profiles.values()

    def remove_profile(self, profile):
        """Removes profile ``profile``"""
        uuid = profile.get_settings()['connection']['uuid']
        assert uuid in self.profiles, "Removing a non-existent profile?"

        self.profiles[uuid].remove()
        del self.profiles[uuid]

        # as NetworkManager listens for GConf-DBus signals, we don't need
        # to manually sync it
        if uuid in self.nm_profiles:
            del self.nm_profiles[uuid]

    def update_profile(self, profile, props):
        """Updates ``profile`` with settings ``props``"""
        uuid = profile.get_settings()['connection']['uuid']
        assert uuid in self.profiles, "Updating a non-existent profile?"

        _profile = self.profiles[uuid]
        _profile.update(patch_list_signature(props))

        if uuid in self.nm_profiles:
            obj = self.nm_profiles[uuid]
            obj.Update(patch_list_signature(props),
                       dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION)

    @signal(dbus_interface=WADER_PROFILES_INTFACE, signature='o')
    def NewConnection(self, opath):
        pass

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='s', out_signature='o')
    def GetNMObjectPath(self, uuid):
        """Returns the object path of the connection referred by ``uuid``"""
        if uuid not in self.nm_profiles:
            raise KeyError("Unknown uuid: %s" % uuid)

        profile = self.nm_profiles[uuid]
        return profile.__dbus_object_path__
