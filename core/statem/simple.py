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
from twisted.internet import defer, reactor
from twisted.python import log

import wader.common.aterrors as E
from wader.common.consts import STATUS_HOME, STATUS_ROAMING
from wader.common.utils import convert_network_mode_to_allowed_mode

# poll at 'n' second intervals for 'm' tries
INTERVAL = 3
TRIES = 30


class SimpleStateMachine(Modal):
    """I am a state machine for o.fd.ModemManager.Modem.Simple"""

    modeAttribute = 'mode'
    initialMode = 'begin'

    def __init__(self, device, settings):
        self.device = device
        self.sconn = device.sconn

        # XXX: Currently, as of NM 0.8, nm-applet always passes
        #      'network_mode'=ANY in ConnectSimple. We have to
        #      remove it here or we stamp on the card setting
        #      done from the user's profile
        if 'network_mode' in settings:
            del settings['network_mode']

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
            self.registration_tries = TRIES
            self.transition_to('check_pin')

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
            log.msg("Simple SM: set_band exited")

        def do_next(self):
            if 'band' in self.settings:
                d = self.sconn.set_band(self.settings['band'])
                d.addCallback(lambda _:
                        reactor.callLater(1,
                                       self.transition_to, 'set_allowed_mode'))
            else:
                self.transition_to('set_allowed_mode')

    class set_allowed_mode(mode):

        def __enter__(self):
            log.msg("Simple SM: set_allowed_mode entered")

        def __exit__(self):
            log.msg("Simple SM: set_allowed_mode exited")

        def do_next(self):

            def get_network_mode_cb(mode):
                allowed = convert_network_mode_to_allowed_mode(mode)

                if allowed == self.settings['allowed_mode']:
                    log.msg("Simple SM: set_allowed_mode is current")
                    self.transition_to('wait_for_registration')
                else:
                    log.msg("Simple SM: set_allowed_mode change required")
                    d2 = self.sconn.set_allowed_mode(
                            self.settings['allowed_mode'])
                    # We need to wait long enough for the device to start
                    # switching and lose the current registration
                    d2.addCallback(lambda _: reactor.callLater(5,
                            self.transition_to, 'wait_for_registration'))

            if 'allowed_mode' in self.settings:
                d = self.sconn.get_network_mode()
                d.addCallback(get_network_mode_cb)
            else:
                self.transition_to('wait_for_registration')

    class wait_for_registration(mode):

        def __enter__(self):
            log.msg("Simple SM: wait_for_registration entered")

        def __exit__(self):
            log.msg("Simple SM: wait_for_registration exited")

        def do_next(self):

            def get_netreg_status_cb(info):
                if info[1] in [STATUS_HOME, STATUS_ROAMING]:
                    self.transition_to('connect')
                elif self.registration_tries <= 0:
                    self.notify_failure(E.NoNetwork("Not registered"))
                else:
                    self.registration_tries -= 1
                    reactor.callLater(INTERVAL, self.do_next)

            d = self.sconn.get_netreg_status()
            d.addCallback(get_netreg_status_cb)

    class connect(mode):

        def __enter__(self):
            log.msg("Simple SM: connect entered")

        def __exit__(self):
            log.msg("Simple SM: connect exited")

        def do_next(self):
            self.settings['number'] = \
                "*99***%d#" % self.sconn.state_dict.get('conn_id')
            d = self.sconn.connect_to_internet(self.settings)
            d.addCallback(lambda _: self.transition_to('done'))

    class done(mode):

        def __enter__(self):
            log.msg("Simple SM: done entered")

        def __exit__(self):
            log.msg("Simple SM: done exited")

        def do_next(self):
            self.notify_success()
