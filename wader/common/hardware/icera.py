# -*- coding: utf-8 -*-
# Copyright (C) 2009  Vodafone España, S.A.
# Author:  Andrew Bird
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
Common stuff for all ZTE's Icera based cards
"""

import re
from twisted.internet import defer, reactor
from twisted.python import log

from wader.common import consts
import wader.common.aterrors as E
from wader.common.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.exported import HSOExporter
from wader.common.sim import SIMBaseClass
from wader.common.statem.simple import SimpleStateMachine
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict
import wader.common.signals as S
from wader.contrib.modal import mode as Mode

HSO_MAX_RETRIES = 10
HSO_RETRY_TIMEOUT = 3

ICERA_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: 5,
    consts.MM_ALLOWED_MODE_2G_ONLY: 0,
    consts.MM_ALLOWED_MODE_3G_ONLY: 1,
    consts.MM_ALLOWED_MODE_2G_PREFERRED: 2,
    consts.MM_ALLOWED_MODE_3G_PREFERRED: 3,
}

ICERA_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY: 5,
    consts.MM_NETWORK_MODE_2G_ONLY: 0,
    consts.MM_NETWORK_MODE_3G_ONLY: 1,
    consts.MM_NETWORK_MODE_2G_PREFERRED: 2,
    consts.MM_NETWORK_MODE_3G_PREFERRED: 3,
}

ICERA_BAND_DICT = {
}

ICERA_CMD_DICT = get_cmd_dict_copy()

# \r\n+CPBR: (1-200),80,14,0,0,0\r\n\r\nOK\r\n
ICERA_CMD_DICT['get_phonebook_size'] = build_cmd_dict(
    re.compile(r"""
        \r\n
        \+CPBR:\s
        \(\d+-(?P<size>\d+)\).*
        \r\n
    """, re.VERBOSE))

# \r\n+CMGL: 1,1,"616E64726577",23\r\n
# 0791447758100650040C9144977162470100009011503195310004D436390C\r\n
ICERA_CMD_DICT['list_sms'] = build_cmd_dict(
    re.compile(r"""
        \r\n
        \+CMGL:\s
        (?P<id>\d+),
        (?P<where>\d),
        (?P<alpha>"\w*?")?,
        \d+
        \r\n(?P<pdu>\w+)
    """, re.VERBOSE))

# \r\n%IPSYS: 1,2\r\n
ICERA_CMD_DICT['get_network_mode'] = build_cmd_dict(
    re.compile(r"""
        %IPSYS:\s
        (?P<mode>\d+),
        (?P<domain>\d+)
    """, re.VERBOSE))

# %IPDPADDR:<cid>,<ip>,<gw>,<dns1>,<dns2>[,<nbns1>,<nbns2>]\r\n
ICERA_CMD_DICT['get_ip4_config'] = build_cmd_dict(
    re.compile(r"""
        %IPDPADDR:
        \s*(?P<cid>\d+),
        \s*(?P<ip>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+),
        \s*(?P<gw>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+),
        \s*(?P<dns1>[0-9.]*),
        \s*(?P<dns2>[0-9.]*)
        (?P<ign>.*|,.*)
    """, re.VERBOSE))

ICERA_CMD_DICT['hso_authenticate'] = build_cmd_dict()

ICERA_CONN_DICT_REV = {
    '2G-GPRS': consts.MM_NETWORK_MODE_GPRS,
    '2G-EDGE': consts.MM_NETWORK_MODE_EDGE,
    '3G': consts.MM_NETWORK_MODE_UMTS,
    '3G-HSDPA': consts.MM_NETWORK_MODE_HSDPA,
    '3G-HSUPA': consts.MM_NETWORK_MODE_HSUPA,
    '3G-HSDPA-HSUPA': consts.MM_NETWORK_MODE_HSPA,
}


def icera_new_conn_mode(args):
    if not args:
        return consts.MM_NETWORK_MODE_UNKNOWN

    # ['4', '23415', '3G-HSDPA', '-', '0']
    rssi, network, tech, connected, regulation = args.split(',')

    if tech in ICERA_CONN_DICT_REV:
        return ICERA_CONN_DICT_REV[tech]
    else:
        # ['0', '2g', '3g'] '*g' == only C/S attached
        return consts.MM_NETWORK_MODE_UNKNOWN


class IceraSIMClass(SIMBaseClass):
    """
    Icera SIM Class

    I perform an initial setup in the device
    """

    def __init__(self, sconn):
        super(IceraSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):
        self.sconn.reset_settings()
        self.sconn.disable_echo()

        d = super(IceraSIMClass, self).initialize(set_encoding=set_encoding)

        def init_callback(size):
            # setup SIM storage defaults
            d = self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            # turn on unsolicited network notifications
            d.addCallback(lambda _: self.sconn.send_at('AT%NWSTATE=1'))
            d.addCallback(lambda _: size)
            return d

        d.addCallback(init_callback)
        return d


class IceraWrapper(WCDMAWrapper):
    """Wrapper for all ZTE Icera based cards"""

    def enable_radio(self, enable):
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                return self.send_at('AT+CFUN=1')

            elif status in [1, 5, 6] and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_band(self):
        return defer.succeed(consts.MM_NETWORK_BAND_ANY)

    def get_network_mode(self):
        """Returns the current network mode"""

        def get_network_mode_cb(resp):
            mode = int(resp[0].group('mode'))
            ICERA_MODE_DICT_REV = revert_dict(self.custom.conn_dict)
            if mode in ICERA_MODE_DICT_REV:
                return ICERA_MODE_DICT_REV[mode]

            raise KeyError("Unknown network mode %s" % mode)

        d = self.send_at('AT%IPSYS?', name='get_network_mode',
                         callback=get_network_mode_cb)
        return d

    def set_band(self, band):
        if band == consts.MM_NETWORK_BAND_ANY:
            return defer.succeed('OK')

        raise KeyError("Unsupported band %d" % band)

    def set_allowed_mode(self, mode):
        if mode not in self.custom.allowed_dict:
            raise KeyError("Mode %s not found" % mode)

        if self.device.get_property(consts.NET_INTFACE, "AllowedMode") == mode:
            # NOOP
            return defer.succeed("OK")

        def set_allowed_mode_cb(orig=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return orig

        return self.send_at("AT%%IPSYS=%d" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        # Note: Icera devices drop signal and network acquisition on bearer
        #       preference set. This causes the connection sequence to take
        #       7 secs instead of 2. So we test for current value and only
        #       set if required. Perhaps a similar thing will happen on
        #       band set, but as there are no bands defined for Icera at
        #       the moment, the band set is a no-op.
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %s not found" % mode)

        d = self.get_network_mode()

        def get_network_mode_cb(_mode):
            if _mode == mode:
                return defer.succeed('OK')

            return self.send_at("AT%%IPSYS=%d" % self.custom.conn_dict[mode])

        d.addCallback(get_network_mode_cb)
        return d

    def get_ip4_config(self):
        """
        Returns the ip4 config on a NDIS device

        Wrapper around _get_ip4_config that provides some error control
        """
        ip_method = self.device.get_property(consts.MDM_INTFACE, 'IpMethod')
        if ip_method != consts.MM_IP_METHOD_STATIC:
            msg = "Cannot get IP4 config from a non static ip method"
            raise E.OperationNotSupported(msg)

        self.state_dict['retry_call'] = None
        self.state_dict['num_of_retries'] = 0

        def real_get_ip4_config(deferred):

            def get_ip4_eb(failure):
                failure.trap(E.GenericError)
                if self.state_dict.get('should_stop'):
                    self.state_dict.pop('should_stop')
                    return

                self.state_dict['num_of_retries'] += 1
                if self.state_dict['num_of_retries'] > HSO_MAX_RETRIES:
                    return failure

                self.state_dict['retry_call'] = reactor.callLater(
                        HSO_RETRY_TIMEOUT,
                        real_get_ip4_config, deferred)

            d = self._get_ip4_config()
            d.addCallback(deferred.callback)
            d.addErrback(get_ip4_eb)
            return deferred

        auxdef = defer.Deferred()
        return real_get_ip4_config(auxdef)

    def _get_ip4_config(self):
        """Returns the ip4 config on a Icera NDIS device"""
        conn_id = self.state_dict.get('conn_id')
        if conn_id is None:
            raise E.CallIndexError("conn_id is None")

        cmd = ATCmd('AT%%IPDPADDR=%d' % conn_id, name='get_ip4_config')
        d = self.queue_at_cmd(cmd)

        def _get_ip4_config_cb(resp):
            if not resp:
                raise E.GenericError()

            ip, dns1 = resp[0].group('ip'), resp[0].group('dns1')
            # XXX: Fix dns3
            dns2 = dns3 = resp[0].group('dns2')
            self.device.set_status(consts.DEV_CONNECTED)
            return [ip, dns1, dns2, dns3]

        d.addCallback(_get_ip4_config_cb)
        return d

    def hso_authenticate(self, user, passwd, auth):
        """Authenticates using ``user`` and ``passwd`` on Icera NDIS devices"""
        conn_id = self.state_dict.get('conn_id')
        if conn_id is None:
            raise E.CallIndexError("conn_id is None")

        args = (conn_id, auth, user, passwd)
        cmd = ATCmd('AT%%IPDPCFG=%d,0,%d,"%s","%s"' % args,
                    name='hso_authenticate')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda resp: resp[0].group('resp'))
        return d

    def hso_connect(self):
        conn_id = self.state_dict.get('conn_id')
        if conn_id is None:
            raise E.CallIndexError("conn_id is None")

        return self.send_at('AT%%IPDPACT=%d,1' % conn_id)

    def disconnect_from_internet(self):
        """
        meth:`~wader.common.middleware.WCDMAWrapper.disconnect_from_internet`
        """
        conn_id = self.state_dict.get('conn_id')
        if conn_id is None:
            raise E.CallIndexError("conn_id is None")

        d = self.send_at('AT%%IPDPACT=%d,0' % conn_id)
        d.addCallback(lambda _: self.device.set_status(consts.DEV_ENABLED))
        return d


# XXX: maybe we can see about sharing this once SimpleConnect is working
class IceraSimpleStateMachine(SimpleStateMachine):
    begin = SimpleStateMachine.begin
    check_pin = SimpleStateMachine.check_pin
    register = SimpleStateMachine.register
    set_apn = SimpleStateMachine.set_apn
    set_band = SimpleStateMachine.set_band
    set_network_mode = SimpleStateMachine.set_network_mode
    done = SimpleStateMachine.done

    class connect(Mode):

        def __enter__(self):
            log.msg("Icera Simple SM: connect entered")

        def __exit__(self):
            log.msg("Icera Simple SM: connect exited")

        def do_next(self):
            username = self.settings['username']
            password = self.settings['password']
            # XXX: One day Connect.Simple will receive auth too
            # defaulting to PAP_AUTH as that's what we had before
            auth = consts.HSO_PAP_AUTH

            d = self.sconn.hso_authenticate(username, password, auth)
            d.addCallback(lambda _: self.sconn.hso_connect())
            d.addCallback(lambda _: self.transition_to('done'))


class IceraWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for ZTE Icera based devices"""
    async_regexp = re.compile("""
                    \r\n
                    (?P<signal>%[A-Z]{3,}):\s*(?P<args>.*)
                    \r\n""", re.VERBOSE)
    allowed_dict = ICERA_ALLOWED_DICT
    band_dict = ICERA_BAND_DICT
    conn_dict = ICERA_MODE_DICT
    cmd_dict = ICERA_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE]
    signal_translations = {
        '%NWSTATE': (S.SIG_NETWORK_MODE, icera_new_conn_mode),
    }
    wrapper_klass = IceraWrapper
    exporter_klass = HSOExporter
    simp_klass = IceraSimpleStateMachine


class IceraWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for ZTE Icera based devices"""
    sim_klass = IceraSIMClass
    custom = IceraWCDMACustomizer()
