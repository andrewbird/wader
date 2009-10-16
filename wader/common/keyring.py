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
"""Keyring module for Wader"""

import os
try:
    import cPickle as pickle
except ImportError:
    import pickle

import gobject
import dbus
from dbus.service import Object, BusName, signal

from wader.common.consts import (APP_SLUG_NAME, WADER_KEYRING_SERVICE,
                                 WADER_KEYRING_OBJPATH, WADER_KEYRING_INTFACE,
                                 NM_PASSWD)
from wader.common._gconf import GConfHelper
from wader.contrib.aes import (AESModeOfOperation, append_PKCS7_padding,
                               CBC, SIZE_128)

# this line is required, otherwise gnomekeyring will complain about
# the application name not being set
gobject.set_application_name(APP_SLUG_NAME)

KEYRING_AVAILABLE = True
try:
    import gnomekeyring
except ImportError:
    KEYRING_AVAILABLE = False
else:
    try:
        gnomekeyring.get_default_keyring_sync()
    except gnomekeyring.NoKeyringDaemonError:
        KEYRING_AVAILABLE = False


class KeyringNoMatchError(Exception):
    """Exception raised when there is no match for a keyring request"""


class KeyringInvalidPassword(Exception):
    """Exception raised when the supplied password is invalid"""


class KeyringIsClosed(Exception):
    """
    Exception raised when an operation has been attempted on a closed keyring
    """


_keyring_manager = None


def get_keyring_manager(base_gpath):
    """
    Returns a reference to the :class:`KeyringManager` singleton

    It will use the appropriate keyring backend depending on the system

    :param base_gpath: GConf base path that will be used to store
                       keyring data
    """
    global _keyring_manager
    # if is already instantiated
    if _keyring_manager is not None:
        return _keyring_manager

    if KEYRING_AVAILABLE:
        _keyring_manager = KeyringManager(GnomeKeyring())
        return _keyring_manager

    _keyring_manager = KeyringManager(AESKeyring(base_gpath))
    return _keyring_manager


class KeyringManager(Object):
    """
    I am the keyring manager

    I provide a uniform API over different keyrings
    """

    def __init__(self, keyring):
        name = BusName(WADER_KEYRING_SERVICE, bus=dbus.SystemBus())
        super(KeyringManager, self).__init__(bus_name=name,
                                             object_path=WADER_KEYRING_OBJPATH)
        self.keyring = keyring

        self.open_callbacks = set()

    def _get_keyring_new(self):
        return self.keyring.is_new

    def _get_keyring_open(self):
        return self.keyring.is_open

    is_open = property(_get_keyring_open)
    is_new = property(_get_keyring_new)

    def register_open_callback(self, callback):
        """Registers ``callback`` to be executed upon keyring unlock"""
        self.open_callbacks.add(callback)

    def delete_secret(self, uuid):
        """
        Deletes the secret identified by ``uuid``

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.keyring.is_open:
            return self.keyring.delete(uuid)

        raise KeyringIsClosed()

    def update_secret(self, uuid, conn_id, secrets, update=True):
        """
        Updates secret ``secrets`` in profile ``uuid``

        :param uuid: The uuid of the profile to be updated
        :param conn_id: The id (name) of the profile to be updated
        :param secrets: The secrets
        :params update: Should existing secrets be updated?

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.keyring.is_open:
            ret = self.keyring.update(uuid, conn_id, secrets, update)
            self.keyring.write()
            return ret

        raise KeyringIsClosed()

    def get_secret(self, uuid):
        """
        Returns the secrets associated with ``uuid``

        :param uuid: The UUID of the connection to use
        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.keyring.is_open:
            return self.keyring.get(uuid)

        raise KeyringIsClosed()

    def close(self):
        """
        Cleans up the underlying backend and deletes the cached secrets

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.keyring.is_open:
            return self.keyring.close()

        raise KeyringIsClosed()

    def write(self):
        """
        Writes the changes to the underlying keyring manager

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.keyring.is_open:
            return self.keyring.write()

        raise KeyringIsClosed()

    def open(self, password):
        """
        Opens the keyring using ``password``

        If successful, it will execute all the callbacks registered with
        :meth:`register_open_callback`.

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        self.keyring.open(password)

        for callback in self.open_callbacks:
            callback()

    @signal(WADER_KEYRING_INTFACE, signature="o")
    def KeyNeeded(self, opath):
        pass


class GnomeKeyring(object):
    """I just wrap gnome-keyring"""

    def __init__(self):
        super(GnomeKeyring, self).__init__()
        self.is_new = False
        self.name = gnomekeyring.get_default_keyring_sync()

        if not self.name:
            self.is_new = True
            self.name = 'login'

        try:
            gnomekeyring.create_sync(self.name, None)
        except gnomekeyring.AlreadyExistsError:
            pass

    def _get_is_open(self):
        info = gnomekeyring.get_info_sync(self.name)
        return not info.get_is_locked()

    is_open = property(_get_is_open)

    def open(self, password):
        """See :meth:`KeyringManager.open`"""
        if not self.is_open:
            try:
                gnomekeyring.unlock_sync(self.name, password)
            except gnomekeyring.DeniedError:
                raise KeyringInvalidPassword()

    def close(self):
        """See :meth:`KeyringManager.close`"""
        if self.is_open:
            gnomekeyring.lock_sync(self.name)
        else:
            raise KeyringIsClosed()

    def get(self, uuid):
        """See :meth:`KeyringManager.get_secret`"""
        attrs = {'connection-uuid' : str(uuid)}
        try:
            secrets = gnomekeyring.find_items_sync(
                            gnomekeyring.ITEM_GENERIC_SECRET, attrs)
            return {'gsm' : {NM_PASSWD : secrets[0].secret}}
        except gnomekeyring.NoMatchError:
            msg = "No secrets for connection '%s'"
            raise KeyringNoMatchError(msg % str(uuid))

    def update(self, uuid, conn_id, secrets, update=True):
        """See :meth:`KeyringManager.update_secret`"""
        attrs = {'connection-uuid' : str(uuid), 'setting-name' : 'gsm',
                 'setting-key' : 'password'}

        password = secrets['gsm'][NM_PASSWD]

        text = 'Network secret for %s/%s/%s' % (conn_id, 'gsm', 'password')
        return gnomekeyring.item_create_sync(self.name,
                                             gnomekeyring.ITEM_GENERIC_SECRET,
                                             text, attrs, password, update)

    def delete(self, uuid):
        """See :meth:`KeyringManager.delete_secret`"""
        attrs = {'connection-uuid' : str(uuid)}
        secrets = gnomekeyring.find_items_sync(
                            gnomekeyring.ITEM_GENERIC_SECRET, attrs)
        # we find the secret, and we delete it
        return gnomekeyring.item_delete_sync(self.name, secrets[0].item_id)

    def write(self):
        """See :meth:`KeyringManager.write`"""
        # NOOP
        pass


class AESKeyring(GConfHelper):
    """
    GConf powered keyring

    I will store the secrets encrypted with TripleDES
    """

    def __init__(self, base_gpath):
        super(AESKeyring, self).__init__()

        self.path = os.path.join(base_gpath, 'keyring')
        self.is_open = False
        self.is_new = True
        self._aes = None
        self._iv = [101, 32, 138, 239, 76, 213, 47, 118, 255, 222, 123,
                   176, 106, 134, 98, 92]
        self._key = None

        self._data = None
        self._load_data()

    def _load_data(self):
        if self.client.dir_exists(self.path):
            self.is_new = False

    def open(self, password):
        """See :meth:`KeyringManager.open`"""
        self._aes = AESModeOfOperation()
        self._key = map(ord, append_PKCS7_padding(password))

        if not self.is_new:
            value = self.client.get(os.path.join(self.path, 'data'))
            enc_data = self.get_value(value)
            orig_len = self.client.get_int(os.path.join(self.path, 'orig_len'))

            dict_data = self._aes.decrypt(enc_data, orig_len, CBC, self._key,
                                          SIZE_128, self._iv)
            if not dict_data:
                raise KeyringInvalidPassword()
            try:
                self._data = pickle.loads(dict_data)
            except pickle.UnpicklingError:
                raise KeyringInvalidPassword()
        else:
            self._data = {}

        self.is_open = True

    def close(self):
        """See :meth:`KeyringManager.close`"""
        del self._data
        self.is_open = False

    def get(self, uuid):
        """See :meth:`KeyringManager.get_secret`"""
        if uuid not in self._data:
            raise KeyringNoMatchError()

        return self._data[uuid]

    def update(self, uuid, conn_id, secrets, update=True):
        """See :meth:`KeyringManager.update_secret`"""
        if update:
            self._data[uuid] = secrets

    def delete(self, uuid):
        """See :meth:`KeyringManager.delete_secret`"""
        if uuid not in self._data:
            raise KeyringNoMatchError()

        del self._data[uuid]

    def write(self):
        """See :meth:`KeyringManager.write`"""
        dict_data = pickle.dumps(self._data, protocol=-1)
        mode, orig_len, enc_data = self._aes.encrypt(dict_data, CBC,
                                                     self._key, SIZE_128,
                                                     self._iv)
        self.set_value(os.path.join(self.path, 'data'), enc_data)
        self.set_value(os.path.join(self.path, 'orig_len'), orig_len)
        self.client.suggest_sync()
