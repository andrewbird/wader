# -*- coding: utf-8 -*-
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
"""HSOLink Dialer"""

from wader.common.dialer import Dialer
from wader.common.consts import (HSO_NO_AUTH, HSO_PAP_AUTH, HSO_CHAP_AUTH,
                                 HSO_INTFACE)
from wader.common.oal import osobj


class HSODialer(Dialer):
    """Dialer for HSO type devices"""

    # Note: The interface is called HSO for historical reasons but actually
    #       it can be used by devices other than Option's e.g. ZTE's Icera

    def __init__(self, device, opath, **kwds):
        super(HSODialer, self).__init__(device, opath, **kwds)
        # After 2.6.33 can be wwan%d or usb%d or hso%d
        self.iface = self.device.props[HSO_INTFACE]['NetworkDevice']

    def configure(self, config):
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
        d = osobj.configure_iface(self.iface, ip, 'up')
        d.addCallback(lambda _: osobj.add_default_route(self.iface))
        d.addCallback(lambda _: osobj.add_dns_info([dns1, dns2], self.iface))
        return d

    def disconnect(self):
        d = self.device.sconn.disconnect_from_internet()
        osobj.delete_default_route(self.iface)
        osobj.delete_dns_info(None, self.iface)
        osobj.configure_iface(self.iface, '', 'down')
        d.addCallback(lambda _: self.Disconnected())
        return d

    def stop(self):
        # set internal flag in device for disconnection
        self.device.sconn.state_dict['should_stop'] = True
        return self.disconnect()
