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
"""org.freedesktop.ModemManager.Modem.Simple state machine"""

from epsilon.modal import mode, Modal
from twisted.python import log
from twisted.internet import defer, reactor

import wader.common.aterrors as E


class SimpleStateMachine(Modal):
    """I am a state machine for o.fd.ModemManager.Modem.Simple"""

    modeAttribute = 'mode'
    initialMode = 'begin'

    def __init__(self, device, settings):
        self.device = device
        self.sconn = device.sconn
        self.settings = settings

        self.deferred = defer.Deferred()

    def transition_to(self, state):
        self.transitionTo(state)
        self.do_next()

    def start_simple(self):
        """Starts the whole process"""
        self.do_next()
        return self.deferred

    def notify_success(self, ignored=True):
        """Notifies the caller that we have succeed"""
        self.deferred.callback(ignored)

    def notify_failure(self, failure):
        """Notifies the caller that we have failed"""
        self.deferred.errback(failure)

    class begin(mode):

        def __enter__(self):
            log.msg("Simple SM: begin entered")

        def __exit__(self):
            log.msg("Simple SM: begin exited")

        def do_next(self):
            # start by enabling device
            d = self.sconn.enable_device(True)
            d.addCallback(lambda _: self.transition_to('check_pin'))

    class check_pin(mode):
        """We are going to check whether auth is ready or not"""

        def __enter__(self):
            log.msg("Simple SM: check_pin entered")

        def __exit__(self):
            log.msg("Simple SM: check_pin exited")

        def do_next(self):
            # check the auth state, if its ready go to next state
            # otherwise try to auth with the provided pin, give it
            # some seconds to settle and go to next state
            def check_pin_cb(ignored, wait=False):
                if not wait:
                    self.transition_to('register')
                else:
                    DELAY = self.device.custom.auth_klass.DELAY
                    reactor.callLater(DELAY, self.transition_to, 'register')

            def check_pin_eb_pin_needed(failure):
                failure.trap(E.SimPinRequired)
                if 'pin' not in self.settings:
                    self.notify_failure(E.SimPinRequired("No pin provided"))
                    return

                d = self.sconn.send_pin(self.settings['pin'])
                d.addCallback(check_pin_cb, wait=True)
                d.addErrback(self.notify_failure)

            d = self.sconn.check_pin()
            d.addCallback(check_pin_cb)
            d.addErrback(check_pin_eb_pin_needed)

    class register(mode):
        """Registers with the given network id"""

        def __enter__(self):
            log.msg("Simple SM: register entered")

        def __exit__(self):
            log.msg("Simple SM: register exited")

        def do_next(self):
            if 'network_id' in self.settings:
                netid = self.settings['network_id']
                d = self.sconn.register_with_netid(netid)
                d.addCallback(lambda _: self.transition_to('set_apn'))
            else:
                self.transition_to('set_apn')

    class set_apn(mode):

        def __enter__(self):
            log.msg("Simple SM: set_apn entered")

        def __exit__(self):
            log.msg("Simple SM: set_apn exited")

        def do_next(self):
            if 'apn' in self.settings:
                d = self.sconn.set_apn(self.settings['apn'])
                d.addCallback(lambda _: self.transition_to('set_band'))
            else:
                self.transition_to('set_band')

    class set_band(mode):

        def __enter__(self):
            log.msg("Simple SM: set_band entered")

        def __exit__(self):
            log.msg("Simple SM: set_apn exited")

        def do_next(self):
            if 'band' in self.settings:
                d = self.sconn.set_band(self.settings['band'])
                d.addCallback(lambda _:
                        reactor.callLater(1,
                                       self.transition_to, 'set_network_mode'))
            else:
                self.transition_to('set_network_mode')

    class set_network_mode(mode):

        def __enter__(self):
            log.msg("Simple SM: set_network_mode entered")

        def __exit__(self):
            log.msg("Simple SM: set_network_mode exited")

        def do_next(self):
            if 'network_mode' in self.settings:
                d = self.sconn.set_network_mode(self.settings['network_mode'])
                d.addCallback(lambda _:
                        reactor.callLater(1, self.transition_to, 'connect'))
            else:
                self.transition_to('connect')

    class connect(mode):

        def __enter__(self):
            log.msg("Simple SM: connect entered")

        def __exit__(self):
            log.msg("Simple SM: connect exited")

        def do_next(self):
            number = self.settings['number']
            d = self.sconn.connect_to_internet(number)
            d.addCallback(lambda _: self.transition_to('done'))

    class done(mode):

        def __enter__(self):
            log.msg("Simple SM: done entered")

        def __exit__(self):
            log.msg("Simple SM: done exited")

        def do_next(self):
            self.notify_success()
