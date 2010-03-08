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

import dbus
from dbus.service import Object, BusName, signal

from wader.common.consts import (WADER_KEYRING_SERVICE,
                                 WADER_KEYRING_OBJPATH, WADER_KEYRING_INTFACE)


class KeyringNoMatchError(Exception):
    """Exception raised when there is no match for a keyring request"""


class KeyringInvalidPassword(Exception):
    """Exception raised when the supplied password is invalid"""


class KeyringIsClosed(Exception):
    """
    Exception raised when an operation has been attempted on a closed keyring
    """


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

    def is_new(self):
        return self.keyring.is_new()

    def is_open(self):
        return self.keyring.is_open()

    def register_open_callback(self, callback):
        """Registers ``callback`` to be executed upon keyring unlock"""
        self.open_callbacks.add(callback)

    def delete_secret(self, uuid):
        """
        Deletes the secret identified by ``uuid``

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.is_open():
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
        if self.is_open():
            return self.keyring.update(uuid, conn_id, secrets, update)

        raise KeyringIsClosed()

    def get_secrets(self, uuid):
        """
        Returns the secrets associated with ``uuid``

        :param uuid: The UUID of the connection to use
        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.is_open():
            return self.keyring.get(uuid)

        raise KeyringIsClosed()

    def close(self):
        """
        Cleans up the underlying backend and deletes the cached secrets

        :raise KeyringIsClosed: When the underlying keyring is closed
        """
        if self.is_open():
            return self.keyring.close()

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
