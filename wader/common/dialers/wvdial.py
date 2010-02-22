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
"""WvDial Dialer"""

from cStringIO import StringIO
import os
import re
import shutil
from string import Template
import tempfile

from twisted.internet import utils, reactor, defer, protocol, error
from twisted.python import log, procutils

import wader.common.consts as consts
from wader.common.dialer import Dialer
from wader.common.utils import get_file_data, save_file, is_bogus_ip

WVDIAL_CONF = os.path.join('/etc', 'ppp', 'peers', 'wvdial')
WVDIAL_RETRIES = 3

DEFAULT_TEMPLATE = """
debug
noauth
name wvdial
replacedefaultroute
noipdefault
nomagic
usepeerdns
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


def get_wvdial_conf_file(conf, serial_port):
    """
    Returns the path of the generated wvdial.conf

    :param conf: `DialerConf` instance
    :param serial_port: The port to use
    :rtype: str
    """
    text = _generate_wvdial_conf(conf, serial_port)
    dirpath = tempfile.mkdtemp('', consts.APP_NAME, '/tmp')
    path = tempfile.mkstemp('wvdial.conf', consts.APP_NAME, dirpath, True)[1]
    save_file(path, text)
    return path


def _generate_wvdial_conf(conf, sport):
    """
    Generates a specially crafted wvdial.conf with `conf` and `sport`

    :param conf: `DialerConf` instance
    :param sport: The port to use
    :rtype: str
    """
    user = conf.username
    passwd = conf.password
    theapn = conf.apn

    # build template
    data = StringIO(get_file_data(consts.WVTEMPLATE))
    template = Template(data.getvalue())
    data.close()
    # return template
    props = dict(serialport=sport, username=user, password=passwd, apn=theapn)
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
        self.proto = None
        self.iconn = None
        self.iface = 'ppp0'
        self.should_stop = False

    def configure(self, config):
        return defer.maybeDeferred(self._generate_config, config)

    def connect(self):
        if self.should_stop:
            self.should_stop = False
            return

        self.proto = WVDialProtocol(self)
        args = [self.binary, '-C', self.conf_path, 'connect']
        self.iconn = reactor.spawnProcess(self.proto, args[0], args, env=None)
        return self.proto.deferred

    def stop(self):
        self.should_stop = True
        return self.disconnect()

    def disconnect(self):
        if self.proto is None:
            return defer.succeed(self.opath)

        # ignore the fact that we are gonna be disconnected
        self.proto.ignore_disconnect = True

        try:
            self.proto.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            return defer.succeed(self.opath)

        # just be damn sure that we're killing everything
        if self.proto.pid:
            try:
                kill_path = procutils.which('kill')[0]
            except IndexError:
                kill_path = '/bin/kill'

            args = [kill_path, '-9', self.proto.pid]
            d = utils.getProcessValue(args[0], args, env=None)

            def disconnect_cb(error_code):
                log.msg("wvdial: exit code %d" % error_code)
                self._cleanup()
                return self.opath

            d.addCallback(disconnect_cb)
            return d
        else:
            self._cleanup()
            return defer.succeed(self.opath)

    def _generate_config(self, conf):
        # backup wvdial configuration
        self.backup_path = self._backup_conf()
        self.conf = conf
        # generate auth configuration
        self._generate_auth_config()
        # generate wvdial.conf from template
        port = self.device.ports.dport
        self.conf_path = get_wvdial_conf_file(self.conf, port.path)

    def _cleanup(self, ignored=None):
        """cleanup our traces"""
        try:
            path = os.path.dirname(self.conf_path)
            os.unlink(self.conf_path)
            os.rmdir(path)
        except (IOError, OSError):
            pass

        self._restore_conf()

    def _generate_auth_config(self):
        if not self.conf.refuse_chap:
            save_file(WVDIAL_CONF, CHAP_TEMPLATE)
        elif not self.conf.refuse_pap:
            save_file(WVDIAL_CONF, PAP_TEMPLATE)
        else:
            # this could be a NOOP, but the user might have modified
            # the stock /etc/ppp/peers/wvdial file, so the safest option
            # is to overwrite with our known good options.
            save_file(WVDIAL_CONF, DEFAULT_TEMPLATE)

    def _backup_conf(self):
        path = tempfile.mkstemp('wvdial', consts.APP_NAME)[1]
        try:
            shutil.copy(WVDIAL_CONF, path)
            return path
        except IOError:
            return None

    def _restore_conf(self):
        if self.backup_path:
            shutil.copy(self.backup_path, WVDIAL_CONF)
            os.unlink(self.backup_path)
            self.backup_path = None

    def _set_iface(self, iface):
        self.iface = iface
        if self.conf.staticdns:
            from wader.common.oal import get_os_object
            osobj = get_os_object()
            osobj.add_dns_info((self.conf.dns1, self.conf.dns2), iface)


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


class WVDialProtocol(protocol.ProcessProtocol):
    """ProcessProtocol for wvdial"""

    def __init__(self, dialer):
        self.dialer = dialer
        self.__connected = False
        self.pid = None
        self.retries = 0
        self.deferred = defer.Deferred()
        self.ignore_disconnect = False
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
        log.msg('wvdial: pppd closed their stdout!')

    def errConnectionLost(self):
        log.msg('wvdial: pppd closed their stderr.')

    def processEnded(self, status_object):
        log.msg('wvdial: quitting')
        if not self.__connected and not self.ignore_disconnect:
            self.dialer.disconnect()
            self.dialer.Disconnected()

    def _set_connected(self):
        if self.__connected:
            return

        self.__connected = True
        self.dialer.Connected()
        self.deferred.callback(self.dialer.opath)

    def _extract_iface(self, data):
        match = PPPD_IFACE_REGEXP.search(data)
        if match:
            self.dialer._set_iface(match.group('iface'))
            log.msg("wvdial: dialer interface %s" % self.dialer.iface)

    def _extract_dns_strings(self, data):
        if self.__connected:
            return

        for match in re.finditer(DNS_REGEXP, data):
            dns_ip = match.group('ip')
            self.dns.append(dns_ip)

            if len(self.dns) == 2:
                self._set_connected()

                # check if they're valid DNS ips
                if any(map(is_bogus_ip, self.dns)):
                    # the DNS assigned by the APN is probably invalid
                    # notify the user only if she didn't specify static DNS
                    self.dialer.InvalidDNS(self.dns)

    def _extract_connected(self, data):
        if self.__connected:
            return

        # extract pppd pid
        match = PPPD_PID_REGEXP.search(data)
        if match:
            self.pid = match.group('pid')
            self.retries += 1

        if CONNECTED_REGEXP.search(data):
            self._set_connected()

    def _extract_disconnected(self, data):
        # more than three attempts
        disconnected = MAX_ATTEMPTS_REGEXP.search(data)
        # pppd died
        pppd_died = PPPD_DIED_REGEXP.search(data)
        # wvdial refuses to stop after three attempts?

        if disconnected or pppd_died or self.retries >= WVDIAL_RETRIES:
            if not self.ignore_disconnect:
                self.__connected = False
                self.dialer.disconnect()
                self.dialer.Disconnected()

    def _parse_output(self, data):
        self._extract_iface(data)
        self._extract_dns_strings(data)
        if not self.__connected:
            self._extract_connected(data)
        else:
            self._extract_disconnected(data)
