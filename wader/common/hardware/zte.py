# -*- coding: utf-8 -*-
# Copyright (C) 2006-2007  Vodafone España, S.A.
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
"""Common stuff for all zte's cards"""

import re

from wader.common import consts
from wader.common.command import get_cmd_dict_copy, build_cmd_dict
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict
import wader.common.signals as S

ZTE_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY          : (0, 0, 0),
    consts.MM_NETWORK_MODE_2G_ONLY      : (1, 0, 0),
    consts.MM_NETWORK_MODE_3G_ONLY      : (2, 0, 0),
    consts.MM_NETWORK_MODE_2G_PREFERRED : (0, 0, 1),
    consts.MM_NETWORK_MODE_3G_PREFERRED : (1, 0, 2),
}

ZTE_BAND_DICT = {
    consts.MM_NETWORK_BAND_PCS   : 4, # PCS (1900MHz)
    consts.MM_NETWORK_BAND_G850  : 3, # GSM (850 MHz)
    consts.MM_NETWORK_BAND_U2100 : 2, # WCDMA 2100Mhz            (Class I)
    consts.MM_NETWORK_BAND_U850  : 1, # WCDMA 3GPP UMTS850       (Class V)
    consts.MM_NETWORK_BAND_ANY   : 0, # any band
}

ZTE_CMD_DICT = get_cmd_dict_copy()

ZTE_CMD_DICT['get_band'] = build_cmd_dict(re.compile(r"""
                                            \r\n
                                            \+ZBANDI:\s?
                                            (?P<band>\d)
                                            \r\n
                                            """, re.VERBOSE))

ZTE_CMD_DICT['get_netreg_status'] = build_cmd_dict(re.compile(r"""
                                \r\n
                                \+CREG:\s
                                (?P<mode>\d),
                                (?P<status>\d+)(,[0-9a-fA-F]*,[0-9a-fA-F]*)?
                                \r\n""", re.VERBOSE))

ZTE_CMD_DICT['get_network_mode'] = build_cmd_dict(re.compile(r"""
                                \r\n
                                \+ZPAS:\s
                                "(?P<mode>.*)",
                                "(?P<srv>.*)",
                                \r\n""", re.VERBOSE))

def zte_new_conn_mode(args):
    what = args.replace('"', '')
    if what in "UMTS":
        return S.UMTS_SIGNAL
    elif what in ["GPRS", "GSM"]:
        return S.GPRS_SIGNAL
    elif what in "HSDPA":
        return S.HSDPA_SIGNAL
    elif what in "HSUPA":
        return S.HSDPA_SIGNAL
    elif what in "EDGE":
        return S.EDGE_SIGNAL
    elif what in ["No service", "Limited Service"]:
        return S.NO_SIGNAL


class ZTEWrapper(WCDMAWrapper):
    """Wrapper for all ZTE cards"""

    def get_band(self):
        """Returns the current used band"""
        def get_band_cb(resp):
            band = int(resp[0].group('band'))
            return revert_dict(ZTE_BAND_DICT)[band]

        return self.send_at("at+zbandi?", name='get_band',
                            callback=get_band_cb)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if band not in ZTE_BAND_DICT:
            raise KeyError("Band %d not found" % band)

        return self.send_at("at+zbandi=%d" % ZTE_BAND_DICT[band])

    def get_network_mode(self):
        """Returns the current used network mode"""
        def get_network_mode_cb(resp):
            mode = resp[0].group('mode')

            if mode in "UMTS":
                return consts.MM_NETWORK_MODE_UMTS
            elif mode in ["GPRS", "GSM"]:
                return consts.MM_NETWORK_MODE_GPRS
            elif mode in ["EDGE"]:
                return consts.MM_NETWORK_MODE_EDGE
            elif mode in ["HSDPA"]:
                return consts.MM_NETWORK_MODE_HSDPA
            elif mode in ["HSUPA"]:
                return consts.MM_NETWORK_MODE_HSUPA
            elif mode in ["HSPA"]:
                return consts.MM_NETWORK_MODE_HSPA

            raise ValueError("Can not translate mode %s" % mode)

        return self.send_at("AT+ZPAS?", name='get_network_mode',
                            callback=get_network_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in ZTE_MODE_DICT:
            raise KeyError("Mode %s not found" % mode)

        return self.send_at("AT^ZSNT=%d,%d,%d" % ZTE_MODE_DICT[mode])


class ZTEWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for ZTE devices"""
    async_regexp = re.compile("""
                    \r\n
                    (?P<signal>\+Z[A-Z]{3,}):\s*(?P<args>.*)
                    \r\n""", re.VERBOSE)
    band_dict = ZTE_BAND_DICT
    conn_dict = ZTE_MODE_DICT
    cmd_dict = ZTE_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE]
    signal_translations = {
        '+ZDONR' : (None, None),
        '+ZPASR' : (S.SIG_NETWORK_MODE, zte_new_conn_mode),
        '+ZUSIMR' : (None, None),
    }
    wrapper_klass = ZTEWrapper


class ZTEWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for ZTE devices"""
    custom = ZTEWCDMACustomizer()

