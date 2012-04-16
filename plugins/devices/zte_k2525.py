# -*- coding: utf-8 -*-
# Copyright (C) 2006-2012  Vodafone España, S.A.
# Copyright (C) 2008-2009  Warp Networks, S.L.
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

import re
from twisted.internet import defer, reactor
from twisted.internet.task import deferLater

from wader.common import consts
import wader.common.aterrors as E
from wader.common.encoding import (unpack_ucs2_bytes, pack_ucs2_bytes,
                                   check_if_ucs2)
from wader.common.exceptions import LimitedServiceNetworkError
from core.command import build_cmd_dict
from core.middleware import WCDMAWrapper, NetworkOperator
from core.hardware.zte import (ZTEWCDMADevicePlugin,
                                       ZTEWCDMACustomizer,
                                       ZTEWrapper,
                                       ZTE_CMD_DICT)
from core.sim import SIMBaseClass

ZTEK2525_ALLOWED_DICT = {
    consts.MM_ALLOWED_MODE_ANY: None,
    consts.MM_ALLOWED_MODE_2G_ONLY: None,
}

ZTEK2525_CONN_DICT = {
    consts.MM_NETWORK_MODE_ANY: None,
    consts.MM_NETWORK_MODE_2G_ONLY: None,
}

ZTEK2525_CMD_DICT = ZTE_CMD_DICT.copy()

ZTEK2525_CMD_DICT['get_network_info'] = build_cmd_dict(re.compile(r"""
                             \r\n
                             \+COPS:\s+
                             (
                             (?P<error>\d) |
                             \d,\d, # or followed by num,num,str (fixed bearer)
                             "(?P<netname>[\w\S ]*)"
                             )      # end of group
                             \r\n
                             """, re.VERBOSE))

ZTEK2525_CMD_DICT['get_network_mode'] = build_cmd_dict(re.compile(r"""
                             \r\n
                             \+ZSNT=
                             (?P<only>\d+),
                             (?P<netsel>\d+),
                             (?P<order>\d+)
                             \r\n
                             """, re.VERBOSE))

ZTEK2525_CMD_DICT['get_network_names'] = build_cmd_dict(re.compile(r"""
                             \(
                             (?P<id>\d+),
                             "(?P<lname>[^"]*)",
                             "(?P<sname>[^"]*)",
                             "(?P<netid>\d+)"
                             \),?
                             """, re.VERBOSE),
                             end=re.compile('\r\n\r\nOK\r\n'))

ZTEK2525_CMD_DICT['get_sms'] = build_cmd_dict(re.compile(r"""
                             \r\n
                             \+CMGR:\s
                             (?P<where>\d),
                             (?P<contact>.*),
                             \d+\r\n
                             (?P<pdu>\w+)
                             \r\n
                             """, re.VERBOSE))

ZTEK2525_CMD_DICT['list_sms'] = build_cmd_dict(re.compile(r"""
                             \r\n
                             \+CMGL:\s
                             (?P<id>\d+),
                             (?P<where>\d),
                             (?P<contact>.*),
                             \d+\r\n
                             (?P<pdu>\w+)
                             """, re.VERBOSE))


class ZTEK2525Wrapper(ZTEWrapper):

    def enable_radio(self, enable):
        # It's really difficult to bring device back from +cfun=0, so let's
        # just turn the radio off instead
        d = self.get_radio_status()

        def get_radio_status_cb(status):
            if status in [0, 4] and enable:
                d = self.send_at('AT+CFUN=1')

                def cb(arg):
                    # delay here 5 secs
                    return deferLater(reactor, 5, lambda: arg)

                d.addCallback(cb)
                return d

            elif status == 1 and not enable:
                return self.send_at('AT+CFUN=4')

        d.addCallback(get_radio_status_cb)
        return d

    def get_network_info(self, _type=None):
        """
        Returns the network info  (a.k.a AT+COPS?)

        The response will be a tuple as (OperatorName, ConnectionType) if
        it returns a (None, None) that means that some error occurred while
        obtaining the info. The class that requested the info should take
        care of insisting before this problem. This method will convert
        numeric network IDs to alphanumeric.
        """
        d = super(WCDMAWrapper, self).get_network_info(_type)

        def get_net_info_cb(netinfo):
            """
            Returns a (Networkname, ConnType) tuple

            It returns None if there's no info
            """
            if not netinfo:
                return None

            netinfo = netinfo[0]

            if netinfo.group('error'):
                # this means that we've received a response like
                # +COPS: 0 which means that we don't have network temporaly
                # we should raise an exception here
                raise E.NoNetwork()

            conn_type = consts.MM_GSM_ACCESS_TECH_GPRS
            netname = netinfo.group('netname')

            if netname in ['Limited Service',
                           pack_ucs2_bytes('Limited Service')]:
                raise LimitedServiceNetworkError()

            # netname can be in UCS2, as a string, or as a network id (int)
            if check_if_ucs2(netname):
                return unpack_ucs2_bytes(netname), conn_type
            else:
                # now can be either a string or a network id (int)
                try:
                    netname = int(netname)
                except ValueError:
                    # we got a string ID
                    return netname, conn_type

                # if we have arrived here, that means that the network id
                # is a five digit integer
                return str(netname), conn_type

        d.addCallback(get_net_info_cb)
        return d

    def get_network_names(self):
        """
        Performs a network search

        :rtype: list of :class:`NetworkOperator`
        """
        d = super(WCDMAWrapper, self).get_network_names()

        def get_network_names_cb(resp):
            # K2525 is GPRS/EDGE only, so won't provide bearer type in results
            return [NetworkOperator(*match.groups() + (0,)) for match in resp]

        d.addCallback(get_network_names_cb)
        return d

    def get_network_mode(self):
        """Returns the current network mode preference"""
        return defer.succeed(consts.MM_NETWORK_MODE_2G_ONLY)

    def set_allowed_mode(self, mode):
        """Sets the allowed mode to ``mode``"""
        if mode in self.custom.allowed_dict:
            self.device.set_property(consts.NET_INTFACE, "AllowedMode", mode)
            return defer.succeed("OK")
        else:
            raise KeyError("Mode %s not found" % mode)

    def set_network_mode(self, mode):
        """Sets the network mode to ``mode``"""
        if mode in self.custom.conn_dict:
            return defer.succeed("OK")
        else:
            raise KeyError("Unsupported mode %d" % mode)

    def set_smsc(self, smsc):
        """Sets the SIM's SMSC number to ``smsc``"""
        # K2525 never requires UCS2
        d = super(WCDMAWrapper, self).set_smsc(smsc)
        d.addCallback(lambda response: response[0].group('resp'))
        return d


class ZTEK2525SIMClass(SIMBaseClass):
    """SIM class for ZTE K2525 devices"""

    def __init__(self, sconn):
        super(ZTEK2525SIMClass, self).__init__(sconn)

    def setup_sms(self):
        # Select SIM storage
        self.sconn.send_at('AT+CPMS="SM","SM","SM"')

        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(1, 1, 0, 1, 0)

        # set PDU mode
        self.sconn.set_sms_format(0)


class ZTEK2525Customizer(ZTEWCDMACustomizer):
    allowed_dict = ZTEK2525_ALLOWED_DICT
    band_dict = {}
    conn_dict = ZTEK2525_CONN_DICT
    cmd_dict = ZTEK2525_CMD_DICT
    wrapper_klass = ZTEK2525Wrapper


class ZTEK2525(ZTEWCDMADevicePlugin):
    """:class:`~core.plugin.DevicePlugin` for ZTE's K2525"""
    name = "Vodafone K2525"
    version = "0.1"
    author = "Andrew Bird"
    sim_klass = ZTEK2525SIMClass
    custom = ZTEK2525Customizer()

    __remote_name__ = "K2525"

    __properties__ = {
        'ID_VENDOR_ID': [0x19d2],
        'ID_MODEL_ID': [0x0022],
    }

    conntype = consts.WADER_CONNTYPE_USB

zte_k2525 = ZTEK2525()
