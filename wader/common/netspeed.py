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
"""Utilities to measure network speed in an hardware agnostic way"""

from math import floor
from time import time

from twisted.internet import task, defer

def bps_to_human(up, down):
    """
    Converts ``up`` and ``down`` from bits per second to human

    :param up: The upload speed in bits per second
    :param down: The download speed in bits per second
    :rtype: tuple
    """
    if up > 1000:
        upspeed = up / 1000.0
        downspeed = down / 1000.0
        upmsg = (upspeed > 1000) and "%3.2f Mbps" % (upspeed / 1000) or \
                    "%3.2f Kbps" % upspeed
        downmsg = (downspeed > 1000) and "%3.2f Mbps" % (downspeed / 1000) \
                    or "%3.2f Kbps" % downspeed
    else:
        upmsg = "%3.2f bps" % up
        downmsg = "%3.2f bps" % down

    return upmsg, downmsg

class NetworkSpeed(object):
    """Class to measure network speed"""

    INTERVAL = .5

    def __init__(self):
        self.speed = {'down': 0.0, 'up': 0.0}
        self.loop = task.LoopingCall(self.compute_stats)
        self.mutex = defer.DeferredLock()
        self._time = None
        self._inbits = 0
        self._outbits = 0

    def __getitem__(self, key):
        if not key in self.speed:
            raise IndexError("key %s not in %s" % (key, self.speed))

        return self.speed[key]

    def start(self):
        """Starts the measurement"""
        self.loop.start(self.INTERVAL, now=False)
        self._time = time()

    def stop(self):
        """Stops the measurement"""
        self.loop.stop()

    def compute_stats(self):
        """Extracts and computes the number of bytes recv/sent"""
        from wader.common.oal import osobj
        d = osobj.get_iface_stats()
        d.addCallback(self.update_stats)

    def update_stats(self, (inbits, outbits)):
        """Updates the stats with parse_input's result"""
        # Inspired by Gdesklet's Net.py module
        if inbits is None or outbits is None:
            return

        if not self._inbits or not self._outbits:
            self._inbits = inbits
            self._outbits = outbits

        def doit(ignored):
            now = time()
            interval = now - self._time

            in_diff = inbits - self._inbits
            out_diff = outbits - self._outbits

            self.speed['down'] = int(floor(in_diff / interval))
            self.speed['up'] = int(floor(out_diff / interval))

            self._inbits = inbits
            self._outbits = outbits
            self._time = now
            self.mutex.release()

        d = self.mutex.acquire()
        d.addCallback(doit)

