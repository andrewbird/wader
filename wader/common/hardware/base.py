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

import serial
from twisted.internet.threads import deferToThread
from twisted.python import log

from wader.common.command import get_cmd_dict_copy
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import PluginManager
from wader.common.statem.auth import AuthStateMachine
from wader.common.statem.simple import SimpleStateMachine
from wader.common.statem.networkreg import NetworkRegistrationStateMachine
import wader.common.exceptions as ex

class WCDMACustomizer(object):
    """
    I contain all the custom classes and metadata that a WCDMA device needs

    :cvar wrapper_klass: Wrapper for the device
    :cvar exporter_klass: DBus Exporter for the device
    :cvar async_regexp: regexp to parse asynchronous notifications emited
          by the device.
    :cvar band_dict: Dictionary with the supported bands
    :cvar conn_dict: Dictionary with the supported network modes
    :cvar cmd_dict: Dictionary with commands info
    :cvar device_capabilities: List with the unsolicited notifications that
          this device supports
    :cvar auth_klass: Class that will handle the authentication for this device
    :cvar netr_klass: Class that will handle the network registration for this
          device
    """
    from wader.common.exported import WCDMAExporter
    wrapper_klass = WCDMAWrapper
    exporter_klass = WCDMAExporter
    async_regexp = None
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

def _identify_device(port):
    """Returns the model of the device present at `port`"""
    # as the readlines method blocks, this is executed in a parallel thread
    # with deferToThread
    ser = serial.Serial(port, timeout=1)
    ser.write('ATZ E0 V1 X4 &C1\r\n')
    ser.readlines()

    ser.flushOutput()
    ser.flushInput()

    ser.write('AT+CGMM\r\n')
    # clean up unsolicited notifications and \r\n's
    response = [r.replace('\r\n', '') for r in ser.readlines()
                    if not r.startswith(('^', '_')) and r.replace('\r\n','')]
    if response and response[0].startswith('AT+CGMM'):
        response.pop(0)

    assert len(response), "Modem didn't reply anything meaningless"
    log.msg("at+cgmm response: %s" % response[0])
    ser.close()

    return response[0]

def identify_device(plugin):
    """Returns a :class:`~wader.common.plugin.DevicePlugin` out of `plugin`"""
    def identify_device_cb(model):
        # plugin to return
        _plugin = None

        if plugin.mapping:
            if model in plugin.mapping:
                _plugin = plugin.mapping[model]()

        # the plugin has no mapping, chances are that we already identified
        # it by its vendor & product id
        elif plugin.__remote_name__ != model:
            # so we basically have a device identified by vendor & product id
            # but we know nuthin of this model
            try:
                _plugin = PluginManager.get_plugin_by_remote_name(model)
            except ex.UnknownPluginNameError:
                plugin.name = model

        if _plugin is not None:
            # we found another plugin during the process
            _plugin.patch(plugin)
            return _plugin
        else:
            return plugin

    ports = plugin.ports
    port = ports.has_two() and ports.cport or ports.dport
    d = deferToThread(_identify_device, port.path)
    d.addCallback(identify_device_cb)
    return d

