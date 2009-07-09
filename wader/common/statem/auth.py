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
"""Authentication state machine"""

from twisted.internet import reactor, defer
from twisted.python import log

from epsilon.modal import mode, Modal
import wader.common.aterrors as E

SIM_FAIL_DELAY = 15
MAX_NUM_SIM_ERRORS = 3
MAX_NUM_SIM_BUSY = 5


class AuthStateMachine(Modal):
    """I authenticate against a device"""
    modeAttribute = 'mode'
    initialMode = 'get_pin_status'
    DELAY = 15

    def __init__(self, device):
        self.device = device
        self.deferred = defer.Deferred()
        # it will be set to True if AT+CPIN? == +CPIN: READY
        self.auth_was_ready = False
        self.num_sim_errors = 0
        self.num_sim_busy = 0
        log.msg("starting %s ..." % self.__class__.__name__)

    def __repr__(self):
        return "authentication_sm"

    # keyring stuff
    def notify_auth_ok(self):
        """Called when authentication was successful"""
        self.deferred.callback(True)

    def notify_auth_failure(self, failure):
        """Called when we faced a failure"""
        log.msg("%s: notifying auth failure %s" % (self, failure))
        self.deferred.errback(failure)

    # states callbacks
    def check_pin_cb(self, resp):
        """Callbacked with check_pin's result"""
        self.auth_was_ready = True
        self.notify_auth_ok()

    def get_pin_status_cb(self, enabled):
        """Callbacked with get_pin_status's result"""
        if int(enabled):
            self.notify_auth_failure(E.SimPinRequired())
        else:
            self.notify_auth_ok()

    def incorrect_pin_eb(self, failure):
        """Executed when PIN is incorrect"""
        failure.trap(E.IncorrectPassword)
        self.notify_auth_failure(failure)

    def incorrect_puk_eb(self, failure):
        """Executed when the PUK is incorrect"""
        failure.trap(E.IncorrectPassword, E.GenericError)
        self.notify_auth_failure(E.IncorrectPassword())

    def incorrect_puk2_eb(self, failure):
        """Executed when the PUK2 is incorrect"""
        failure.trap(E.IncorrectPassword, E.GenericError)
        self.notify_auth_failure(E.IncorrectPassword())

    def pin_required_eb(self, failure):
        """Executed when SIM PIN is required"""
        failure.trap(E.SimPinRequired, E.GenericError)
        self.notify_auth_failure(E.SimPinRequired())

    def puk_required_eb(self, failure):
        """Executed when PUK/PUK2 is required"""
        failure.trap(E.SimPukRequired, E.SimPuk2Required)
        self.notify_auth_failure(failure)

    def sim_failure_eb(self, failure):
        """Executed when there's a SIM failure, try again in a while"""
        failure.trap(E.SimFailure)
        self.num_sim_errors += 1
        if self.num_sim_errors >= MAX_NUM_SIM_ERRORS:
            # we can now consider that there's something wrong with the
            # device, probably there's no SIM
            self.notify_auth_failure(E.SimNotInserted())
            return

        reactor.callLater(SIM_FAIL_DELAY, self.do_next)

    def sim_busy_eb(self, failure):
        """Executed when SIM is busy, try again in a while"""
        failure.trap(E.SimBusy, E.SimNotStarted, E.GenericError)
        self.num_sim_busy += 1
        if self.num_sim_busy >= MAX_NUM_SIM_BUSY:
            # we can now consider that there's something wrong with the
            # device, probably a firmwarebug
            self.notify_auth_failure(E.SimFailure())
            return

        reactor.callLater(SIM_FAIL_DELAY, self.do_next)

    def sim_no_present_eb(self, failure):
        """Executed when there's no SIM, errback it"""
        failure.trap(E.SimNotInserted)
        self.notify_auth_failure(failure)

    # entry point
    def start_auth(self):
        """
        Starts the authentication

        Returns a deferred that will be callbacked if everything goes alright

        :raise SimFailure: SIM unknown error
        :raise SimNotInserted: SIM not inserted
        :raise DeviceLockedError: Device is locked
        """
        self.do_next()
        return self.deferred

    # states
    class get_pin_status(mode):
        """
        Ask the PIN what's the PIN status

        The SIM can be in one of the following states:
         - SIM is ready (already authenticated, or PIN disabled)
         - PIN is needed
         - PIN2 is needed (not handled)
         - PUK/PUK2 is needed
         - SIM is not inserted
         - SIM's firmware error
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            log.msg("%s: transition to get_pin_status mode...." % self)
            d = self.device.sconn.check_pin()
            d.addCallback(self.check_pin_cb)
            d.addErrback(self.pin_required_eb)
            d.addErrback(self.puk_required_eb)
            d.addErrback(self.sim_failure_eb)
            d.addErrback(self.sim_busy_eb)
            d.addErrback(self.sim_no_present_eb)

    class pin_needed_status(mode):
        """
        Three things can happen:
         - Auth went OK
         - PIN is incorrect
         - After three failed PIN auths, PUK is needed
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            """
            Three things can happen:
             - Auth went OK
             - PIN is incorrect
             - After three failed PIN auths, PUK is needed
            """
            pass

    class puk_needed_status(mode):
        """
        Three things can happen:
         - Auth went OK
         - PUK/PIN is incorrect
         - After five failed attempts, PUK2 is needed
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            pass

    class puk2_needed_status(mode):
        """
        Three things can happen:
         - Auth went OK
         - PUK2/PIN is incorrect
         - After ten failed attempts, device is locked
        """
        def __enter__(self):
            pass
        def __exit__(self):
            pass

        def do_next(self):
            pass

