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
"""Common stuff for all Option's datacards/devices"""

import re

from twisted.internet import defer, reactor

from wader.common import consts
import wader.common.aterrors as E
import wader.common.signals as S
from wader.common.utils import rssi_to_percentage, revert_dict

from core.command import get_cmd_dict_copy, build_cmd_dict, ATCmd
from core.exported import HSOExporter
from core.hardware.base import WCDMACustomizer
from core.middleware import WCDMAWrapper
from core.plugin import DevicePlugin
from core.sim import SIMBaseClass

NUM_RETRIES = 30
RETRY_TIMEOUT = 4

HSO_MAX_RETRIES = 10
HSO_RETRY_TIMEOUT = 3

OPTION_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: 5,
    consts.MM_ALLOWED_MODE_2G_PREFERRED: 2,
    consts.MM_ALLOWED_MODE_3G_PREFERRED: 3,
    consts.MM_ALLOWED_MODE_2G_ONLY: 0,
    consts.MM_ALLOWED_MODE_3G_ONLY: 1,
}

# The MM band dictionary was modelled after the Option band dict, but there are
# now some differences
OPTION_BAND_DICT = {
    consts.MM_NETWORK_BAND_ANY: 'ANY',
    consts.MM_NETWORK_BAND_EGSM: 'EGSM',
    consts.MM_NETWORK_BAND_DCS: 'DCS',
    consts.MM_NETWORK_BAND_PCS: 'PCS',
    consts.MM_NETWORK_BAND_G850: 'G850',
    consts.MM_NETWORK_BAND_U2100: 'U2100',
    consts.MM_NETWORK_BAND_U1800: 'U1700',  # Option calls this U1700
    consts.MM_NETWORK_BAND_U17IV: 'U17IV',
    consts.MM_NETWORK_BAND_U800: 'U800',
    consts.MM_NETWORK_BAND_U850: 'U850',
    consts.MM_NETWORK_BAND_U900: 'U900',
    consts.MM_NETWORK_BAND_U17IX: 'U17IX',
    consts.MM_NETWORK_BAND_U1900: 'U1900',
                                            # Option has no U2600
}

OPTION_CONN_DICT = {
    consts.MM_NETWORK_MODE_2G_ONLY: 0,
    consts.MM_NETWORK_MODE_3G_ONLY: 1,
    consts.MM_NETWORK_MODE_2G_PREFERRED: 2,
    consts.MM_NETWORK_MODE_3G_PREFERRED: 3,
    consts.MM_NETWORK_MODE_ANY: 5,
}

# Option devices like to append its serial number after the IMEI, ignore it
OPTION_CMD_DICT = get_cmd_dict_copy()
OPTION_CMD_DICT['get_imei'] = build_cmd_dict(re.compile(
                                    "\r\n(?P<imei>\d+),\S+\r\n", re.VERBOSE))

OPTION_CMD_DICT['get_sim_status'] = build_cmd_dict(re.compile(r"""
                                             _OBLS:\s(?P<sim>\d),
                                             (?P<contacts>\d),
                                             (?P<sms>\d)
                                             """, re.VERBOSE))

OPTION_CMD_DICT['get_band'] = build_cmd_dict(re.compile(r"""
                                             \r\n(?P<name>.*):\s+(?P<active>\d)
                                             """, re.VERBOSE))

# AT_OPBM=?
# _OPBM: ("ANY","EGSM","DCS","PCS","G850","U2100","U1900","U1700","U17IV",
#           "U850","U800","U900","U17IX")
OPTION_CMD_DICT['get_bands'] = build_cmd_dict(re.compile(r"""
                                             "(?P<name>[A-Za-z0-9]+)"(?:,|\))
                                             """, re.VERBOSE))

OPTION_CMD_DICT['get_network_mode'] = build_cmd_dict(re.compile(r"""
                                             _OPSYS:\s
                                             (?P<mode>\d),
                                             (?P<domain>\d)
                                             """, re.VERBOSE))

OPTION_CMD_DICT['hso_authenticate'] = build_cmd_dict()

OPTION_CMD_DICT['get_ip4_config'] = build_cmd_dict(re.compile(r"""
                                             \r\n
                                             _OWANDATA:\s
                                             (?P<cid>\d),\s
                                             (?P<ip>.*),\s
                                             (?P<ign1>.*),\s
                                             (?P<dns1>.*),\s
                                             (?P<dns2>.*),\s
                                             (?P<ign2>.*),\s
                                             (?P<ign3>.*),\s
                                             (?P<baud>\d+)
                                             \r\r\n""", re.X))


def option_new_mode(args, device):
    """
    Translates Option's unsolicited notifications to Wader's representation
    """
    ossysi_args_dict = {
        '0': consts.MM_NETWORK_MODE_GPRS,
        '2': consts.MM_NETWORK_MODE_UMTS,
        '3': consts.MM_NETWORK_MODE_UNKNOWN,
    }
    netmode = ossysi_args_dict.get(args, consts.MM_NETWORK_MODE_UNKNOWN)

    device.sconn.emit_network_mode(netmode)

    return None


def option_new_rssi(args, device):
    try:
        strength = rssi_to_percentage(int(args.split(',')[0]))
    except (ValueError, TypeError, IndexError):
        return None

    device.sconn.updatecache(strength, 'signal')
    device.sconn.emit_rssi(strength)
    return None


class OptionSIMClass(SIMBaseClass):
    """
    Option SIM Class

    I perform an initial setup in the device and will not
    return until the SIM is *really* ready
    """

    def __init__(self, sconn):
        super(OptionSIMClass, self).__init__(sconn)
        self.num_retries = 0

    def initialize(self, set_encoding=True):
        deferred = defer.Deferred()

        def init_callback(size):
            # make sure we aren't looking for a network that isn't available
            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            # setup asynchronous notifications
            self.sconn.send_at('AT_OSSYS=1')  # cell change notification
            self.sconn.send_at('AT_OSQI=1')   # signal quality notification
            deferred.callback(size)

        def sim_ready_cb(ignored):
            d2 = super(OptionSIMClass, self).initialize(set_encoding)
            d2.addCallback(init_callback)

        def sim_ready_eb(failure):
            deferred.errback(failure)

        d = self.is_sim_ready()
        d.addCallback(sim_ready_cb)
        d.addErrback(sim_ready_eb)

        return deferred

    def is_sim_ready(self):
        deferred = defer.Deferred()

        def process_sim_state(auxdef):

            def parse_response(resp):
                status = tuple(map(int, resp[0].groups()))
                if status == (1, 1, 1):
                    auxdef.callback(True)
                else:
                    self.num_retries += 1
                    if self.num_retries < NUM_RETRIES:
                        reactor.callLater(RETRY_TIMEOUT,
                                            process_sim_state, auxdef)
                    else:
                        msg = "Max number of attempts reached %d"
                        auxdef.errback(E.General(msg % self.num_retries))

                return

            self.sconn.send_at('AT_OBLS', name='get_sim_status',
                               callback=parse_response)

            return auxdef

        return process_sim_state(deferred)


class OptionWrapper(WCDMAWrapper):
    """Wrapper for all Option cards"""

    def _get_band_dict(self):
        """Returns a dict with the currently selected bands"""

        def callback(resp):
            bands = {}

            for r in resp:
                name, active = r.group('name'), int(r.group('active'))
                bands[name] = active

            return bands

        d = self.send_at('AT_OPBM?', name='get_band', callback=callback)
        return d

    def get_band(self):
        """Returns the current used band"""

        def get_band_dict_cb(current):
            if 'ANY' in current and current['ANY'] == 1:
                # can't be combined by design
                return consts.MM_NETWORK_BAND_ANY

            ret = 0
            for key, value in self.custom.band_dict.items():
                for name, active in current.items():
                    if name == value and active:
                        ret |= key
            return ret

        d = self._get_band_dict()
        d.addCallback(get_band_dict_cb)
        return d

    def get_bands(self):
        """
        Returns the supported bands from the device, but filtered to the set
        supported in the custom band_dict. This means we can remove any
        awkward bands from problematic devices e.g. K3760 / U2100
        """

        def callback(resp):
            bands = [r.group('name') for r in resp]

            ret = 0
            for key, value in self.custom.band_dict.items():
                if key == consts.MM_NETWORK_BAND_ANY:
                    # skip ANY
                    continue

                if value in bands:
                    ret |= key

            return ret

        return self.send_at('AT_OPBM=?', name='get_bands', callback=callback)

    def get_network_mode(self):
        """Returns the current network mode"""

        def get_network_mode_cb(resp):
            mode = int(resp[0].group('mode'))
            OPTION_CONN_DICT_REV = revert_dict(OPTION_CONN_DICT)
            if mode in OPTION_CONN_DICT_REV:
                return OPTION_CONN_DICT_REV[mode]

            raise KeyError("Unknown network mode %d" % mode)

        return self.send_at('AT_OPSYS?', name='get_network_mode',
                         callback=get_network_mode_cb)

    def get_roaming_ids(self):
        # Many Option devices panic if AT+CPOL is sent while in UCS2, we will
        # switch to IRA, perform the operation and switch back to UCS2
        self.set_charset("IRA")
        d = super(OptionWrapper, self).get_roaming_ids()

        def get_roaming_ids_cb(rids):
            d2 = self.set_charset("UCS2")
            d2.addCallback(lambda _: rids)
            return d2

        d.addCallback(get_roaming_ids_cb)
        return d

    def set_band(self, band):
        """Sets the band set to requested ``band``"""

        def get_band_dict_cb(current):
            at_str = 'AT_OPBM="%s",%d'

            todo = []
            if band == consts.MM_NETWORK_BAND_ANY:
                # enabling ANY should suffice
                todo.append(self.send_at(at_str % ('ANY', 1)))
            else:
                supported = self.custom.band_dict.copy()
                supported.pop(consts.MM_NETWORK_BAND_ANY)

                # turn on the bits we want first
                for key, value in supported.items():
                    if key & band and current[value] != 1:
                        # enable required band
                        todo.append(self.send_at(at_str % (value, 1)))

                # turn off the bits we don't want
                for key, value in supported.items():
                    if (not key & band) and current[value] != 0:
                        # disable unrequired band
                        todo.append(self.send_at(at_str % (value, 0)))

            if todo:
                dlist = defer.DeferredList(todo, consumeErrors=1)
                dlist.addCallback(lambda l: [x[1] for x in l])
                return dlist

            raise KeyError("OptionWrapper: Unknown band %d" % band)

        # due to Option's band API, we'll start by obtaining the current bands
        d = self._get_band_dict()
        d.addCallback(get_band_dict_cb)
        return d

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``_mode``"""
        if mode not in self.custom.allowed_dict:
            raise KeyError("Unknown mode %d for set_allowed_mode" % mode)

        def set_allowed_mode_cb(orig=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return orig

        return self.send_at("AT_OPSYS=%d,2" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``_mode``"""
        if mode not in OPTION_CONN_DICT:
            raise KeyError("Unknown mode %d for set_network_mode" % mode)

        return self.send_at("AT_OPSYS=%d,2" % OPTION_CONN_DICT[mode])


class OptionHSOWrapper(OptionWrapper):
    """Wrapper for all Option HSO cards"""

    def get_ip4_config(self):
        """
        Returns the ip4 config on a HSO device

        Wrapper around _get_ip4_config that provides some error control
        """
        ip_method = self.device.get_property(consts.MDM_INTFACE, 'IpMethod')
        if ip_method != consts.MM_IP_METHOD_STATIC:
            msg = "Cannot get IP4 config from a non static ip method"
            raise E.OperationNotSupported(msg)

        self.state_dict['num_of_retries'] = 0

        def real_get_ip4_config(deferred):

            def inform_caller():
                if self.device.status > consts.MM_MODEM_STATE_REGISTERED:
                    self.device.set_status(consts.MM_MODEM_STATE_REGISTERED)
                deferred.errback(RuntimeError('Connection attempt failed'))

            def get_ip4_eb(failure):
                failure.trap(E.General)
                if self.state_dict.get('should_stop'):
                    self.state_dict.pop('should_stop')
                    return

                self.state_dict['num_of_retries'] += 1
                if self.state_dict['num_of_retries'] > HSO_MAX_RETRIES:
                    inform_caller()
                    return failure

                reactor.callLater(HSO_RETRY_TIMEOUT,
                                  real_get_ip4_config, deferred)

            d = self._get_ip4_config()
            d.addCallback(deferred.callback)
            d.addErrback(get_ip4_eb)
            return deferred

        auxdef = defer.Deferred()
        return real_get_ip4_config(auxdef)

    def _get_ip4_config(self):
        """Returns the ip4 config on a HSO device"""
        conn_id = self.state_dict.get('conn_id')
        if not conn_id:
            raise E.CallIndexError("conn_id is None")

        cmd = ATCmd('AT_OWANDATA=%d' % conn_id, name='get_ip4_config')
        d = self.queue_at_cmd(cmd)

        def _get_ip4_config_cb(resp):
            ip, dns1 = resp[0].group('ip'), resp[0].group('dns1')
            # XXX: Fix dns3
            dns2 = dns3 = resp[0].group('dns2')
            self.device.set_status(consts.MM_MODEM_STATE_CONNECTED)
            return [ip, dns1, dns2, dns3]

        d.addCallback(_get_ip4_config_cb)
        return d

    def hso_authenticate(self, user, passwd, auth):
        """Authenticates using ``user`` and ``passwd`` on HSO devices"""
        conn_id = self.state_dict.get('conn_id')
        if not conn_id:
            raise E.CallIndexError("conn_id is None")

        # Note: auth is now a bitfield, but option can only support one mode so
        #       unless it's only NONE or CHAP, default to PAP
        if auth == consts.MM_ALLOWED_AUTH_NONE:
            _auth = 0   # No auth
        elif auth == consts.MM_ALLOWED_AUTH_CHAP:
            _auth = 2   # CHAP
        else:
            _auth = 1   # PAP

        args = (conn_id, _auth, user, passwd)
        cmd = ATCmd('AT$QCPDPP=%d,%d,"%s","%s"' % args,
                    name='hso_authenticate')
        d = self.queue_at_cmd(cmd)
        d.addCallback(lambda resp: resp[0].group('resp'))
        return d

    def hso_connect(self):
        # clean should_stop
        if 'should_stop' in self.state_dict:
            self.state_dict.pop('should_stop')

        conn_id = self.state_dict.get('conn_id')
        if not conn_id:
            raise E.CallIndexError("conn_id is None")

        if self.device.status == consts.MM_MODEM_STATE_CONNECTED:
            # this cannot happen
            raise E.Connected("we are already connected")

        if self.device.status == consts.MM_MODEM_STATE_CONNECTING:
            raise E.SimBusy("we are already connecting")

        self.device.set_status(consts.MM_MODEM_STATE_CONNECTING)

        return self.device.sconn.send_at('AT_OWANCALL=%d,1,0' % conn_id)

    def hso_disconnect(self):
        conn_id = self.state_dict.get('conn_id')
        if not conn_id:
            raise E.CallIndexError("conn_id is None")

        self.device.set_status(consts.MM_MODEM_STATE_DISCONNECTING)
        self.state_dict['should_stop'] = True

        def disconnect_cb(ignored):
            # XXX: perhaps we should check the registration status here
            if self.device.status > consts.MM_MODEM_STATE_REGISTERED:
                self.device.set_status(consts.MM_MODEM_STATE_REGISTERED)

        d = self.device.sconn.send_at('AT_OWANCALL=%d,0,0' % conn_id)
        d.addCallback(disconnect_cb)
        return d


class OptionWCDMACustomizer(WCDMACustomizer):
    """Customizer for Option's cards"""

    async_regexp = re.compile(r"""
                \r\n
                (?P<signal>_O[A-Z]{3,}):\s(?P<args>.*)
                \r\n""", re.VERBOSE)
    allowed_dict = OPTION_ALLOWED_DICT
    band_dict = OPTION_BAND_DICT
    conn_dict = OPTION_CONN_DICT
    cmd_dict = OPTION_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE,
                           S.SIG_SMS_NOTIFY_ONLINE,
                           S.SIG_RSSI]
    signal_translations = {
        '_OSSYSI': (None, option_new_mode),
        '_OSIGQ': (None, option_new_rssi),
    }

    wrapper_klass = OptionWrapper


class OptionHSOWCDMACustomizer(OptionWCDMACustomizer):
    """Customizer for HSO WCDMA devices"""

    exporter_klass = HSOExporter
    wrapper_klass = OptionHSOWrapper


class OptionWCDMADevicePlugin(DevicePlugin):
    """DevicePlugin for Option"""

    sim_klass = OptionSIMClass
    custom = OptionWCDMACustomizer()

    def __init__(self):
        super(OptionWCDMADevicePlugin, self).__init__()


class OptionHSOWCDMADevicePlugin(OptionWCDMADevicePlugin):
    """DevicePlugin for Option HSO devices"""

    custom = OptionHSOWCDMACustomizer()
    dialer = 'hso'
    ipmethod = consts.MM_IP_METHOD_STATIC

    def __init__(self):
        super(OptionHSOWCDMADevicePlugin, self).__init__()
