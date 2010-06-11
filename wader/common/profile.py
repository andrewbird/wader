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
from __future__ import with_statement

from contextlib import closing
import socket
import time
from uuid import uuid1

import dbus
from dbus.service import BusName, method, signal
from zope.interface import implements
from twisted.python import log

from wader.common._dbus import DelayableDBusObject, delayable
from wader.common.interfaces import IProfile
from wader.common.consts import (WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 MM_NETWORK_BAND_ANY,
                                 MM_ALLOWED_MODE_ANY)
import wader.common.exceptions as ex
from wader.common.provider import NetworkProvider
from wader.common.utils import convert_ip_to_int


class Profile(DelayableDBusObject):
    """I am a group of settings required to dial up"""

    implements(IProfile)

    def __init__(self, opath, props=None):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        DelayableDBusObject.__init__(self, bus_name, opath)

        self.opath = opath
        self.secrets = None
        self.props = {} if props is None else props

    def get_settings(self):
        """Returns the profile settings"""
        raise NotImplementedError("Implement in subclass")

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
        raise NotImplementedError("Implement in subclass")

    def is_good(self):
        """Has this profile been successfully used?"""
        raise NotImplementedError("Implement in subclass")

    def on_open_keyring(self, tag):
        """Callback to be executed when the keyring has been opened"""
        raise NotImplementedError("Implement in subclass")

    def set_secrets(self, tag, secrets):
        """
        Sets or updates the secrets associated with the profile

        :param tag: The section to use
        :param secrets: The new secret to store
        """
        raise NotImplementedError("Implement in subclass")

    def update(self, props):
        """Updates the profile with settings ``props``"""
        raise NotImplementedError("Implement in subclass")

    def remove(self):
        """Removes the profile"""
        raise NotImplementedError("Implement in subclass")

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='', out_signature='a{sa{sv}}')
    def GetSettings(self):
        """See :meth:`get_settings`"""
        return self.get_settings()

    @signal(dbus_interface=WADER_PROFILES_INTFACE,
            signature='os')
    def KeyNeeded(self, conn_path, tag):
        msg = "KeyNeeded emitted for connection: %s tag: %s"
        log.msg(msg % (conn_path, tag))

    @delayable
    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='sasb', out_signature='a{sa{sv}}')
    def GetSecrets(self, tag, hints, ask):

        def ask_user():
            self.GetSecrets.delay_reply()
            self.KeyNeeded(self, tag)

        if ask:
            ask_user()
        else:
            ask = not self.secrets.is_open()
            secrets = self.get_secrets(tag, hints, ask=ask)

            if secrets and tag in secrets:
                return {tag: secrets[tag]}
            elif self.secrets.is_open():
                ask_user()
            else:
                self.secrets.register_open_callback(
                    lambda: self.on_open_keyring(tag))
                # will emit KeyNeeded if on_open_keyring does not return
                # sound secrets
                self.GetSecrets.delay_reply()

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='sa{sv}', out_signature='')
    def SetSecrets(self, tag, secrets):
        """See :meth:`set_secrets`"""
        self.set_secrets(tag, secrets)

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='a{sa{sv}}', out_signature='')
    def Update(self, options):
        """See :meth:`update`"""
        self.update(options)

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='', out_signature='')
    def Delete(self):
        """See :meth:`remove`"""
        log.msg("Delete received")
        self.remove()

    @signal(dbus_interface=WADER_PROFILES_INTFACE, signature='a{sa{sv}}')
    def Updated(self, options):
        log.msg("Updated emitted")

    @signal(dbus_interface=WADER_PROFILES_INTFACE, signature='')
    def Removed(self):
        log.msg("Removed emitted")


class ProfileManager(object):
    """I manage profiles in the system"""

    def __init__(self, backend, arg):
        super(ProfileManager, self).__init__()
        self.backend = backend.get_profile_manager(arg)

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        return self.backend.add_profile(props)

    def get_profile_by_uuid(self, uuid):
        """
        Returns the :class:`Profile` identified by ``uuid``

        :param uuid: The uuid of the profile
        :raise ProfileNotFoundError: If no profile was found
        """
        return self.backend.get_profile_by_uuid(uuid)

    def get_profile_by_object_path(self, opath):
        """Returns a :class:`Profile` out of its object path ``opath``"""
        return self.backend.get_profile_by_object_path(opath)

    def get_profile_options_from_imsi(self, imsi):
        """Generates a new :class:`Profile` from ``imsi``"""
        with closing(NetworkProvider()) as provider:
            network = provider.get_network_by_id(imsi)
            if network:
                # XXX: use the first NetworkOperator object for now
                network = network[0]
                return self.get_profile_options_from_network(network)

            raise ex.ProfileNotFoundError("No profile for IMSI %s" % imsi)

    def get_profile_options_from_network(self, network):
        """Generates a new :class:`Profile` from ``network``"""
        props = {}

        # gsm
        props['gsm'] = {'band': MM_NETWORK_BAND_ANY,
                        'username': network.username,
                        'password': network.password,
                        'network-type': MM_ALLOWED_MODE_ANY,
                        'number': '*99#',
                        'apn': network.apn,
                        'name': 'gsm'}
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

        props['ipv4'] = {'addresses': [],
                         'dns': dns,
                         'ignore-auto-dns': ignore_auto_dns,
                         'method': 'auto',
                         'name': 'ipv4',
                         'routes': []}
        return props

    def get_profiles(self):
        """Returns all the profiles in the system"""
        return self.backend.get_profiles()

    def remove_profile(self, profile):
        """Removes profile ``profile``"""
        return self.backend.remove_profile(profile)

    def update_profile(self, profile, props):
        """Updates ``profile`` with settings ``props``"""
        return self.backend.update_profile(profile, props)
