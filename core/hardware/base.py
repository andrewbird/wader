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
"""Base classes for the hardware module"""

from __future__ import with_statement
from contextlib import closing

import re
import serial
from time import sleep
from twisted.internet.threads import deferToThread
from twisted.python import log

from core.command import get_cmd_dict_copy
from wader.common.consts import MDM_INTFACE
from core.middleware import WCDMAWrapper
from core.plugin import PluginManager
from core.statem.auth import AuthStateMachine
from core.statem.simple import SimpleStateMachine
from core.statem.networkreg import NetworkRegistrationStateMachine
import wader.common.exceptions as ex


class WCDMACustomizer(object):
    """
    I contain all the custom classes and metadata that a WCDMA device needs

    :cvar wrapper_klass: Wrapper for the device
    :cvar exporter_klass: DBus Exporter for the device
    :cvar async_regexp: regexp to parse asynchronous notifications emited
          by the device.
    :cvar allowed_dict: Dictionary with the allowed modes
    :cvar band_dict: Dictionary with the supported bands
    :cvar conn_dict: Dictionary with the supported network modes
    :cvar cmd_dict: Dictionary with commands info
    :cvar device_capabilities: List with the unsolicited notifications that
          this device supports
    :cvar auth_klass: Class that will handle the authentication for this device
    :cvar netr_klass: Class that will handle the network registration for this
          device
    """

    from core.exported import WCDMAExporter
    wrapper_klass = WCDMAWrapper
    exporter_klass = WCDMAExporter
    async_regexp = None
    allowed_dict = {}
    band_dict = {}
    conn_dict = {}
    cmd_dict = get_cmd_dict_copy()
    device_capabilities = []
    signal_translations = {}
    auth_klass = AuthStateMachine
    simp_klass = SimpleStateMachine
    netr_klass = NetworkRegistrationStateMachine


def build_band_dict(family_dict, supported_list):
    """Returns a new dict with just the supported bands of the family"""
    band_dict = {}
    for band in supported_list:
        band_dict[band] = family_dict[band]

    return band_dict


def check_auth_state(plugin):
    codes = {
        'READY': '',
        'SIM PIN': 'sim-pin',
        'SIM PIN2': 'sim-pin2',
        'SIM PUK': 'sim-puk',
        'SIM PUK2': 'sim-puk2',
        'PH-NETSUB PIN': 'ph-netsub-pin',
        'PH-NETSUB PUK': 'ph-netsub-puk',
        'PH-SIM PIN': 'ph-sim-pin',
        'PH-NET PUK': 'ph-net-puk',
        'PH-NET PIN': 'ph-net-pin',
        'PH-SP PIN': 'ph-sp-pin',
        'PH-SP PUK': 'ph-sp-puk',
        'PH-CORP PIN': 'ph-corp-pin',
        'PH-CORP PUK': 'ph-corp-puk',
        'PH-FSIM PIN': 'ph-fsim-pin',
        'PH-FSIM PUK': 'ph-fsim-puk',
    }

    def do_check(port):
        with closing(serial.Serial(port.path, timeout=.5)) as ser:

            # some devices need to be enabled before pin can be checked
            if plugin.quirks.get('needs_enable_before_pin_check', False):
                ser.write('AT+CFUN=1\r\n')
                lines = ser.readlines()

            for i in range(15):  # some devices/SIMs are slow to be available
                ser.flushOutput()
                ser.flushInput()

                ser.write('AT+CPIN?\r\n')
                lines = ser.readlines()

                for line in lines:
                    line = line.replace('\r', '').replace('\n', '')

                    m = re.search('\+CPIN:\s*(?P<code>\w+[\w -]*\w+)', line)
                    if m is not None:
                        code = m.group('code')
                        if code in codes:
                            plugin.set_property(MDM_INTFACE, 'UnlockRequired',
                                            codes[code])
                            plugin.set_authtime(0)
                            return plugin

                log.msg("check_auth_state: +CPIN? returned '%s'" % lines)
                sleep(1)  # can do this as we are in a separate thread

        log.msg("check_auth_state: +CPIN? no match lines = %s" % str(lines))

        return plugin

    port = plugin.ports.get_application_port()
    return deferToThread(do_check, port)


def raw_identify_device(port):
    """Returns the model of the device present at `port`"""
    BAD_REPLIES = ['AT+CGMM', 'OK', '']
    # as the readlines method blocks, this is executed in a parallel thread
    # with deferToThread
    with closing(serial.Serial(port, timeout=.5)) as ser:
        ser.write('ATZ E0 V1 X4 &C1\r\n')
        ser.readlines()

        ser.flushOutput()
        ser.flushInput()

        ser.write('AT+CGMM\r\n')
        lines = ser.readlines()
        # clean up \r\n as pairs or singles and avoid unsolicited notifications
        resp = [r for r in [l.strip('\r\n') for l in lines
                    if not l.startswith(('^', '_'))] if r not in BAD_REPLIES]
        if resp:
            log.msg("AT+CGMM response: %s" % resp)
            return resp[0]

        raise ValueError("Reply from modem %s was meaningless: %s"
                            % (port, lines))


def identify_device(plugin):
    """Returns a :class:`~core.plugin.DevicePlugin` out of `plugin`"""
    if not plugin.mapping:
        # only identify devices that require it
        return check_auth_state(plugin)

    def identify_device_cb(model):
        # plugin to return
        ret = None

        if model in plugin.mapping:
            ret = plugin.mapping[model]()
        elif plugin.__remote_name__ != model:
            # so we basically have a device identified by vendor & product id
            # but we know nothing of this model
            try:
                ret = PluginManager.get_plugin_by_remote_name(model)
            except ex.UnknownPluginNameError:
                plugin.name = model

        if ret is not None:
            # we found another plugin during the process
            ret.patch(plugin)
            return check_auth_state(ret)

        # return the original plugin, most of the time this should work
        return check_auth_state(plugin)

    port = plugin.ports.get_application_port()
    d = deferToThread(raw_identify_device, port.path)
    d.addCallback(identify_device_cb)
    return d


def probe_port(port):
    """
    Check whether ``port`` exists and works

    :rtype: bool
    """
    with closing(serial.Serial(port, timeout=.01)) as ser:
        try:
            ser.write('AT+CGMR\r\n')
            # Huawei E620 with driver option registers three serial
            # ports and the middle one wont raise any exception while
            # opening it even thou its a dummy port.
            return ser.readlines() != []
        except (serial.SerialException, OSError), e:
            log.err(e, "Error identifying device in port %s" % port)
            return False


def probe_ports(ports):
    """
    Obtains the data and control ports out of ``ports``

    :rtype: tuple
    """
    dport = cport = None
    for port in ports:
        if probe_port(port):
            if dport is None:
                # data port tends to the be the first one
                dport = port
            elif cport is None:
                # control port the next working one
                cport = port

        if dport and cport:
            break

    return dport, cport
