from collections import defaultdict
import os

import copy
import dbus
from dbus.service import method, signal, Object, BusName
import gobject
from twisted.internet.defer import Deferred
from twisted.python import log
from zope.interface import implements

from wader.common._gconf import GConfHelper
from wader.common.consts import (WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH,
                                 APP_SLUG_NAME,
                                 MDM_INTFACE, MM_IP_METHOD_PPP,
                                 MM_SYSTEM_SETTINGS_PATH,
                                 MM_ALLOWED_MODE_ANY,
                                 MM_ALLOWED_MODE_2G_PREFERRED,
                                 MM_ALLOWED_MODE_3G_PREFERRED,
                                 MM_ALLOWED_MODE_2G_ONLY,
                                 MM_ALLOWED_MODE_3G_ONLY)

from wader.common.dialer import Dialer
import wader.common.exceptions as ex
from wader.common.interfaces import IBackend, IProfileManagerBackend
from wader.common.keyring import (KeyringManager, KeyringInvalidPassword,
                                  KeyringIsClosed, KeyringNoMatchError)
from wader.common.profile import Profile
from wader.common.secrets import ProfileSecrets
from wader.common.utils import (convert_int_to_uint, patch_list_signature,
                                revert_dict)

# this line is required, otherwise gnomekeyring will complain about
# the application name not being set
gobject.set_application_name(APP_SLUG_NAME)


NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_OBJPATH = '/org/freedesktop/NetworkManager'
NM_INTFACE = 'org.freedesktop.NetworkManager'
NM_DEVICE = '%s.Device' % NM_INTFACE
NM_GSM_INTFACE = '%s.Gsm' % NM_DEVICE

NM_USER_SETTINGS = 'org.freedesktop.NetworkManagerUserSettings'
NM_SYSTEM_SETTINGS = 'org.freedesktop.NetworkManagerSettings'
NM_SYSTEM_SETTINGS_OBJ = '/org/freedesktop/NetworkManagerSettings'
NM_SYSTEM_SETTINGS_CONNECTION = '%s.Connection' % NM_SYSTEM_SETTINGS
NM_SYSTEM_SETTINGS_SECRETS = '%s.Secrets' % NM_SYSTEM_SETTINGS_CONNECTION

GCONF_PROFILES_BASE = '/system/networking/connections'

NM_CONNECTED, NM_DISCONNECTED = 8, 3

NM_NETWORK_TYPE_MAP = {
    MM_ALLOWED_MODE_ANY: -1,
    MM_ALLOWED_MODE_2G_PREFERRED: 3,
    MM_ALLOWED_MODE_3G_PREFERRED: 2,
    MM_ALLOWED_MODE_2G_ONLY: 1,
    MM_ALLOWED_MODE_3G_ONLY: 0,
}
NM_NETWORK_TYPE_MAP_REV = revert_dict(NM_NETWORK_TYPE_MAP)


def transpose_from_NM(oldprops):
    # call on read
    props = copy.deepcopy(oldprops)

    if 'gsm' in props:
        # map to Modem manager constants, default to ANY
        if not 'network-type' in props['gsm']:
            props['gsm']['network-type'] = MM_ALLOWED_MODE_ANY
        else:
            nm_val = props['gsm'].get('network-type')
            props['gsm']['network-type'] = NM_NETWORK_TYPE_MAP_REV[nm_val]

    # XXX: shouldn't we be converting the DNS/Address/route integer values
    #      received from NM
    return dict(props)


def transpose_to_NM(oldprops, new=True):
    # call on write
    props = copy.deepcopy(oldprops)

    if 'gsm' in props:
        mm_val = props['gsm'].get('network-type', MM_ALLOWED_MODE_ANY)
        props['gsm']['network-type'] = NM_NETWORK_TYPE_MAP[mm_val]

    # NM doesn't like us setting these on update
    if not new:
        for key in ['connection', 'gsm', 'ppp', 'serial', 'ipv4']:
            if 'name' in props[key]:
                del props[key]['name']

    if 'ipv4' in props:
        if not props['ipv4'].get('ignore-auto-dns'):
            props['ipv4']['dns'] = []

        # convert the integer format
        for key in ['addresses', 'dns', 'routes']:
            if key in props['ipv4']:
                val = props['ipv4'][key]
                value = map(dbus.UInt32, map(convert_int_to_uint, val))
                if key in ['dns']:
                    props['ipv4'][key] = dbus.Array(value, signature='u')
                else:
                    props['ipv4'][key] = dbus.Array(value, signature='au')

    return props


class NMDialer(Dialer):
    """I wrap NetworkManager's dialer"""

    def __init__(self, device, opath, **kwds):
        super(NMDialer, self).__init__(device, opath, **kwds)

        self.int = None
        self.conn_obj = None
        self.iface = self._get_stats_iface()
        self.state = NM_DISCONNECTED

        self.nm_opath = None
        self.connect_deferred = None
        self.disconnect_deferred = None
        self.sm = None

    def _cleanup(self):
        # enable +CREG notifications afterwards
        self.device.sconn.set_netreg_notification(1)
        self.sm.remove()
        self.sm = None

    def _get_device_opath(self):
        """
        Returns the object path to use in the connection / signal
        """
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        interface = dbus.Interface(obj, NM_INTFACE)
        for opath in interface.GetDevices():
            dev = self.bus.get_object(NM_SERVICE, opath)
            udi = dev.Get('org.freedesktop.NetworkManager.Devices', 'Udi')
            if self.device.opath == udi:
                return opath

    def _get_stats_iface(self):
        if self.device.get_property(MDM_INTFACE,
                                    'IpMethod') == MM_IP_METHOD_PPP:
            iface = 'ppp0' # XXX: shouldn't hardcode to first PPP instance
        else:
            iface = self.device.get_property(MDM_INTFACE, 'Device')

        return iface

    def _on_properties_changed(self, changed):
        if 'State' not in changed:
            return

        if changed['State'] == NM_CONNECTED and self.state == NM_DISCONNECTED:
            # emit the connected signal and send back the opath
            # if the deferred is present
            self.state = NM_CONNECTED
            self.Connected()
            self.connect_deferred.callback(self.opath)

        if changed['State'] == NM_DISCONNECTED and self.state == NM_CONNECTED:
            self.state = NM_DISCONNECTED
            self.Disconnected()
            if self.disconnect_deferred is not None:
                # could happen if we are connected and a NM_DISCONNECTED
                # signal arrives without having explicitly disconnected
                self.disconnect_deferred.callback(self.conn_obj)
            self._cleanup()

    def _setup_signals(self):
        self.sm = self.bus.add_signal_receiver(self._on_properties_changed,
                                               "PropertiesChanged",
                                               path=self._get_device_opath(),
                                               dbus_interface=NM_GSM_INTFACE)

    def configure(self, config):
        self._setup_signals()
        # get the profile object and obtains its uuid
        # get ProfileManager and translate the uuid to a NM object path
        profiles = self.bus.get_object(WADER_PROFILES_SERVICE,
                                       WADER_PROFILES_OBJPATH)
        # get the object path of the profile being used
        self.nm_opath = profiles.GetNMObjectPath(str(config.uuid),
                                       dbus_interface=WADER_PROFILES_INTFACE)
        # Disable +CREG notifications, otherwise NMDialer won't work
        return self.device.sconn.set_netreg_notification(0)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)
        args = (NM_USER_SETTINGS, self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s\n%s" % args)
        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()

    def stop(self):
        self._cleanup()
        return self.disconnect()

    def disconnect(self):
        self.disconnect_deferred = Deferred()
        self.int.DeactivateConnection(self.conn_obj)
        # the deferred will be callbacked as soon as we get a
        # connectivity status change
        return self.disconnect_deferred


class GnomeKeyring(object):
    """I just wrap gnome-keyring"""

    def __init__(self):
        super(GnomeKeyring, self).__init__()
        self._is_new = False
        self.gk = None
        self.name = None
        self._setup_keyring()

    def _setup_keyring(self):
        # import it here so importing this backend on a non GNOME
        # system doesn't fails
        import gnomekeyring as gk
        self.gk = gk
        self.name = self.gk.get_default_keyring_sync()

        if not self.name:
            self._is_new = True
            self.name = 'login'

            # if keyring does not exist, create it
            try:
                self.gk.create_sync(self.name, None)
            except self.gk.AlreadyExistsError:
                pass

            self.gk.set_default_keyring_sync(self.name)

    def is_open(self):
        info = self.gk.get_info_sync(self.name)
        return not info.get_is_locked()

    def is_new(self):
        return self._is_new

    def open(self, password):
        """See :meth:`KeyringManager.open`"""
        if not self.is_open():
            try:
                self.gk.unlock_sync(self.name, password)
            except (IOError, self.gk.DeniedError):
                raise KeyringInvalidPassword()

    def close(self):
        """See :meth:`KeyringManager.close`"""
        if self.is_open():
            self.gk.lock_sync(self.name)
        else:
            raise KeyringIsClosed()

    def get(self, uuid):
        """See :meth:`KeyringManager.get_secrets`"""
        attrs = {'connection-uuid': str(uuid)}
        try:
            secrets = self.gk.find_items_sync(
                            self.gk.ITEM_GENERIC_SECRET, attrs)
            return {'gsm': {'passwd': secrets[0].secret}}
        except self.gk.NoMatchError:
            msg = "No secrets for connection '%s'"
            raise KeyringNoMatchError(msg % str(uuid))

    def update(self, uuid, conn_id, secrets, update=True):
        """See :meth:`KeyringManager.update_secret`"""
        attrs = {'connection-uuid': str(uuid), 'setting-name': 'gsm',
                 'setting-key': 'password'}

        password = secrets['gsm']['passwd']
        text = 'Network secret for %s/%s/%s' % (conn_id, 'gsm', 'password')
        return self.gk.item_create_sync(self.name, self.gk.ITEM_GENERIC_SECRET,
                                        text, attrs, password, update)

    def delete(self, uuid):
        """See :meth:`KeyringManager.delete_secret`"""
        attrs = {'connection-uuid': str(uuid)}
        secrets = self.gk.find_items_sync(self.gk.ITEM_GENERIC_SECRET, attrs)
        # we find the secret, and we delete it
        return self.gk.item_delete_sync(self.name, secrets[0].item_id)


class NMProfile(Profile):
    """I am a group of settings required to dial up"""

    def __init__(self, opath, nm_obj, gpath, props, manager):
        super(NMProfile, self).__init__(opath)
        self.helper = GConfHelper()

        self.nm_obj = nm_obj
        self.gpath = gpath
        self.props = props
        self.manager = manager

        from wader.common.backends import get_backend
        keyring = get_backend().get_keyring()
        self.secrets = ProfileSecrets(self, keyring)
        self._connect_to_signals()

    def _connect_to_signals(self):
        self.nm_obj.connect_to_signal("Removed", self._on_removed)
        self.nm_obj.connect_to_signal("Updated", self._on_updated)

    def _on_removed(self):
        log.msg("Profile %s has been removed externally" % self.opath)
        self.manager.remove_profile(self)

    def _on_updated(self, props):
        log.msg("Profile %s has been updated" % self.opath)
        self.update(props)

    def _write(self, props):
        self.props = props

        props = transpose_to_NM(props)

        for key, value in props.iteritems():
            new_path = os.path.join(self.gpath, key)
            self.helper.set_value(new_path, value)

        self.helper.client.suggest_sync()

    def _load_info(self):
        props = {}

        if self.helper.client.dir_exists(self.gpath):
            self._load_dir(self.gpath, props)

        self.props = transpose_from_NM(props)

    def _load_dir(self, directory, info):
        for entry in self.helper.client.all_entries(directory):
            key = os.path.basename(entry.key)
            info[key] = self.helper.get_value(entry.value)

        for _dir in self.helper.client.all_dirs(directory):
            dirname = os.path.basename(_dir)
            info[dirname] = {}
            self._load_dir(_dir, info[dirname])

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
        return self.secrets.get(ask)

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
        from gconf import UNSET_INCLUDING_SCHEMA_NAMES
        self.helper.client.recursive_unset(self.gpath,
                                           UNSET_INCLUDING_SCHEMA_NAMES)
        # emit Removed and unexport from DBus
        self.Removed()
        self.remove_from_connection()


class NMProfileManager(Object):
    """I manage profiles in the system"""

    implements(IProfileManagerBackend)

    def __init__(self):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        super(NMProfileManager, self).__init__(bus_name,
                                               WADER_PROFILES_OBJPATH)
        self.helper = GConfHelper()
        self.gpath = GCONF_PROFILES_BASE
        self.profiles = {}
        self.nm_profiles = {}
        self.nm_manager = None
        self.index = -1

        self._init_nm_manager()
        # connect to signals
        self._connect_to_signals()

    def get_next_dbus_opath(self):
        self.index += 1
        return os.path.join(MM_SYSTEM_SETTINGS_PATH, str(self.index))

    def _init_nm_manager(self):
        obj = self.bus.get_object(NM_USER_SETTINGS, NM_SYSTEM_SETTINGS_OBJ)
        self.nm_manager = dbus.Interface(obj, NM_SYSTEM_SETTINGS)

    def _connect_to_signals(self):
        self.nm_manager.connect_to_signal("NewConnection",
                       self._on_new_nm_profile, NM_SYSTEM_SETTINGS)

    def _on_new_nm_profile(self, opath):
        obj = self.bus.get_object(NM_USER_SETTINGS, opath)
        props = obj.GetSettings(dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION)
        # filter out non GSM profiles
        if props['connection']['type'] == 'gsm':
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

    def _get_next_free_gpath(self):
        """Returns the next unused slot of /system/networking/connections"""
        all_dirs = list(self.helper.client.all_dirs(self.gpath))
        try:
            max_index = max(map(int, [d.split('/')[-1] for d in all_dirs]))
        except ValueError:
            # /system/networking/connections is empty
            max_index = -1

        index = 0 if not all_dirs else max_index + 1
        return os.path.join(self.gpath, str(index))

    def _get_profile_from_nm_connection(self, uuid):
        for gpath in self.helper.client.all_dirs(self.gpath):
            # filter out wlan connections
            if self.helper.client.dir_exists(os.path.join(gpath, 'gsm')):
                path = os.path.join(gpath, 'connection', 'uuid')
                value = self.helper.client.get(path)
                if value and uuid == self.helper.get_value(value):
                    return self._get_profile_from_gconf_path(gpath)

        msg = "NM profile identified by uuid %s could not be found"
        raise ex.ProfileNotFoundError(msg % uuid)

    def _get_profile_from_gconf_path(self, gconf_path):
        props = defaultdict(dict)
        for path in self.helper.client.all_dirs(gconf_path):
            for entry in self.helper.client.all_entries(path):
                section, key = entry.get_key().split('/')[-2:]
                value = entry.get_value()
                if value is not None:
                    props[section][key] = self.helper.get_value(value)

        props = transpose_from_NM(props)
        uuid = props['connection']['uuid']
        try:
            return NMProfile(self.get_next_dbus_opath(),
                             self.nm_profiles[uuid],
                             gconf_path, props, self)
        except KeyError:
            raise ex.ProfileNotFoundError("Profile '%s' could not "
                                          "be found" % uuid)

    def _do_set_profile(self, path, props):
        props = transpose_to_NM(props)

        for key in props:
            for name in props[key]:
                value = props[key][name]
                _path = os.path.join(path, key, name)

                self.helper.set_value(_path, value)

        self.helper.client.suggest_sync()

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        gconf_path = self._get_next_free_gpath()
        self._do_set_profile(gconf_path, props)
        # the rest will be handled by _on_new_nm_profile

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

    def get_profiles(self):
        """Returns all the profiles in the system"""
        if not self.nm_profiles:
            # cache existing profiles
            map(self._on_new_nm_profile, self.nm_manager.ListConnections())

        if not self.profiles:
            for path in self.helper.client.all_dirs(self.gpath):
                # filter out wlan connections
                if self.helper.client.dir_exists(os.path.join(path, 'gsm')):
                    # profile = self._get_profile_from_gconf_path(path)
                    # uuid = profile.get_settings()['connection']['uuid']
                    # self.profiles[uuid] = profile
                    try:
                         profile = self._get_profile_from_gconf_path(path)
                         uuid = profile.get_settings()['connection']['uuid']
                         self.profiles[uuid] = profile

                    except ex.ProfileNotFoundError:
                         pass

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
        _profile.update(props)

        props = transpose_to_NM(props, new=False)

        if uuid in self.nm_profiles:
            obj = self.nm_profiles[uuid]
            obj.Update(props,
                       dbus_interface=NM_SYSTEM_SETTINGS_CONNECTION)

    @signal(dbus_interface=WADER_PROFILES_INTFACE, signature='o')
    def NewConnection(self, opath):
        pass

    @method(dbus_interface=WADER_PROFILES_INTFACE,
            in_signature='s', out_signature='o')
    def GetNMObjectPath(self, uuid):
        """Returns the object path of the connection referred by ``uuid``"""
        if uuid not in self.nm_profiles:
            msg = "Could not find profile %s in %s"
            raise KeyError(msg % (uuid, self.nm_profiles))

        profile = self.nm_profiles[uuid]
        return profile.__dbus_object_path__


class NetworkManagerBackend(object):

    implements(IBackend)

    def __init__(self):
        self.bus = dbus.SystemBus()
        self._nm08_present = None
        self._nm_applet_present = None
        self._profile_manager = None
        self._keyring = None

    def _is_nm08_present(self):
        if self._nm08_present is None:
            try:
                obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
                devices = obj.GetDevices()
                if len(devices):
                    self._nm08_present = 'NetworkManager' in devices[0]
                else:
                    self._nm08_present = False
            except dbus.DBusException:
                self._nm08_present = False

        return self._nm08_present

    def _is_nm_applet_present(self):
        if self._nm_applet_present is None:
            try:
                self.bus.get_object(NM_USER_SETTINGS,
                                    NM_SYSTEM_SETTINGS_OBJ)
                self._nm_applet_present = True
            except dbus.DBusException:
                self._nm_applet_present = False

        return self._nm_applet_present

    def should_be_used(self):
        """Returns True if both NM08-core and UI are present"""
        return all([self._is_nm08_present(), self._is_nm_applet_present()])

    def get_dialer_klass(self, device):
        return NMDialer

    def get_keyring(self):
        if self._keyring is None:
            self._keyring = KeyringManager(GnomeKeyring())

        return self._keyring

    def get_profile_manager(self, arg=None):
        if self._profile_manager is None:
            self._profile_manager = NMProfileManager()

        return self._profile_manager


nm_backend = NetworkManagerBackend()
