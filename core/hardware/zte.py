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

from twisted.internet import defer

from wader.common import consts
from core.command import get_cmd_dict_copy, build_cmd_dict
from core.hardware.base import WCDMACustomizer
from core.middleware import WCDMAWrapper
from core.plugin import DevicePlugin
from core.sim import SIMBaseClass
from wader.common.utils import revert_dict
import wader.common.signals as S


ZTE_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: (0, 0),
    consts.MM_ALLOWED_MODE_2G_ONLY: (1, 0),
    consts.MM_ALLOWED_MODE_3G_ONLY: (2, 0),
    consts.MM_ALLOWED_MODE_2G_PREFERRED: (0, 1),
    consts.MM_ALLOWED_MODE_3G_PREFERRED: (0, 2),
}

ZTE_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY: (0, 0),
    consts.MM_NETWORK_MODE_2G_ONLY: (1, 0),
    consts.MM_NETWORK_MODE_3G_ONLY: (2, 0),
    consts.MM_NETWORK_MODE_2G_PREFERRED: (0, 1),
    consts.MM_NETWORK_MODE_3G_PREFERRED: (0, 2),
}

ZTE_BAND_DICT = {
    consts.MM_NETWORK_BAND_ANY: 0,   # any band

    (consts.MM_NETWORK_BAND_U850 |
     consts.MM_NETWORK_BAND_EGSM |
     consts.MM_NETWORK_BAND_DCS): 1,

    (consts.MM_NETWORK_BAND_U2100 |
     consts.MM_NETWORK_BAND_EGSM |
     consts.MM_NETWORK_BAND_DCS): 2,  # Europe

    (consts.MM_NETWORK_BAND_U850 |
     consts.MM_NETWORK_BAND_U2100 |
     consts.MM_NETWORK_BAND_EGSM |
     consts.MM_NETWORK_BAND_DCS): 3,

    (consts.MM_NETWORK_BAND_U850 |
     consts.MM_NETWORK_BAND_U1900 |
     consts.MM_NETWORK_BAND_G850 |
     consts.MM_NETWORK_BAND_PCS): 4,
}
# AT+ZBANDI=0 : Automatic (Auto) - Default
# AT+ZBANDI=1 : UMTS 850 + GSM 900/1800
# AT+ZBANDI=2 : UMTS 2100 + GSM 900/1800 (Europe)
# AT+ZBANDI=3 : UMTS 850/2100 + GSM 900/1800
# AT+ZBANDI=4 : UMTS 850/1900 + GSM 850/1900

ZTE_CMD_DICT = get_cmd_dict_copy()

ZTE_CMD_DICT['get_band'] = build_cmd_dict(re.compile(r"""
                                            \r\n
                                            \+ZBANDI:\s?
                                            (?P<band>\d)
                                            \r\n
                                            """, re.VERBOSE))

ZTE_CMD_DICT['get_network_mode'] = build_cmd_dict(re.compile(r"""
                                            \r\n
                                            \+ZSNT:\s
                                            (?P<only>\d+),
                                            (?P<netsel>\d+),
                                            (?P<order>\d+)
                                            \r\n
                                            """, re.VERBOSE))


def zte_new_conn_mode(what, device):
    zpasr = re.search(r'"(?P<mode>.*?)"(?:,"(?P<domain>.*?)")?', what)
    mode = zpasr.group('mode')

    modes = {
        "GSM": consts.MM_NETWORK_MODE_GPRS,
        "GPRS": consts.MM_NETWORK_MODE_GPRS,
        "EDGE": consts.MM_NETWORK_MODE_EDGE,
        "UMTS": consts.MM_NETWORK_MODE_UMTS,
        "HSDPA": consts.MM_NETWORK_MODE_HSDPA,
        "HSUPA": consts.MM_NETWORK_MODE_HSUPA,
    }

    # "No Service", "Limited Service", non-match
    return modes.get(mode, consts.MM_NETWORK_MODE_UNKNOWN)


class ZTEWrapper(WCDMAWrapper):
    """Wrapper for all ZTE cards"""

    def get_band(self):
        """Returns the current used band"""
        if not len(self.custom.band_dict):
            return defer.succeed(consts.MM_NETWORK_BAND_ANY)

        def get_band_cb(resp):
            band = int(resp[0].group('band'))
            return revert_dict(self.custom.band_dict)[band]

        return self.send_at("AT+ZBANDI?", name='get_band',
                            callback=get_band_cb)

    def get_network_mode(self):
        """Returns the current network mode preference"""

        def get_network_mode_cb(resp):
            only = int(resp[0].group('only'))
            order = int(resp[0].group('order'))
            return revert_dict(self.custom.conn_dict)[(only, order)]

        return self.send_at("AT+ZSNT?", name='get_network_mode',
                            callback=get_network_mode_cb)

    def set_band(self, band):
        """Sets the band to ``band``"""
        if not len(self.custom.band_dict):
            if band == consts.MM_NETWORK_BAND_ANY:
                return defer.succeed('')
            else:
                raise KeyError("Unsupported band %d" % band)

        for key, value in self.custom.band_dict.items():
            if band & key:
                return self.send_at("AT+ZBANDI=%d" % value)

        raise KeyError("Unsupported band %d" % band)

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode not in self.custom.allowed_dict:
            raise KeyError("Mode %s not found" % mode)

        if self.device.get_property(consts.NET_INTFACE, "AllowedMode") == mode:
            # NOOP
            return defer.succeed("OK")

        def set_allowed_mode_cb(ign=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return ign

        return self.send_at("AT+ZSNT=%d,0,%d" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in self.custom.conn_dict:
            raise KeyError("Mode %s not found" % mode)

        return self.send_at("AT+ZSNT=%d,0,%d" % self.custom.conn_dict[mode])


class ZTEWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for ZTE devices"""
    async_regexp = re.compile("""
                    \r\n
                    (?P<signal>\+Z[A-Z]{3,}):\s*(?P<args>.*)
                    \r\n""", re.VERBOSE)
    allowed_dict = ZTE_ALLOWED_DICT
    band_dict = {}
    conn_dict = ZTE_MODE_DICT
    cmd_dict = ZTE_CMD_DICT
    device_capabilities = [S.SIG_NETWORK_MODE,
                           S.SIG_SMS_NOTIFY_ONLINE]
    signal_translations = {
        '+ZDONR': (None, None),
        '+ZPASR': (S.SIG_NETWORK_MODE, zte_new_conn_mode),
        '+ZUSIMR': (None, None),
        '+ZPSTM': (None, None),
        '+ZEND': (None, None),
    }
    wrapper_klass = ZTEWrapper


class ZTEWCDMASIMClass(SIMBaseClass):
    """WCDMA SIM class for ZTE devices"""

    def __init__(self, sconn):
        super(ZTEWCDMASIMClass, self).__init__(sconn)

    def setup_sms(self):
        # Select SIM storage
        self.sconn.send_at('AT+CPMS="SM","SM","SM"')

        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(2, 1, 0, 2, 0)
        # XXX: We have to set +CDSI indication as original ZTE devices don't
        #      support +CDS mode. At some point we will have to implement
        #      processing of +CDSI notifications in core
        # Sample notification
        # '+CDSI: "SR",50'
        #
        # Sample retrieval
        # AT+CPMS="SR";+CMGR=50;+CMGD=50;+CPMS="SM"
        # +CPMS: 1,100,1,15,1,15
        #
        # +CMGR: ,,25
        # 079144775810065006FD0C91449771624701117013908522401170139085624000
        #
        # +CPMS: 0,100,1,15,1,15
        #
        # OK

        # set PDU mode
        self.sconn.set_sms_format(0)


class ZTEWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for ZTE devices"""
    sim_klass = ZTEWCDMASIMClass
    custom = ZTEWCDMACustomizer()
