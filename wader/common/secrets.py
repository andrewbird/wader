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
Classes that mediate access to the secrets. This is done through the
:mod:`~wader.common.keyring` module.
"""

from wader.common import keyring


class ProfileSecrets(object):
    """
    I mediate access to the secrets associated with a profile

    I provide a uniform API to interact with the different keyrings.
    """

    def __init__(self, connection, base_gpath):
        self.connection = connection
        self.uuid = connection.get_settings()['connection']['uuid']
        self.manager = keyring.get_keyring_manager(base_gpath)
        self.temporal_secrets = {}

    def get(self, ask=True):
        """
        Returns the secrets associated with the profile

        :param ask: Should we ask the user if the keyring is closed?
        """
        if self.manager.is_open:
            try:
                return self.manager.get_secret(self.uuid)
            except keyring.KeyringNoMatchError:
                # None signals that something went wrong
                return None
            else:
                if self.temporal_secrets:
                    self.update(self.temporal_secrets, False)
                    return self.temporal_secrets
                else:
                    return {}
        else:
            if ask:
                self.manager.KeyNeeded(self.connection)

            return self.temporal_secrets

    def update(self, secrets, ask=False):
        """
        Updates the secrets associated with the profile

        :param secrets: The new password to use
        :param ask: Should we ask the user if the keyring is closed?
        """
        _id = self.connection.get_settings()['connection']['id']
        if self.manager.is_open:
            self.manager.update_secret(self.uuid, _id, secrets)
        else:
            if ask:
                self.manager.KeyNeeded(self.connection)
                self.register_open_callback(lambda:
                        self.manager.update_secret(self.uuid, _id,
                                                  self.temporal_secrets))

            self.temporal_secrets.update(secrets)

    def open(self, password):
        """Opens the keyring backend using ``password``"""
        self.manager.open(password)

    def clean(self):
        """Cleans up the profile secrets"""
        if self.manager.is_open:
            self.manager.delete_secret(self.uuid)
            self.manager.write()

        self.temporal_secrets = {}

    def is_using_keyring(self):
        return self.manager.is_open

    def register_open_callback(self, callback):
        """Registers ``callback`` to be executed when the keyring is open"""
        self.manager.register_open_callback(callback)
