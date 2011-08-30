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
from wader.common.utils import (convert_int_to_uint32, convert_uint32_to_int,
                                patch_list_signature, revert_dict)

# XXX: mustn't set the application name here else BCM gets called 'wader-core'
# > this line is required, otherwise gnomekeyring will complain about
# > the application name not being set
# gobject.set_application_name(APP_SLUG_NAME)

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_OBJPATH = '/org/freedesktop/NetworkManager'
NM_INTFACE = 'org.freedesktop.NetworkManager'
NM_DEVICE = '%s.Device' % NM_INTFACE

NM08_GSM_INTFACE = '%s.Gsm' % NM_DEVICE
NM08_USER_SETTINGS = 'org.freedesktop.NetworkManagerUserSettings'
NM08_SYSTEM_SETTINGS = 'org.freedesktop.NetworkManagerSettings'
NM08_SYSTEM_SETTINGS_OBJ = '/org/freedesktop/NetworkManagerSettings'
NM08_SYSTEM_SETTINGS_CONNECTION = '%s.Connection' % NM08_SYSTEM_SETTINGS
NM08_SYSTEM_SETTINGS_SECRETS = '%s.Secrets' % NM08_SYSTEM_SETTINGS_CONNECTION

NM084_SETTINGS = '%sUserSettings' % NM_SERVICE
NM084_SETTINGS_INT = '%sSettings' % NM_INTFACE
NM084_SETTINGS_OBJ = '%sSettings' % NM_OBJPATH
NM084_SETTINGS_CONNECTION = '%s.Connection' % NM084_SETTINGS_INT
NM084_SETTINGS_CONNECTION_SECRETS = '%s.Secrets' % NM084_SETTINGS_CONNECTION

NM09_MODEM_INTFACE = '%s.Modem' % NM_DEVICE
NM09_SETTINGS = NM_SERVICE
NM09_SETTINGS_INT = '%s.Settings' % NM_INTFACE
NM09_SETTINGS_OBJ = '%s/Settings' % NM_OBJPATH
NM09_SETTINGS_CONNECTION = '%s.Connection' % NM09_SETTINGS_INT


NM08_STATE = {
    'UNKNOWN': 0,
    'ASLEEP': 1,
    'CONNECTING': 2,
    'CONNECTED': 3,
    'DISCONNECTED': 4,
}

NM09_STATE = {
    'UNKNOWN': 0,
    'ASLEEP': 10,
    'DISCONNECTED': 20,
    'DISCONNECTING': 30,
    'CONNECTING': 40,
    'CONNECTED_LOCAL': 50,
    'CONNECTED_SITE': 60,
    'CONNECTED_GLOBAL': 70,
    'IPCONFIG': 100
}

NM08_DEVICE_STATE_UNKNOWN = 0
NM08_DEVICE_STATE_UNMANAGED = 1
NM08_DEVICE_STATE_UNAVAILABLE = 2
NM08_DEVICE_STATE_DISCONNECTED = 3
NM08_DEVICE_STATE_PREPARE = 4
NM08_DEVICE_STATE_CONFIG = 5
NM08_DEVICE_STATE_NEED_AUTH = 6
NM08_DEVICE_STATE_IP_CONFIG = 7
NM08_DEVICE_STATE_ACTIVATED = 8
NM08_DEVICE_STATE_FAILED = 9

NM08_DEVICE_STATE = {
    'UNKNOWN': NM08_DEVICE_STATE_UNKNOWN,
    'UNMANAGED': NM08_DEVICE_STATE_UNMANAGED,
    'UNAVAILABLE': NM08_DEVICE_STATE_UNAVAILABLE,
    'DISCONNECTED': NM08_DEVICE_STATE_DISCONNECTED,
    'PREPARE': NM08_DEVICE_STATE_PREPARE,
    'CONFIG': NM08_DEVICE_STATE_CONFIG,
    'NEED_AUTH': NM08_DEVICE_STATE_NEED_AUTH,
    'IP_CONFIG': NM08_DEVICE_STATE_IP_CONFIG,
    'ACTIVATED': NM08_DEVICE_STATE_ACTIVATED,
    'FAILED': NM08_DEVICE_STATE_FAILED
}

NM09_DEVICE_STATE_UNKNOWN = 0
NM09_DEVICE_STATE_UNMANAGED = 10
NM09_DEVICE_STATE_UNAVAILABLE = 20
NM09_DEVICE_STATE_DISCONNECTED = 30
NM09_DEVICE_STATE_PREPARE = 40
NM09_DEVICE_STATE_CONFIG = 50
NM09_DEVICE_STATE_NEED_AUTH = 60
NM09_DEVICE_STATE_IP_CONFIG = 70
NM09_DEVICE_STATE_IP_CHECK = 80
NM09_DEVICE_STATE_SECONDARIES = 90
NM09_DEVICE_STATE_ACTIVATED = 100

NM09_DEVICE_STATE = {
    'UNKNOWN': NM09_DEVICE_STATE_UNKNOWN,
    'UNMANAGED': NM09_DEVICE_STATE_UNMANAGED,
    'UNAVAILABLE': NM09_DEVICE_STATE_UNAVAILABLE,
    'DISCONNECTED': NM09_DEVICE_STATE_DISCONNECTED,
    'PREPARE': NM09_DEVICE_STATE_PREPARE,
    'CONFIG': NM09_DEVICE_STATE_CONFIG,
    'NEED_AUTH': NM09_DEVICE_STATE_NEED_AUTH,
    'IP_CONFIG': NM09_DEVICE_STATE_IP_CONFIG,
    'IP_CHECK': NM09_DEVICE_STATE_IP_CHECK,
    'SECONDARIES': NM09_DEVICE_STATE_SECONDARIES,
    'ACTIVATED': NM09_DEVICE_STATE_ACTIVATED
}

GCONF_PROFILES_BASE = '/system/networking/connections'

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

        # Note: password is never retrieved via plain props but we map it
        #       anyway to be symmetric
        if 'password' in props['gsm']:
            props['gsm']['passwd'] = props['gsm']['password']
            del props['gsm']['password']

    if 'ipv4' in props:
        if 'dns' in props['ipv4']:
            props['ipv4']['ignore-auto-dns'] = (len(props['ipv4']['dns']) > 0)
        else:
            props['ipv4']['ignore-auto-dns'] = False

        # convert the integer format
        for key in ['addresses', 'dns', 'routes']:
            if key in props['ipv4']:
                vals = map(convert_uint32_to_int, props['ipv4'][key])
                props['ipv4'][key] = vals

    return dict(props)


def transpose_to_NM(oldprops, new=True):
    # call on write
    props = copy.deepcopy(oldprops)

    if 'gsm' in props:
        mm_val = props['gsm'].get('network-type', MM_ALLOWED_MODE_ANY)
        props['gsm']['network-type'] = NM_NETWORK_TYPE_MAP[mm_val]

        # filter out old single band settings, NM now uses a mask
        if 'band' in props['gsm']:
            del props['gsm']['band']

        # Note: password is set via plain props
        if 'passwd' in props['gsm']:
            props['gsm']['password'] = props['gsm']['passwd']
            del props['gsm']['passwd']

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
                value = map(convert_int_to_uint32, props['ipv4'][key])
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
        self.state = self.NM_DISCONNECTED

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
            udi = dev.Get('org.freedesktop.NetworkManager.Device', 'Udi')
            if self.device.opath == udi:
                return opath

    def _get_stats_iface(self):
        if self.device.get_property(MDM_INTFACE,
                                    'IpMethod') == MM_IP_METHOD_PPP:
            iface = 'ppp0'  # XXX: shouldn't hardcode to first PPP instance
        else:
            iface = self.device.get_property(MDM_INTFACE, 'Device')

        return iface

    def _on_properties_changed(self, changed):
        if 'State' not in changed:
            return

        if changed['State'] == self.NM_CONNECTED and \
                self.state == self.NM_DISCONNECTED:
            # emit the connected signal and send back the opath
            # if the deferred is present
            self.state = self.NM_CONNECTED
            self.Connected()
            self.connect_deferred.callback(self.opath)
            return

        if changed['State'] == self.NM_DISCONNECTED:

            if self.state == self.NM_CONNECTED:
                self.Disconnected()
                if self.disconnect_deferred is not None:
                    # could happen if we are connected and a NM_DISCONNECTED
                    # signal arrives without having explicitly disconnected
                    self.disconnect_deferred.callback(self.conn_obj)

            if self.state == self.NM_DISCONNECTED:
                # Occurs if the connection attempt failed
                self.Disconnected()
                if self.connect_deferred is not None:
                    msg = 'Network Manager failed to connect'
                    self.connect_deferred.errback(RuntimeError(msg))

            self.state = self.NM_DISCONNECTED
            self._cleanup()

    def _setup_signals(self):
        self.sm = self.bus.add_signal_receiver(self._on_properties_changed,
                                                "PropertiesChanged",
                                                path=self._get_device_opath(),
                                            dbus_interface=self.NM_MODEM_INT)

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
        raise NotImplementedError("Implement in subclass")

    def stop(self):
        self._cleanup()
        return self.disconnect()

    def disconnect(self):
        self.disconnect_deferred = Deferred()
        self.int.DeactivateConnection(self.conn_obj)
        # the deferred will be callbacked as soon as we get a
        # connectivity status change
        return self.disconnect_deferred


class NM08Dialer(NMDialer):

    def __init__(self, device, opath, **kwds):
        self.NM_CONNECTED = NM08_DEVICE_STATE_ACTIVATED
        self.NM_DISCONNECTED = NM08_DEVICE_STATE_DISCONNECTED
        self.NM_MODEM_INT = NM08_GSM_INTFACE

        super(NM08Dialer, self).__init__(device, opath, **kwds)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)

        # NM 0.8 - applet (USER)
        #    <arg name="service_name" type="s" direction="in"/>
        #    <arg name="connection" type="o" direction="in"/>
        #    <arg name="device" type="o" direction="in"/>
        #    <arg name="specific_object" type="o" direction="in"/>
        args = (NM08_USER_SETTINGS,
                self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s\n%s" % args)

        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()


class NM09Dialer(NMDialer):

    def __init__(self, device, opath, **kwds):
        self.NM_CONNECTED = NM09_DEVICE_STATE_ACTIVATED
        self.NM_DISCONNECTED = NM09_DEVICE_STATE_DISCONNECTED
        self.NM_MODEM_INT = NM09_MODEM_INTFACE

        super(NM09Dialer, self).__init__(device, opath, **kwds)

    def connect(self):
        self.connect_deferred = Deferred()
        obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
        self.int = dbus.Interface(obj, NM_INTFACE)

        # NM 0.9
        #     <arg name="connection" type="o" direction="in">
        #     <arg name="device" type="o" direction="in">
        #     <arg name="specific_object" type="o" direction="in">
        args = (self.nm_opath, self._get_device_opath(), '/')
        log.msg("Connecting with:\n%s\n%s\n%s" % args)

        try:
            self.conn_obj = self.int.ActivateConnection(*args)
            # the deferred will be callbacked as soon as we get a
            # connectivity status change
            return self.connect_deferred
        except dbus.DBusException, e:
            log.err(e)
            self._cleanup()


class DummyKeyringManager(object):

    def __init__(self, get_cb, set_cb):
        self.get_cb = get_cb
        self.set_cb = set_cb

    def get_secrets(self, uuid):
        """Returns the secrets associated with ``uuid``"""
        return self.get_cb(uuid)

    def is_open(self):
        """Always open"""
        return True

    def update_secret(self, uuid, secrets, update=True):
        return self.set_cb(uuid, secrets)


class DummySecrets(object):

    def __init__(self, connection, manager):
        self.uuid = connection.get_settings()['connection']['uuid']
        self.manager = manager

    def get(self, ask=True):
        """Returns the secrets associated with the profile"""
        return self.manager.get_secrets(self.uuid)

    def is_open(self):
        return self.manager.is_open()

    def update(self, secrets, ask=True):
        """Updates the secrets associated with the profile"""
        return self.manager.update_secret(self.uuid, secrets)


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

    def __init__(self, opath, nm_obj, props, manager):
        super(NMProfile, self).__init__(opath)

        self.nm_obj = nm_obj
        self.props = props
        self.manager = manager

    def _connect_to_signals(self):
        self.nm_obj.connect_to_signal("Removed", self._on_removed)
        self.nm_obj.connect_to_signal("Updated", self._on_updated)

    def get_secrets(self, tag, hints=None, ask=True):
        """
        Returns the secrets associated with the profile

        :param tag: The section to use
        :param hints: what specific setting are we interested in
        :param ask: Should we ask the user if there is no secret?
        """
        return self.secrets.get(ask)

    def get_settings(self):
        """Returns the profile settings"""
        return patch_list_signature(self.props)

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


class NM08Profile(NMProfile):

    def __init__(self, opath, nm_obj, gpath, props, manager):
        super(NM08Profile, self).__init__(opath, nm_obj, props, manager)

        self.helper = GConfHelper()
        self.gpath = gpath

        from wader.common.backends import get_backend
        keyring = get_backend().get_keyring()
        self.secrets = ProfileSecrets(self, keyring)

        self._connect_to_signals()

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

        self.helper.client.notify(self.gpath)
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


class NM084Profile(NMProfile):

    def __init__(self, opath, nm_obj, props, manager):
        super(NM084Profile, self).__init__(opath, nm_obj, props, manager)

        self.secrets = DummySecrets(self, self.manager.keyring_manager)

        self._connect_to_signals()

    def _on_removed(self):
        log.msg("NM Connection profile %s has been removed" % self.opath)
        self.manager.remove_profile_cb(self)

    def _on_updated(self, props):
        log.msg("NM Connection profile %s has been updated" % self.opath)
        self.manager.update_profile_cb(self, props)

    def update(self, props):
        """Updates the profile with settings ``props``"""
        self.props = props
        # emit Updated
        self.Updated(patch_list_signature(self.props))

    def remove(self):
        """Removes the profile"""
        # emit Removed and unexport from DBus
        self.Removed()
        self.remove_from_connection()


class NM09Profile(NM084Profile):

    def _on_updated(self):
        log.msg("NM Connection profile %s has been updated" % self.opath)
        self.manager.update_profile_cb(self)


class NMProfileManager(Object):
    """I manage profiles in the system"""

    implements(IProfileManagerBackend)

    def __init__(self):
        self.bus = dbus.SystemBus()
        bus_name = BusName(WADER_PROFILES_SERVICE, bus=self.bus)
        super(NMProfileManager, self).__init__(bus_name,
                                               WADER_PROFILES_OBJPATH)
        self.profiles = {}
        self.nm_profiles = {}
        self.nm_manager = None
        self.index = -1

        self._init_nm_manager()

    def get_next_dbus_opath(self):
        self.index += 1
        return os.path.join(MM_SYSTEM_SETTINGS_PATH, str(self.index))

    def get_profile_by_object_path(self, opath):
        """Returns a :class:`Profile` out of its object path ``opath``"""
        for profile in self.profiles.values():
            if profile.opath == opath:
                return profile

        raise ex.ProfileNotFoundError("No profile with object path %s" % opath)

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


class NM08ProfileManager(NMProfileManager):
    """I manage profiles in the system"""

    def __init__(self):
        super(NM08ProfileManager, self).__init__()

        self.helper = GConfHelper()
        self.gpath = GCONF_PROFILES_BASE

        # connect to signals
        self._connect_to_signals()

    def _init_nm_manager(self):
        obj = self.bus.get_object(NM08_USER_SETTINGS, NM08_SYSTEM_SETTINGS_OBJ)
        self.nm_manager = dbus.Interface(obj, NM08_SYSTEM_SETTINGS)

    def _connect_to_signals(self):
        self.nm_manager.connect_to_signal("NewConnection",
                       self._on_new_nm_profile, NM08_SYSTEM_SETTINGS)

    def _on_new_nm_profile(self, opath):
        obj = self.bus.get_object(NM08_USER_SETTINGS, opath)
        props = obj.GetSettings(dbus_interface=NM08_SYSTEM_SETTINGS_CONNECTION)
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
            return NM08Profile(self.get_next_dbus_opath(),
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

        self.helper.client.notify(path)
        self.helper.client.suggest_sync()

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        gconf_path = self._get_next_free_gpath()
        self._do_set_profile(gconf_path, props)
        # the rest will be handled by _on_new_nm_profile

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
                       dbus_interface=NM08_SYSTEM_SETTINGS_CONNECTION)


class NMLaterProfileManager(NMProfileManager):
    # XXX: Poor name but is intended to provide common stuff in 0.8.4 and 0.9,
    #      to be subclassed only

    def __init__(self):
        super(NMLaterProfileManager, self).__init__()

    def _init_nm_manager(self):
        obj = self.bus.get_object(self.NM_SETTINGS, self.NM_SETTINGS_OBJ)
        self.nm_manager = dbus.Interface(obj, self.NM_SETTINGS_INT)

    def _connect_to_signals(self):
        self.nm_manager.connect_to_signal("NewConnection",
                       self._on_new_nm_profile, self.NM_SETTINGS_INT)

    def _on_new_nm_profile(self, opath):
        log.msg("NM notified us of a new connection profile %s" % opath)
        self._store_new_profile(opath)

    def _get_profile_from_nm_connection(self, props):
        print "NMLaterProfileManager::_get_profile_from_nm_connection()"

        props = transpose_from_NM(props)
        uuid = props['connection']['uuid']
        try:
            return self.NM_PROFILE_KLASS(self.get_next_dbus_opath(),
                               self.nm_profiles[uuid], props, self)
        except KeyError:
            raise ex.ProfileNotFoundError("Profile '%s' could not "
                                          "be found" % uuid)

    def _keyring_set_callback(self, uuid, secrets):
        # Our UI clients expect that setting password secrets is a separate
        # operation to other profile activities when in fact we do it via the
        # same mechanism again, this means that two NM connection updates are
        # generated for every client profile save.
        print "NMLaterProfileManager::_keyring_set_callback()"

        passwd = secrets['gsm']['passwd']

        if uuid in self.nm_profiles:
            obj = self.nm_profiles[uuid]
            # Need to merge in the password
            nm_props = obj.GetSettings(dbus_interface=self.NM_SETTINGS_CONNECTION)
            nm_props['gsm']['password'] = passwd

            obj.Update(nm_props, dbus_interface=self.NM_SETTINGS_CONNECTION)
        else:
            log.msg("NM connection profile does not exist for %s" % uuid)

    def _store_new_profile(self, opath):
        """
        called:
            1/ from signal handler when NM has a new connection
            2/ by get_profiles to populate the profiles cache
        """
        print "NMLaterProfileManager::_store_new_profile()"
        obj = self.bus.get_object(self.NM_SETTINGS, opath)

        props = obj.GetSettings(dbus_interface=self.NM_SETTINGS_CONNECTION)

        # filter out non GSM profiles
        if props['connection']['type'] != 'gsm':
            return

        uuid = props['connection']['uuid']
        assert uuid not in self.nm_profiles, "Adding twice the same profile?"
        self.nm_profiles[uuid] = obj

        # handle when a NM profile has been externally added
        if uuid not in self.profiles:
            try:
                profile = self._get_profile_from_nm_connection(props)
            except ex.ProfileNotFoundError:
                log.msg("Adding non existing NM profile %s" % uuid)
                del self.nm_profiles[uuid]
            else:
                self.profiles[uuid] = profile
                self.NewConnection(profile.opath)

    def get_profiles(self):
        """Returns all the profiles in the system"""
        if not self.nm_profiles:
            # cache existing profiles
            map(self._store_new_profile, self.nm_manager.ListConnections())

        if self.profiles is None:
            return []

        return self.profiles.values()

    def remove_profile(self, profile):
        print "NMLaterProfileManager::remove_profile()"
        """
        Removes profile ``profile``

        Should initiate the NM connection removal, but the removal of our
        profile should be done by the signal handler
        """
        uuid = profile.get_settings()['connection']['uuid']

        if uuid in self.nm_profiles:
            obj = self.nm_profiles[uuid]
            obj.Delete(dbus_interface=self.NM_SETTINGS_CONNECTION)
        else:
            log.msg("NM connection profile does not exist for %s" % uuid)

    def remove_profile_cb(self, profile):
        """
        Called by NMxxxProfile's Remove signal handler
        """
        log.msg("NM notified us of a connection profile removal")

        uuid = profile.props['connection']['uuid']

        if uuid in self.profiles:
            self.profiles[uuid].remove()
            del self.profiles[uuid]

        if uuid in self.nm_profiles:
            del self.nm_profiles[uuid]

    def update_profile(self, profile, props):
        """
        Updates ``profile`` with settings ``props``

        Should initiate the NM connection update, but the update of our
        profile should be done by the signal handler
        """
        print "NMLaterProfileManager::update_profile()"
        uuid = profile.get_settings()['connection']['uuid']
        nm_props = transpose_to_NM(props, new=False)

        if uuid in self.nm_profiles:
            obj = self.nm_profiles[uuid]
            obj.Update(nm_props, dbus_interface=self.NM_SETTINGS_CONNECTION)
        else:
            log.msg("NM connection profile does not exist for %s" % uuid)

    def update_profile_cb(self, profile, nm_props=None):
        """
        Called by NMxxxProfile's Updated signal handler
        Called twice per BCM profile change as passwd is updated separately
        via the keyring
        """
        log.msg("NM notified us of a connection profile update")

        obj = profile.nm_obj

        if nm_props is None:
            # NM 0.9 doesn't signal the changed props so we have to retrieve them
            nm_props = obj.GetSettings(dbus_interface=self.NM_SETTINGS_CONNECTION)

        # NM 0.8.4 does signal the changed props but we still have to retrieve the
        # password and merge
        try:
            secrets = obj.GetSecrets('gsm',
                                    dbus_interface=self.NM_SETTINGS_CONNECTION)
            password = secrets['gsm']['password']
        except (KeyError, dbus.exceptions.DBusException):
            pass
        else:
            nm_props['gsm']['password'] = password

        props = transpose_from_NM(nm_props)

        uuid = props['connection']['uuid']
        if uuid in self.profiles:
            self.profiles[uuid].update(props)


class NM084ProfileManager(NMLaterProfileManager):

    def __init__(self):
        super(NM084ProfileManager, self).__init__()

        self.keyring_manager = DummyKeyringManager(self._keyring_get_callback,
                                                    self._keyring_set_callback)
        self.helper = GConfHelper()

        # profile class to create
        self.NM_PROFILE_KLASS = NM084Profile

        # connect to signals
        self._connect_to_signals()

    def _init_nm_manager(self):
        # define DBus details
        self.NM_SETTINGS = NM084_SETTINGS
        self.NM_SETTINGS_OBJ = NM084_SETTINGS_OBJ
        self.NM_SETTINGS_INT = NM084_SETTINGS_INT
        self.NM_SETTINGS_CONNECTION = NM084_SETTINGS_CONNECTION

        super(NM084ProfileManager, self)._init_nm_manager()

    def _get_secrets_gnome(self, uuid):
        # Absolutely the bare minimum wanted here, if the keyring doesn't exist
        # don't create it, and if we fail because we aren't on a gnome system or
        # the value doesn't exist then just return None
        print "NM084ProfileManager::_keyring_get_callback() trying GnomeKeyring"

        attr = {
            'setting-name': 'gsm',
            'setting-key': 'password',
            'connection-uuid': str(uuid)
        }

        try:
            import gnomekeyring as gk

            # Search all the keyrings for it, not just default
            items = gk.find_items_sync(gk.ITEM_GENERIC_SECRET, attr)
            return items[0].secret

        except (ImportError, IndexError, gk.IOError, gk.NoMatchError):
            return None

    def _keyring_get_callback(self, uuid):
        # Getting the secrets probably will need to be obtained from Gnome Keyring
        # directly on NM 0.8.4 as the DBus config usually restricts the secrets
        # access to root only
        print "NM084ProfileManager::_keyring_get_callback()"

        try:
            secrets = self.nm_profiles[uuid].GetSecrets('gsm', ['password',], True,
                                    dbus_interface=NM084_SETTINGS_CONNECTION_SECRETS)
            print "NM084ProfileManager::_keyring_get_callback() got secrets from NM"
            return transpose_from_NM(secrets)

        except KeyError:
            # XXX: ideally we'd return None, but callers may expect
            return {u'gsm': {u'passwd': u'not found'}}

        except dbus.exceptions.DBusException, e:
            if 'AccessDenied' in str(e):
                print "NM084ProfileManager::_keyring_get_callback() DBus config prevents access to secrets"
            else:
                print str(e)

            passwd = self._get_secrets_gnome(uuid)
            if passwd is not None:
                return {u'gsm': {u'passwd': unicode(passwd)}}

            # XXX: TODO, try KDE's keyring, kwallet

            # XXX: ideally we'd return None, but callers may expect
            return {u'gsm': {u'passwd': u'not found'}}

    def _get_next_free_gpath(self):
        """Returns the next unused slot of /system/networking/connections"""
        all_dirs = list(self.helper.client.all_dirs(GCONF_PROFILES_BASE))
        try:
            max_index = max(map(int, [d.split('/')[-1] for d in all_dirs]))
        except ValueError:
            # /system/networking/connections is empty
            max_index = -1

        index = 0 if not all_dirs else max_index + 1
        return os.path.join(GCONF_PROFILES_BASE, str(index))

    def _write_NM_connection_to_gconf(self, path, props):
        for key in props:
            for name in props[key]:
                value = props[key][name]
                _path = os.path.join(path, key, name)

                self.helper.set_value(_path, value)

        self.helper.client.notify(path)
        self.helper.client.suggest_sync()

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        log.msg("Creating a new NM connection profile in GConf")

        props = transpose_to_NM(props)

        # AddConnection(props) never got implemented in NM 0.8x
        # So we need to write to gconf and wait for the applet to notice
        next_gpath = self._get_next_free_gpath()
        self._write_NM_connection_to_gconf(next_gpath, props)

        # The rest will be handled by _on_new_nm_profile when the signal
        # arrives


class NM09ProfileManager(NMLaterProfileManager):

    def __init__(self):
        super(NM09ProfileManager, self).__init__()

        self.keyring_manager = DummyKeyringManager(self._keyring_get_callback,
                                                    self._keyring_set_callback)
        # profile class to create
        self.NM_PROFILE_KLASS = NM09Profile

        # connect to signals
        self._connect_to_signals()

    def _init_nm_manager(self):
        # define DBus details
        self.NM_SETTINGS = NM09_SETTINGS
        self.NM_SETTINGS_OBJ = NM09_SETTINGS_OBJ
        self.NM_SETTINGS_INT = NM09_SETTINGS_INT
        self.NM_SETTINGS_CONNECTION = NM09_SETTINGS_CONNECTION

        super(NM09ProfileManager, self)._init_nm_manager()

    def _keyring_get_callback(self, uuid):
        # On NM0.9 we can get the secrets directly from the network manager
        # service
        try:
            secrets = self.nm_profiles[uuid].GetSecrets('gsm',
                                    dbus_interface=self.NM_SETTINGS_CONNECTION)
        except (KeyError, dbus.exceptions.DBusException):
            # XXX: ideally we'd return None, but callers may expect
            return {u'gsm': {u'passwd': u'not found'}}
        else:
            return transpose_from_NM(secrets)

    def add_profile(self, props):
        """Adds a profile with settings ``props``"""
        log.msg("Asking NM to create new connection profile")

        props = transpose_to_NM(props)

        # In NM 0.9 this finally got implemented
        self.nm_manager.AddConnection(props)

        # The rest will be handled by _on_new_nm_profile when the signal
        # arrives


class NetworkManagerBackend(object):

    implements(IBackend)

    def __init__(self):
        self.bus = dbus.SystemBus()
        self._nm08_core_present = None
        self._nm08_applet_present = None
        self._nm084_present = None
        self._nm09_present = None
        self._profile_manager = None
        self._keyring_manager = None

    def _is_nm08_core_present(self):
        if self._nm08_core_present is None:
            try:
                obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
                devices = obj.GetDevices()
                if len(devices):
                    self._nm08_core_present = 'NetworkManager' in devices[0]
                else:
                    self._nm08_core_present = False
            except dbus.DBusException:
                self._nm08_core_present = False

        return self._nm08_core_present

    def _is_nm08_applet_present(self):
        if self._nm08_applet_present is None:
            try:
                self.bus.get_object(NM08_USER_SETTINGS,
                                    NM08_SYSTEM_SETTINGS_OBJ)
                self._nm08_applet_present = True
            except dbus.DBusException:
                self._nm08_applet_present = False

        return self._nm08_applet_present

    def _is_nm08_present(self):
        return all([self._is_nm08_core_present(),
                    self._is_nm08_applet_present()])

    def _is_nm084_present(self):
        if self._nm084_present is None:
            try:
                # NM 0.8.4 core now provides a version property
                obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
                iface = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                ver = iface.Get(NM_INTFACE, "Version")
                if ver.startswith('0.8.4') or ver.startswith('0.8.3.99'):
                    self._nm084_present = True
                else:
                    self._nm084_present = False
            except dbus.DBusException:
                self._nm084_present = False

        return self._nm084_present

    def _is_nm09_present(self):
        if self._nm09_present is None:
            try:
                # NM 0.9 core now provides a version property
                obj = self.bus.get_object(NM_SERVICE, NM_OBJPATH)
                iface = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
                ver = iface.Get(NM_INTFACE, "Version")
                if ver.startswith('0.9') or ver.startswith('0.8.99'):
                    self._nm09_present = True
                else:
                    self._nm09_present = False
            except dbus.DBusException:
                self._nm09_present = False

        return self._nm09_present

    def _get_version(self):
        """
        There may be some crossover between the _is_nmXX_present()
        functions. Using this function evaluates version in the
        correct order.
        """
        if self._is_nm09_present():
            return '09'
        if self._is_nm084_present():
            return '084'
        if self._is_nm08_present():
            return '08'
        return None

    def should_be_used(self):
        """
        Returns True if:
            NM084 or NM09 is present
        or
            Both NM08 core and UI applet are present
        """
        return self._get_version() is not None

    def get_dialer_klass(self, device):
        if self._get_version() == '08':
            return NM08Dialer
        elif self._get_version() == '084':
            return NM08Dialer
        else:
            return NM09Dialer

    def get_keyring(self):
        # XXX: should be called get_keyring_manager

        if self._keyring_manager is None:
            if self._get_version() == '08':
                self._keyring_manager = KeyringManager(GnomeKeyring())
            else:
                pm = self.get_profile_manager()
                self._keyring_manager = pm.keyring_manager

        return self._keyring_manager

    def get_profile_manager(self, arg=None):
        if self._profile_manager is None:
            if self._get_version() == '08':
                self._profile_manager = NM08ProfileManager()
            elif self._get_version() == '084':
                self._profile_manager = NM084ProfileManager()
            else:
                self._profile_manager = NM09ProfileManager()

        return self._profile_manager


nm_backend = NetworkManagerBackend()
