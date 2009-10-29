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
from wader.common.hardware.option import NO_AUTH, PAP_AUTH, CHAP_AUTH
from wader.common.oal import osobj


class HSODialer(Dialer):
    """Dialer for HSO devices"""

    def __init__(self, device, opath, **kwds):
        super(HSODialer, self).__init__(device, opath, **kwds)
        # XXX: hardcoding iface to hso0
        self.iface = 'hso0'

    def configure(self, config):
        if not config.refuse_chap:
            auth = CHAP_AUTH
        elif not config.refuse_pap:
            auth = PAP_AUTH
        else:
            auth = NO_AUTH

        d = self.device.sconn.set_apn(config.apn)
        d.addCallback(lambda _: self.device.sconn.hso_authenticate(
                                       config.username, config.password, auth))
        return d

    def connect(self):
        # start the connection
        conn_id = self.device.sconn.state_dict['conn_id']
        self.device.sconn.send_at('AT_OWANCALL=%d,1,0' % conn_id)
        # now get the IP4Config and set up device and routes
        d = self.device.sconn.get_ip4_config()
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
        conn_id = self.device.sconn.state_dict['conn_id']
        d = self.device.sconn.send_at('AT_OWANCALL=%d,0,0' % conn_id)
        osobj.delete_default_route(self.iface)
        osobj.delete_dns_info(None, self.iface)
        osobj.configure_iface(self.iface, '', 'down')
        d.addCallback(lambda _: self.Disconnected())
        return d

    def stop(self):
        return self.disconnect()
