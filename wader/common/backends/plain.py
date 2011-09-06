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
import tempfile
import re
import shutil
from signal import SIGTERM, SIGKILL
from string import Template

import dbus
from dbus.service import signal, Object, BusName
from twisted.internet import reactor, defer, protocol, error, task
from twisted.python import log, procutils
from zope.interface import implements

from wader.common.consts import (WADER_PROFILES_SERVICE,
                                 WADER_PROFILES_INTFACE,
                                 WADER_PROFILES_OBJPATH,
                                 APP_NAME, FALLBACK_DNS, MDM_INTFACE,
                                 HSO_CHAP_AUTH, HSO_NO_AUTH, HSO_PAP_AUTH,
                                 MM_MODEM_STATE_REGISTERED,
                                 MM_MODEM_STATE_CONNECTING,
                                 MM_MODEM_STATE_DISCONNECTING,
                                 MM_MODEM_STATE_CONNECTED,
                                 MM_SYSTEM_SETTINGS_PATH)
from wader.common.dialer import Dialer
import wader.common.exceptions as ex
from wader.common.interfaces import IBackend, IProfileManagerBackend
from wader.common.keyring import (KeyringManager, KeyringInvalidPassword,
                                  KeyringIsClosed, KeyringNoMatchError)
from wader.common.oal import get_os_object
from wader.common.profile import Profile
from wader.common.secrets import ProfileSecrets
from wader.common.utils import save_file, is_bogus_ip, patch_list_signature
from wader.contrib import aes


def proc_running(pid):
    try:
        pid = int(pid)
    except ValueError:
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


def validate_dns(dynamic, use_static, static):

    if use_static:
        valid_dns = [addr for addr in static if addr]
    else:
        # If static DNS is not set, then we should use the DNS returned by the
        # network, but let's check if they're valid DNS IPs
        valid_dns = [addr for addr in dynamic if not is_bogus_ip(addr)]

    if len(valid_dns):
        return True, valid_dns

    # The DNS assigned by the network is invalid or missing, or the static
    # addresses are missing, so notify the user and fallback to Google etc
    return False, FALLBACK_DNS

WVDIAL_PPPD_OPTIONS = os.path.join('/etc', 'ppp', 'peers', 'wvdial')
WVDIAL_RETRIES = 3
WVTEMPLATE = """
[Dialer Defaults]

Phone = $phone
Username = $username
Password = $password
Stupid Mode = 1
Dial Command = ATDT
New PPPD = yes
Check Def Route = on
Dial Attempts = 3
Auto Reconnect = off
Auto DNS = on

[Dialer connect]

Modem = $serialport
Baud = 460800
Init2 = ATZ
Init3 = ATQ0 V1 E0 S0=0 &C1 &D2
Init4 = AT+CGDCONT=$context,"IP","$apn"
ISDN = 0
Modem Type = Analog Modem
"""

CONNECTED_REGEXP = re.compile('Connected\.\.\.')
PPPD_PID_REGEXP = re.compile('Pid of pppd: (?P<pid>\d+)')
PPPD_IFACE_REGEXP = re.compile('Using interface (?P<iface>ppp\d+)')
MAX_ATTEMPTS_REGEXP = re.compile('Maximum Attempts Exceeded')
PPPD_DIED_REGEXP = re.compile('The PPP daemon has died')
DNS_REGEXP = re.compile(r"""
   DNS\saddress
   \s                                     # beginning of the string
   (?P<ip>                                # group named ip
   (25[0-5]|                              # integer range 250-255 OR
   2[0-4][0-9]|                           # integer range 200-249 OR
   [01]?[0-9][0-9]?)                      # any number < 200
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   \.                                     # matches '.'
   (25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?) # repeat
   )                                      # end of group
   \b                                     # end of the string
   """, re.VERBOSE)


DEFAULT_TEMPLATE = """
debug
noauth
name wvdial
noipdefault
nomagic
ipcp-accept-local
ipcp-accept-remote
nomp
noccp
nopredictor1
novj
novjccomp
nobsdcomp"""

PAP_TEMPLATE = DEFAULT_TEMPLATE + """
refuse-chap
refuse-mschap
refuse-mschap-v2
refuse-eap
"""

CHAP_TEMPLATE = DEFAULT_TEMPLATE + """
refuse-pap
"""


def get_wvdial_conf_file(conf, context, serial_port):
    """
    Returns the path of the generated wvdial.conf

    :param conf: `DialerConf` instance
    :param serial_port: The port to use
    :rtype: str
    """
    text = _generate_wvdial_conf(conf, context, serial_port)
    dirpath = tempfile.mkdtemp('', APP_NAME, '/tmp')
    path = tempfile.mkstemp('wvdial.conf', APP_NAME, dirpath, True)[1]
    save_file(path, text)
    return path


def _generate_wvdial_conf(conf, context, sport):
    """
    Generates a specially crafted wvdial.conf with `conf` and `sport`

    :param conf: `DialerConf` instance
    :param sport: The port to use
    :rtype: str
    """
    user = conf.username if conf.username else '*'
    passwd = conf.password if conf.password else '*'
    theapn = conf.apn

    # build template
    data = StringIO(WVTEMPLATE)
    template = Template(data.getvalue())
    data.close()
    # construct number
    number = '*99***%d#' % context
    # return template
    props = dict(serialport=sport, username=user, password=passwd,
                 context=context, apn=theapn, phone=number)
    return template.substitute(props)


class WVDialDialer(Dialer):
    """Dialer for WvDial"""

    binary = 'wvdial'

    def __init__(self, device, opath, **kwds):
        super(WVDialDialer, self).__init__(device, opath, **kwds)
        try:
            self.bin_path = procutils.which(self.binary)[0]
        except IndexError:
            self.bin_path = '/usr/bin/wvdial'

        self.backup_path = ""
        self.conf = None
        self.conf_path = ""
        self.dirty = False
        self.proto = None
        self.iconn = None
        self.iface = 'ppp0'
        self.should_stop = False
        self.attempting_connect = False

    def Connected(self):
        self.device.set_status(MM_MODEM_STATE_CONNECTED)
        self.attempting_connect = False
        super(WVDialDialer, self).Connected()

    def Disconnected(self):
        if self.device.status >= MM_MODEM_STATE_REGISTERED:
            self.device.set_status(MM_MODEM_STATE_REGISTERED)
        self.attempting_connect = False
        super(WVDialDialer, self).Disconnected()

    def configure(self, config):
        self.dirty = True

        def get_context_id(ign):
            conn_id = self.device.sconn.state_dict.get('conn_id')
            try:
                context = int(conn_id)
            except ValueError:
                raise Exception('WVDialDialer context id is "%s"' %
                                str(conn_id))
            return context

        d = self.device.sconn.set_apn(config.apn)
        d.addCallback(get_context_id)
        d.addCallback(lambda context: self._generate_config(config, context))
        return d

    def connect(self):
        if self.should_stop:
            self.should_stop = False
            return

        self.device.set_status(MM_MODEM_STATE_CONNECTING)
        self.attempting_connect = True

        self.proto = WVDialProtocol(self)
        args = [self.binary, '-C', self.conf_path, 'connect']
        self.iconn = reactor.spawnProcess(self.proto, args[0], args, env=None)
        return self.proto.deferred

    def stop(self):
        self.should_stop = True
        self.attempting_connect = False
        return self.disconnect()

    def disconnect(self):
        if self.proto is None:
            return defer.succeed(self.opath)

        self.device.set_status(MM_MODEM_STATE_DISCONNECTING)

        msg = 'WVdial failed to connect'

        def get_pppd_pid():
            pid_file = "/var/run/%s.pid" % self.iface

            if not os.path.exists(pid_file):
                return False

            pid = None
            with open(pid_file) as f:
                pid = f.read()
            return pid

        def cleanup_pppd():
            if self.attempting_connect:
                self.proto.deferred.errback(RuntimeError(msg))

            pppd_pid = get_pppd_pid()
            if not signal_process('pppd', pppd_pid, SIGTERM):
                # process was already gone
                d = defer.succeed(self._cleanup())
            else:
                d = task.deferLater(reactor, 5,
                            signal_process, 'pppd', pppd_pid, SIGKILL)
                d.addCallback(lambda _: self._cleanup())
            return d

        # tell wvdial to quit
        try:
            self.proto.transport.signalProcess('TERM')
        except error.ProcessExitedAlready:
            log.msg("wvdial: wvdial exited")

        # just be damn sure that we're killing everything
        wvdial_pid = proc_running(self.proto.pid)
        if not wvdial_pid:
            # process was already gone
            d = cleanup_pppd()
        else:
            d = task.deferLater(reactor, 5,
                            signal_process, 'wvdial', wvdial_pid, SIGKILL)
            d.addCallback(lambda _: cleanup_pppd())

        d.addCallback(lambda _: self.opath)
        return d

    def _generate_config(self, conf, context):
        # backup wvdial configuration
        self.backup_path = self._backup_conf()
        self.conf = conf
        # generate auth configuration
        self._generate_wvdial_ppp_options()
        # generate wvdial.conf from template
        port = self.device.ports.dport
        self.conf_path = get_wvdial_conf_file(self.conf, context, port.path)

    def _cleanup(self, ignored=None):
        """cleanup our traces"""
        if not self.dirty:
            return

        try:
            path = os.path.dirname(self.conf_path)
            os.unlink(self.conf_path)
            os.rmdir(path)
        except (IOError, OSError):
            pass

        self._restore_conf()

    def _generate_wvdial_ppp_options(self):
        if not self.conf.refuse_chap:
            wvdial_ppp_options = CHAP_TEMPLATE
        elif not self.conf.refuse_pap:
            wvdial_ppp_options = PAP_TEMPLATE
        else:
            # this could be a NOOP, but the user might have modified
            # the stock /etc/ppp/peers/wvdial file, so the safest option
            # is to overwrite with our known good options.
            wvdial_ppp_options = DEFAULT_TEMPLATE

        # There are some patched pppd implementations
        # Most systems offer 'replacedefaultroute', but not Fedora
        osobj = get_os_object()
        if hasattr(osobj, 'get_additional_wvdial_ppp_options'):
            wvdial_ppp_options += osobj.get_additional_wvdial_ppp_options()

        save_file(WVDIAL_PPPD_OPTIONS, wvdial_ppp_options)

    def _backup_conf(self):
        path = tempfile.mkstemp('wvdial', APP_NAME)[1]
        try:
            shutil.copy(WVDIAL_PPPD_OPTIONS, path)
            return path
        except IOError:
            return None

    def _restore_conf(self):
        if self.backup_path:
            shutil.copy(self.backup_path, WVDIAL_PPPD_OPTIONS)
            os.unlink(self.backup_path)
            self.backup_path = None

    def _set_iface(self, iface):
        self.iface = iface


class WVDialProtocol(protocol.ProcessProtocol):
    """ProcessProtocol for wvdial"""

    def __init__(self, dialer):
        self.dialer = dialer
        self.__connected = False
        self.pid = None
        self.retries = 0
        self.deferred = defer.Deferred()
        self.dns = []

    def connectionMade(self):
        self.transport.closeStdin()

    def outReceived(self, data):
        log.msg("wvdial: sysout %s" % data)

    def errReceived(self, data):
        """wvdial has this bad habit of using stderr for debug"""
        log.msg("wvdial: %r" % data)
        self._parse_output(data)

    def outConnectionLost(self):
        log.msg('wvdial: wvdial closed its stdout!')

    def errConnectionLost(self):
        log.msg('wvdial: wvdial closed its stderr.')

    def processEnded(self, status_object):
        log.msg('wvdial: quitting')

        if not self.__connected:
            self.dialer.disconnect()

        self._set_disconnected(force=True)

    def processExited(self, status):
        log.msg('wvdial: wvdial processExited')

    def _set_connected(self):
        if self.__connected:
            return

        valid, dns = validate_dns(self.dns, self.dialer.conf.staticdns,
                                [self.dialer.conf.dns1, self.dialer.conf.dns2])
        if not valid:
            if self.dialer.conf.staticdns:
                self.dialer.InvalidDNS([])
            else:
                self.dialer.InvalidDNS(self.dns)

        osobj = get_os_object()
        osobj.add_dns_info(dns, self.dialer.iface)

        self.__connected = True
        self.dialer.Connected()
        self.deferred.callback(self.dialer.opath)

    def _set_disconnected(self, force=False):
        if not self.__connected and not force:
            return

        osobj = get_os_object()
        osobj.delete_dns_info(self.dialer.iface)

        self.__connected = False
        self.dialer.Disconnected()

    def _extract_iface(self, data):
        match = PPPD_IFACE_REGEXP.search(data)
        if match:
            self.dialer._set_iface(match.group('iface'))
            log.msg("wvdial: dialer interface %s" % self.dialer.iface)

    def _extract_dns_strings(self, data):
        for match in re.finditer(DNS_REGEXP, data):
            self.dns.append(match.group('ip'))

    def _extract_connected(self, data):
        if CONNECTED_REGEXP.search(data):
            self._set_connected()

    def _extract_disconnected(self, data):
        # more than three attempts
        max_attempts = MAX_ATTEMPTS_REGEXP.search(data)
        # pppd died
        pppd_died = PPPD_DIED_REGEXP.search(data)

        if max_attempts or pppd_died:
            self._set_disconnected()

    def _extract_tries(self, data):
        # force wvdial to stop after three attempts
        if self.retries >= WVDIAL_RETRIES:
            self.dialer.disconnect()
            self._set_disconnected()
            return

        # extract pppd pid
        match = PPPD_PID_REGEXP.search(data)
        if match:
            self.pid = int(match.group('pid'))
            self.retries += 1
            log.msg("wvdial: dialer tries %d" % self.retries)

    def _parse_output(self, data):
        self._extract_iface(data)
        self._extract_dns_strings(data)

        if not self.__connected:
            self._extract_connected(data)
        else:
            self._extract_disconnected(data)

        self._extract_tries(data)


class HSODialer(Dialer):
    """Dialer for HSO type devices"""
    # Note: The interface is called HSO for historical reasons but actually
    #       it can be used by devices other than Option's e.g. ZTE's Icera

    def __init__(self, device, opath, **kwds):
        super(HSODialer, self).__init__(device, opath, **kwds)
        self.iface = self.device.get_property(MDM_INTFACE, 'Device')
        self.conf = None

    def configure(self, config):
        self.conf = config

        if not config.refuse_chap:
            auth = HSO_CHAP_AUTH
        elif not config.refuse_pap:
            auth = HSO_PAP_AUTH
        else:
            auth = HSO_NO_AUTH

        d = self.device.sconn.set_apn(config.apn)
        d.addCallback(lambda _: self.device.sconn.hso_authenticate(
                                       config.username, config.password, auth))
        return d

    def connect(self):
        # start the connection
        d = self.device.sconn.hso_connect()
        # now get the IP4Config and set up device and routes
        d.addCallback(lambda _: self.device.sconn.get_ip4_config())
        d.addCallback(self._get_ip4_config_cb)
        d.addCallback(lambda _: self.Connected())
        d.addCallback(lambda _: self.opath)
        return d

    def _get_ip4_config_cb(self, (ip, dns1, dns2, dns3)):
        valid, dns = validate_dns([dns1, dns2, dns3], self.conf.staticdns,
                                    [self.conf.dns1, self.conf.dns2])
        if not valid:
            if self.conf.staticdns:
                self.InvalidDNS([])
            else:
                self.InvalidDNS(self.dns)

        osobj = get_os_object()
        d = osobj.configure_iface(self.iface, ip, 'up')
        d.addCallback(lambda _: osobj.add_default_route(self.iface))
        d.addCallback(lambda _: osobj.add_dns_info(dns, self.iface))
        return d

    def disconnect(self):
        d = self.device.sconn.disconnect_from_internet()
        osobj = get_os_object()
        osobj.delete_default_route(self.iface)
        osobj.delete_dns_info(None, self.iface)
        osobj.configure_iface(self.iface, '', 'down')
        d.addCallback(lambda _: self.Disconnected())
        return d

    def stop(self):
        # set internal flag in device for disconnection
        self.device.sconn.state_dict['should_stop'] = True
        return self.disconnect()


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

        pickledobj = aes.decryptData(self.key, data)
        try:
            return pickle.load(StringIO(pickledobj))
        except:
            raise KeyringNoMatchError("bad password")

    def update(self, uuid, conn_id, secrets, update=True):
        path = os.path.join(self.secrets_path, uuid)
        with open(path, 'w') as f:
            data = aes.encryptData(self.key, pickle.dumps(secrets))
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
        if device.dialer in ['hso']:
            return HSODialer

        return WVDialDialer

    def get_keyring(self, secrets_path):
        if self._keyring is None:
            self._keyring = KeyringManager(PlainKeyring(secrets_path))

        return self._keyring

    def get_profile_manager(self, arg=None):
        if self._profile_manager is None:
            self._profile_manager = PlainProfileManager(arg)

        return self._profile_manager


plain_backend = PlainBackend()
