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
"""Network registration state machine"""

import dbus
from twisted.python import log
from twisted.internet import defer, reactor

import wader.common.exceptions as ex
import wader.common.aterrors as E
from wader.common.signals import SIG_CREG
from wader.common.consts import (WADER_SERVICE, STATUS_IDLE, STATUS_HOME,
                                 STATUS_SEARCHING, STATUS_DENIED,
                                 STATUS_UNKNOWN, STATUS_ROAMING)
from wader.contrib.modal import mode, Modal

REGISTER_TIMEOUT = 15
MAX_WAIT_TIMES = 6


class NetworkRegistrationStateMachine(Modal):
    """I am a network registration state machine"""

    modeAttribute = 'mode'
    initialMode = 'check_registration'

    def __init__(self, sconn, netid=""):
        self.sconn = sconn
        self.netid = netid
        self.deferred = defer.Deferred()
        self.call_id = None
        # used to track how many times we've been waiting for a new event
        self.wait_counter = 0
        self.registering = False
        self.tried_manual_registration = False
        self.signal_matchs = []
        self.connect_to_signals()

        log.msg("starting %s ..." % self.__class__.__name__)

    def __repr__(self):
        return "network_sm"

    def connect_to_signals(self):
        bus = dbus.SystemBus()
        device = bus.get_object(WADER_SERVICE, self.sconn.device.opath)
        sm = device.connect_to_signal(SIG_CREG, self.on_netreg_cb)
        self.signal_matchs.append(sm)

    def clean_signals(self):
        while self.signal_matchs:
            sm = self.signal_matchs.pop()
            sm.remove()

    def start_netreg(self):
        """
        Starts the network registration process

        Returns a deferred that will be callbacked upon success and
        errbacked with a CMEError30 or a NetworkRegistrationError if fails
        """
        self.do_next()
        return self.deferred

    def notify_success(self, ignored=True):
        """Notifies the caller that we have succeed"""
        try:
            self.deferred.callback(ignored)
        except defer.AlreadyCalledError:
            pass

        self.cancel_counter()
        self.clean_signals()

    def notify_failure(self, failure):
        """Notifies the caller that we have failed"""
        try:
            self.deferred.errback(failure)
        except defer.AlreadyCalledError:
            pass

        self.cancel_counter()
        self.clean_signals()

    def cancel_counter(self):
        if self.call_id is not None and not self.call_id.called:
            self.call_id.cancel()
            self.call_id = None

    def restart_counter_or_transition(self, timeout=REGISTER_TIMEOUT):
        self.cancel_counter()
        self.wait_counter += 1
        if self.wait_counter <= MAX_WAIT_TIMES:
            self.call_id = reactor.callLater(timeout,
                                             self.check_if_registered)
        elif not self.tried_manual_registration:
            self.transitionTo('manual_registration')
            self.do_next()
        else:
            # we have already tried to register manually and it failed
            self.notify_failure(E.Unknown())

    def register_with_netid(self, netid):
        self.tried_manual_registration = True
        d = self.sconn.register_with_netid(netid)
        d.addCallback(lambda ign: self.check_if_registered())

    def check_if_registered(self):
        d = self.sconn.get_netreg_status()
        d.addCallback(self.process_netreg_status)

    def on_netreg_cb(self, status):
        """Callback for +CREG notifications"""
        # we fake 'mode == 1' as we've already enabled it
        self.process_netreg_status((1, status))

    def process_netreg_status(self, info):
        """Processes get_netreg_status callback and reacts accordingly"""
        _mode, status = info

        if status == STATUS_IDLE:
            # we are not looking for a network
            # set up +CREG notification and start network search
            if not _mode:
                self.sconn.set_netreg_notification(1)

            if not self.registering:
                self.sconn.send_at('AT+COPS=0,,')
                self.registering = True

            self.restart_counter_or_transition()

        elif status in [STATUS_SEARCHING, STATUS_UNKNOWN]:
            # we are looking for a network, give it some time.
            # +CREG: 4 is officially unknown, but it's been seen during
            # Ericsson F3507g radio power up, and with Huawei E173 immediately
            # before registration; in neither case is it fatal.
            if not _mode:
                self.sconn.set_netreg_notification(1)

            self.restart_counter_or_transition()

        elif status in [STATUS_HOME, STATUS_ROAMING]:
            # We have already found our network -unless a netid was
            # specified. Lets check if the contraints are satisfied
            self.registering = False
            self.transitionTo('check_constraints')
            self.do_next()

        elif status == STATUS_DENIED:
            # Network registration has been denied
            self.registering = False
            msg = 'Net registration failed: +CREG: %d,%d' % (_mode, status)
            self.notify_failure(ex.NetworkRegistrationError(msg))
            return

    def process_netreg_info(self, info):
        """
        Checks if we are registered with the supplied operator (if any)

        It will transition to manual_registration if necessary
        """
        status, netid, long_name = info

        if self.netid == netid:
            return self.notify_success()

        # turns out we're registered with an operator we shouldn't be
        self.transitionTo('manual_registration')
        self.do_next()

    def find_netid_to_register_with(self, imsi_prefix):
        """
        Registers with the first netid that appears in both +COPS=? and +CPOL?
        """
        # we have tried to register with our home network and it has
        # failed. We'll try to register with the first netid present
        # in AT+COPS=? and AT+CPOL?
        def process_netnames(networks):
            for n in networks:
                if n.netid in [self.netid, imsi_prefix]:
                    assert self.registering == False, "Registering again?"
                    self.register_with_netid(n.netid)
                    self.registering = True

            def process_roaming_ids_cb(roam_operators):
                for roam_operator in roam_operators:
                    if roam_operator in networks:
                        assert self.registering == False, "Registering again?"
                        self.register_with_netid(roam_operator.netid)
                        self.registering = True
                        break
                else:
                    msg = "Couldnt find a netid in %s and %s to register with"
                    args = (roam_operators, networks)
                    raise ex.NetworkRegistrationError(msg % args)

            def process_roaming_ids_eb(failure):
                # +CME ERROR 3, +CME ERROR 4
                failure.trap(E.OperationNotAllowed, E.OperationNotSupported)
                msg = "Couldnt find a netid in %s to register with"
                raise ex.NetworkRegistrationError(msg % networks)

            d = self.sconn.get_roaming_ids()
            d.addCallback(process_roaming_ids_cb)
            d.addErrback(process_roaming_ids_eb)

        d = self.sconn.get_network_names()
        d.addCallback(process_netnames)

    # states
    class check_registration(mode):
        """I check +CREG to see whats the initial status"""

        def __enter__(self):
            log.msg("%s: check_registration entered" % self)

        def __exit__(self):
            log.msg("%s: check_registration exited" % self)

        def do_next(self):
            d = self.sconn.get_netreg_status()
            d.addCallback(self.process_netreg_status)

    class check_constraints(mode):
        """
        We are registered with our home network or roaming

        We are going to check whether it satisfies our constraints or not
        """

        def __enter__(self):
            log.msg("%s: check_constraints entered" % self)

        def __exit__(self):
            log.msg("%s: check_constraints exited" % self)

        def do_next(self):
            if not self.netid:
                # no netid specified and we're already registered with our
                # home network or roaming, this is success
                self.notify_success()
                return

            d = self.sconn.get_netreg_info()
            d.addCallback(self.process_netreg_info)

    class manual_registration(mode):
        """
        I start the manual registration process

        This is due to a +CREG: 1,2 or because the card automatically
        registered with an operator and its netid doesn't matches with the
        one specified by the user
        """

        def __enter__(self):
            log.msg("%s: manual_registration entered" % self)

        def __exit__(self):
            log.msg("%s: manual_registration exited" % self)

        def do_next(self):

            def process_imsi_cb(imsi):
                imsi = imsi[:5]
                assert self.registering == False, "Registering again?"
                if imsi == self.netid:
                    # if we've been specified a netid, we cannot do
                    # much more than trying to register with it and
                    # if it fails return asap
                    self.register_with_netid(imsi)
                    self.registering = True
                else:
                    # look for a netid to register with
                    self.find_netid_to_register_with(imsi)

            log.msg("%s: obtaining the IMSI..." % self)
            d = self.sconn.get_imsi()
            d.addCallback(process_imsi_cb)
