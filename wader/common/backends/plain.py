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
from __future__ import with_statement

import errno
import pickle
from cStringIO import StringIO
import os
from signal import SIGKILL

import dbus
from dbus.service import signal, Object, BusName
from twisted.python import log
from zope.interface import implements

from wader.common.aes import decryptData, encryptData
from wader.common.consts import (WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH,
                                 MM_SYSTEM_SETTINGS_PATH)
import wader.common.exceptions as ex
from wader.common.interfaces import IBackend, IProfileManagerBackend
from wader.common.keyring import (KeyringManager, KeyringInvalidPassword,
                                  KeyringIsClosed, KeyringNoMatchError)
from wader.common.profile import Profile
from wader.common.secrets import ProfileSecrets
from wader.common.utils import patch_list_signature


def proc_running(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None

    if pid <= 1:
        return False    # No killing of process group members or all of init's
                        # children
    try:
        os.kill(pid, 0)
    except OSError, err:
        if err.errno == errno.ESRCH:
            return False
        elif err.errno == errno.EPERM:
            return pid
        else:
            return None  # Unknown error
    else:
        return pid


def signal_process(name, pid, signal):
    pid = proc_running(pid)
    if not pid:
        log.msg('wvdial: "%s" process (%s) already exited' %
                (name, str(pid)))
        return False

    log.msg('wvdial: "%s" process (%s) will be sent %s' %
                (name, str(pid), signal))
    try:
        os.kill(pid, SIGKILL)
    except OSError, err:
        if err.errno == errno.ESRCH:
            log.msg('wvdial: "%s" process (%s) not found' %
                (name, str(pid)))
        elif err.errno == errno.EPERM:
            log.msg('wvdial: "%s" process (%s) permission denied' %
                (name, str(pid)))
        else:
            log.msg('wvdial: "%s" process exit "%s"' % (name, str(err)))

    return True  # signal was sent


class PlainProfile(Profile):
    """I am a group of settings required to dial up"""

    def __init__(self, opath, path, secrets_path, props=None):
        super(PlainProfile, self).__init__(opath)
        self.path = path
        self.secrets_path = secrets_path
        self.props = props
        self.secrets = None
        self._init()

    def _init(self):
        if self.props is None:
            # created with "from_path"
            self.props = pickle.load(open(self.path))
        else:
            # regular constructor with properties
            self._write()

        from wader.common.backends import get_backend
        keyring = get_backend().get_keyring(self.secrets_path)
        self.secrets = ProfileSecrets(self, keyring)

    def _write(self):
        with open(self.path, 'w') as configfile:
            pickle.dump(self.props, configfile, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_path(cls, opath, path, secrets_path):
        return cls(opath, path, secrets_path)

    def get_settings(self):
        """Returns the profile settings"""
        return patch_list_signature(self.props)

    def get_secrets(self, tag, hints=None, ask=True):
        """
        Returns the secrets associated with the profile

        :param tag: The section to use
        :param hints: what specific setting are we interested in
        :param ask: Should we ask the user if there is no secret?
        """
        return self.secrets.get()

    def get_timestamp(self):
        """Returns the last time this profile was used"""
        return self.props['connection'].get('timestamp', 0)

    def is_good(self):
        """Has this profile been successfully used?"""
        return bool(self.get_timestamp())

    def on_open_keyring(self, tag):
        """Callback to be executed when the keyring has been opened"""
        secrets = self.secrets.get(tag)
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
        self.props = props
        self._write()
        # emit the signal
        self.Updated(patch_list_signature(props))

    def remove(self):
        """Removes the profile"""
        os.unlink(self.path)

        # emit Removed and unexport from DBus
        self.Removed()
        self.remove_from_connection()


class PlainProfileManager(Object):
    """I manage profiles in the system"""

    implements(IProfileManagerBackend)

    def __init__(self, base_path):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        super(PlainProfileManager, self).__init__(bus_name,
                                               WADER_PROFILES_OBJPATH)
        self.profiles = {}
        self.index = -1
        self.base_path = base_path
        self.profiles_path = os.path.join(base_path, 'profiles')
        self.secrets_path = os.path.join(base_path, 'secrets')
        self._init()

    def _init(self):
        # check that the profiles path exists and create it otherwise
        if not os.path.exists(self.profiles_path):
            os.makedirs(self.profiles_path, mode=0700)

        # now load the profiles
        for uuid in os.listdir(self.profiles_path):
            path = os.path.join(self.profiles_path, uuid)
            profile = PlainProfile.from_path(self.get_next_dbus_opath(),
                                             path, self.secrets_path)
            self.profiles[uuid] = profile

    def get_next_dbus_opath(self):
        self.index += 1
        return os.path.join(MM_SYSTEM_SETTINGS_PATH, str(self.index))

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        uuid = props['connection']['uuid']
        path = os.path.join(self.profiles_path, uuid)
        if os.path.exists(path):
            raise ValueError("Profile with uuid %s already exists" % uuid)

        profile = PlainProfile(self.get_next_dbus_opath(), path,
                               self.secrets_path, props=props)
        self.profiles[uuid] = profile

        self.NewConnection(profile.opath)

    def get_profile_by_uuid(self, uuid):
        """
        Returns the :class:`Profile` identified by ``uuid``

        :param uuid: The uuid of the profile
        :raise ProfileNotFoundError: If no profile was found
        """
        try:
            return self.profiles[uuid]
        except KeyError:
            raise ex.ProfileNotFoundError("No profile with uuid %s" % uuid)

    def get_profile_by_object_path(self, opath):
        """Returns a :class:`Profile` out of its object path ``opath``"""
        for profile in self.profiles.values():
            if profile.opath == opath:
                return profile

        raise ex.ProfileNotFoundError("No profile with opath %s" % opath)

    def get_profiles(self):
        """Returns all the profiles in the system"""
        return self.profiles.values()

    def remove_profile(self, profile):
        """Removes profile ``profile``"""
        uuid = profile.get_settings()['connection']['uuid']
        profile = self.get_profile_by_uuid(uuid)
        self.profiles[uuid].remove()
        del self.profiles[uuid]

    def update_profile(self, profile, props):
        """Updates ``profile`` with settings ``props``"""
        uuid = profile.get_settings()['connection']['uuid']
        profile = self.get_profile_by_uuid(uuid)
        profile.update(props)

    @signal(dbus_interface=WADER_PROFILES_INTFACE, signature='o')
    def NewConnection(self, opath):
        pass


def transform_passwd(passwd):
    valid_lengths = [16, 24, 32]
    for l in valid_lengths:
        if l >= len(passwd):
            return passwd.zfill(l)

    msg = "Password '%s' is too long, max length is 32 chars"
    raise KeyringInvalidPassword(msg % passwd)


class PlainKeyring(object):

    def __init__(self, secrets_path):
        self.secrets_path = secrets_path
        self.key = None
        self._is_open = False
        self._is_new = True
        self._init()

    def _init(self):
        if os.path.exists(self.secrets_path):
            self._is_new = False
        else:
            os.makedirs(self.secrets_path, 0700)

    def is_open(self):
        return self._is_open

    def is_new(self):
        return self._is_new

    def open(self, password):
        if not self.is_open():
            self.key = transform_passwd(password)
            self._is_open = True

    def close(self):
        if not self.is_open():
            raise KeyringIsClosed("Keyring is already closed")

        self.key = None
        self._is_open = False

    def get(self, uuid):
        try:
            data = open(os.path.join(self.secrets_path, uuid)).read()
        except IOError:
            raise KeyringNoMatchError("No secrets for uuid %s" % uuid)

        pickledobj = decryptData(self.key, data, testforpickle=True)
        try:
            return pickle.load(StringIO(pickledobj))
        except:
            raise KeyringNoMatchError("bad password")

    def update(self, uuid, conn_id, secrets, update=True):
        path = os.path.join(self.secrets_path, uuid)
        with open(path, 'w') as f:
            data = encryptData(self.key, pickle.dumps(secrets))
            f.write(data)

    def delete(self, uuid):
        path = os.path.join(self.secrets_path, uuid)
        if not os.path.exists(path):
            raise KeyringNoMatchError("No secrets for uuid %s" % uuid)

        os.unlink(path)
        self._is_new = False


class PlainBackend(object):
    """Plain backend"""

    implements(IBackend)

    def __init__(self):
        self.bus = dbus.SystemBus()
        self._profile_manager = None
        self._keyring = None

    def should_be_used(self):
        # always used as a last resort
        return True

    def get_dialer_klass(self, device):
        # Fake function to comply with interface.
        pass

    def get_keyring(self, secrets_path):
        if self._keyring is None:
            self._keyring = KeyringManager(PlainKeyring(secrets_path))

        return self._keyring

    def get_profile_manager(self, arg=None):
        if self._profile_manager is None:
            self._profile_manager = PlainProfileManager(arg)

        return self._profile_manager


plain_backend = PlainBackend()
