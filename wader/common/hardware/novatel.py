# -*- coding: utf-8 -*-
# Copyright (C) 2006-2009  Vodafone España, S.A.
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
"""Common stuff for all Novatel's cards"""

import re
from twisted.internet import defer, reactor

from wader.common import consts
from wader.common.command import get_cmd_dict_copy, build_cmd_dict
from wader.common.hardware.base import WCDMACustomizer
from wader.common.middleware import WCDMAWrapper
from wader.common.plugin import DevicePlugin
from wader.common.utils import revert_dict
from wader.common.sim import SIMBaseClass


NOVATEL_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: '0,2',
    consts.MM_ALLOWED_MODE_2G_ONLY: '1,2',
    consts.MM_ALLOWED_MODE_3G_ONLY: '2,2',
    consts.MM_ALLOWED_MODE_3G_PREFERRED: '0,2',
}

NOVATEL_MODE_DICT = {
    consts.MM_NETWORK_MODE_ANY: '0,2',
    consts.MM_NETWORK_MODE_2G_ONLY: '1,2',
    consts.MM_NETWORK_MODE_3G_ONLY: '2,2',

    consts.MM_NETWORK_MODE_3G_PREFERRED: '0,2', # just a dup of automatic
}

NOVATEL_BAND_DICT = {
    consts.MM_NETWORK_BAND_ANY: 0x3FFFFFFF,

    consts.MM_NETWORK_BAND_EGSM: 0x00000100,  #  900 MHz
    consts.MM_NETWORK_BAND_DCS: 0x00000080,   # 1800 MHz
    consts.MM_NETWORK_BAND_PCS: 0x00200000,   # 1900 MHz
    consts.MM_NETWORK_BAND_G850: 0x00080000,  #  850 MHz
    consts.MM_NETWORK_BAND_U2100: 0x00400000, # WCDMA 2100 MHz
    consts.MM_NETWORK_BAND_U1700: 0x01000000, # WCDMA 3GPP UMTS1800 MHz
    consts.MM_NETWORK_BAND_17IV: 0x02000000,  # WCDMA 3GPP AWS 1700/2100 MHz
    consts.MM_NETWORK_BAND_U800: 0x08000000,  # WCDMA 3GPP UMTS800 MHz
    consts.MM_NETWORK_BAND_U850: 0x04000000,  # WCDMA 3GPP UMTS850 MHz
    consts.MM_NETWORK_BAND_U1900: 0x00800000, # WCDMA 3GPP UMTS MHz
}

# Following band definitions found from X950D
# AT$nwband=?
# $NWBAND: <band> bit definitions
# $NWBAND: 00 CDMA2000 Band Class 0, A-System
# $NWBAND: 01 CDMA2000 Band Class 0, B-System
# $NWBAND: 02 CDMA2000 Band Class 1, all blocks
# $NWBAND: 03 CDMA2000 Band Class 2 place holder
# $NWBAND: 04 CDMA2000 Band Class 3, A-System
# $NWBAND: 05 CDMA2000 Band Class 4, all blocks
# $NWBAND: 06 CDMA2000 Band Class 5, all blocks
# $NWBAND: 07 GSM DCS band
# $NWBAND: 08 GSM Extended GSM (E-GSM) band
# $NWBAND: 09 GSM Primary GSM (P-GSM) band
# $NWBAND: 10 CDMA2000 Band Class 6
# $NWBAND: 11 CDMA2000 Band Class 7
# $NWBAND: 12 CDMA2000 Band Class 8
# $NWBAND: 13 CDMA2000 Band Class 9
# $NWBAND: 14 CDMA2000 Band Class 10
# $NWBAND: 15 CDMA2000 Band Class 11
# $NWBAND: 16 GSM 450 band
# $NWBAND: 17 GSM 480 band
# $NWBAND: 18 GSM 750 band
# $NWBAND: 19 GSM 850 band
# $NWBAND: 20 GSM Band
# $NWBAND: 21 GSM PCS band
# $NWBAND: 22 WCDMA I IMT 2000 band
# $NWBAND: 23 WCDMA II PCS band
# $NWBAND: 24 WCDMA III 1700 band
# $NWBAND: 25 WCDMA IV 1700 band
# $NWBAND: 26 WCDMA V US850 band
# $NWBAND: 27 WCDMA VI JAPAN 800 band
# $NWBAND: 28 Reserved for BC12/BC14
# $NWBAND: 29 Reserved for BC12/BC14
# $NWBAND: 30 Reserved
# $NWBAND: 31 Reserved

# Following additional band definitions from MiFi 2352
# at$NWBAND2=?
# $NWBAND2: <band> bit definitions
# $NWBAND2: 00 WLAN US 2400 band
# $NWBAND2: 01 WLAN ETSI 2400 band
# $NWBAND2: 02 WLAN FRANCE 2400 band
# $NWBAND2: 03 WLAN SPAIN 2400 band
# $NWBAND2: 04 WLAN JAPAN 2400 band
# $NWBAND2: 05 WLAN US 2400 band
# $NWBAND2: 06 WLAN EUROPE 5000 band
# $NWBAND2: 07 WLAN FRANCE 5000 band
# $NWBAND2: 08 WLAN SPAIN 5000 band
# $NWBAND2: 09 WLAN JAPAN 5000 band
# $NWBAND2: 10 Reserved
# $NWBAND2: 11 Reserved
# $NWBAND2: 12 Reserved
# $NWBAND2: 13 Reserved
# $NWBAND2: 14 Reserved
# $NWBAND2: 15 Reserved
# $NWBAND2: 16 WCDMA EUROPE 2600 band
# $NWBAND2: 17 WCDMA EUROPE & JAPAN 900 band
# $NWBAND2: 18 WCDMA JAPAN 1700 band
# $NWBAND2: 19 Reserved for WLAN
# $NWBAND2: 20 Reserved for WLAN
# $NWBAND2: 21 Reserved for WLAN
# $NWBAND2: 22 Reserved for WLAN
# $NWBAND2: 23 Reserved for WLAN
# $NWBAND2: 24 Band Class 16
# $NWBAND2: 25 Reserved
# $NWBAND2: 26 Reserved
# $NWBAND2: 27 Reserved
# $NWBAND2: 28 Reserved
# $NWBAND2: 29 Reserved
# $NWBAND2: 30 Persistent value from NV
# $NWBAND2: 31 Reserved

NOVATEL_CMD_DICT = get_cmd_dict_copy()

NOVATEL_CMD_DICT['get_network_mode'] = build_cmd_dict(
                          re.compile("\r\n\$NWRAT:\s?(?P<mode>\d,\d),\d\r\n"))

NOVATEL_CMD_DICT['get_band'] = build_cmd_dict(
                          re.compile("\r\n\$NWBAND:\s?(?P<band>[0-9A-Fa-f]+)"))


class NovatelSIMClass(SIMBaseClass):
    """Novatel SIM Class"""

    def __init__(self, sconn):
        super(NovatelSIMClass, self).__init__(sconn)

    def initialize(self, set_encoding=True):

        def init_callback(size):
            # make sure we are in most promiscuous mode before registration
            self.sconn.set_network_mode(consts.MM_NETWORK_MODE_ANY)
            # set SMS storage default
            self.sconn.send_at('AT+CPMS="SM","SM","SM"')
            return(size)

        d = super(NovatelSIMClass, self).initialize(set_encoding)
        d.addCallback(init_callback)
        return d


class NovatelWrapper(WCDMAWrapper):
    """Wrapper for all Novatel cards"""

    # XXX: Needs updating for use of bands in second chunk
    #      of bit settings (U900 etc)
    def get_band(self):
        """Returns the current used band"""
        if not len(self.custom.band_dict):
            return defer.succeed(consts.MM_NETWORK_BAND_ANY)

        def get_band_cb(resp):
            band = int(resp[0].group('band'), 16)
            if band == 0x3FFFFFFF:
                return consts.MM_NETWORK_BAND_ANY

            ret = 0
            for key, value in NOVATEL_BAND_DICT.items():
                if value & band:
                    ret |= key
            return ret

        return self.send_at("AT$NWBAND?", name='get_band',
                            callback=get_band_cb)

    def get_network_mode(self):
        """Returns the current network mode"""

        def get_network_mode_cb(resp):
            mode = resp[0].group('mode')
            return revert_dict(self.custom.conn_dict)[mode]

        return self.send_at("AT$NWRAT?", name='get_network_mode',
                            callback=get_network_mode_cb)

    # XXX: Needs updating for use of bands in second chunk
    #      of bit settings (U900 etc)
    def set_band(self, band):
        """Sets the band to ``band``"""
        if not len(self.custom.band_dict):
            if band == consts.MM_NETWORK_BAND_ANY:
                return defer.succeed('')
            else:
                raise KeyError("Unsupported band %d" % band)

        if band == consts.MM_NETWORK_BAND_ANY:
            _band = 0x3FFFFFFF
        else:
            _band = 0
            for key, value in self.custom.band_dict.items():
                if key == consts.MM_NETWORK_BAND_ANY:
                    continue

                if key & band:
                    _band |= value

            if _band == 0:
                # if we could not satisfy the request, tell someone
                raise KeyError("Unsupported band %d" % band)

        deferred = defer.Deferred()
        d = self.send_at("AT$NWBAND=%08x" % _band)

        def delay_result(result):
            reactor.callLater(1, deferred.callback, True)

        d.addCallback(delay_result)
        return deferred

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode not in self.custom.allowed_dict:
            raise KeyError("Unknown network mode %d" % mode)

        def set_allowed_mode_cb(ign=None):
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return ign

        return self.send_at("AT$NWRAT=%s" % self.custom.allowed_dict[mode],
                            callback=set_allowed_mode_cb)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode not in self.custom.conn_dict:
            raise KeyError("Unknown network mode %d" % mode)

        return self.send_at("AT$NWRAT=%s" % self.custom.conn_dict[mode])


class NovatelWCDMACustomizer(WCDMACustomizer):
    """WCDMA customizer for Novatel cards"""
    async_regexp = None
    allowed_dict = NOVATEL_ALLOWED_DICT
    band_dict = {}  # let the cards that support band switching define
                    # the bands they support
    cmd_dict = NOVATEL_CMD_DICT
    conn_dict = NOVATEL_MODE_DICT
    wrapper_klass = NovatelWrapper


class NovatelWCDMADevicePlugin(DevicePlugin):
    """WCDMA device plugin for Novatel cards"""
    sim_klass = NovatelSIMClass
    custom = NovatelWCDMACustomizer()
