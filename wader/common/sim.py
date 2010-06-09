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
"""SIM startup module"""

from twisted.python import log
from twisted.internet import defer, reactor

import wader.common.aterrors as E
from wader.common.encoding import from_ucs2

RETRY_ATTEMPTS = 3
RETRY_TIMEOUT = 3


class SIMBaseClass(object):
    """
    I take care of initing the SIM

    The actual details of initing the SIM vary from mobile to datacard, so
    I am the one to subclass in case your device needs a special startup
    """

    def __init__(self, sconn):
        super(SIMBaseClass, self).__init__()
        self.sconn = sconn
        self.size = None
        self.charset = 'IRA'
        self.num_of_failures = 0

    def set_size(self, size):
        log.msg("Setting size to %d" % size)
        self.size = size

    def set_charset(self, charset):
        try:
            self.charset = from_ucs2(charset)
        except (UnicodeDecodeError, TypeError):
            self.charset = charset
        return charset

    def setup_sms(self):
        # Notification when a SMS arrives...
        self.sconn.set_sms_indication(2, 1, 0, 1, 0)
        # set PDU mode
        self.sconn.set_sms_format(0)

    def initialize(self, set_encoding=True):
        """
        Initializes the SIM card

        This method sets up encoding, SMS format and notifications
        in the SIM. It returns a deferred with the SIM size.
        """
        # set up extended error reporting
        self.sconn.send_at('AT+CMEE=1')

        if set_encoding:
            self._setup_encoding()

        self.setup_sms()

        deferred = defer.Deferred()

        def get_size(auxdef):
            d = self.sconn.get_phonebook_size()

            def phonebook_size_cb(resp):
                self.set_size(resp)
                auxdef.callback(self.size)

            def phonebook_size_eb(failure):
                failure.trap(E.GenericError, E.SimBusy, E.SimFailure)
                self.num_of_failures += 1
                if self.num_of_failures > RETRY_ATTEMPTS:
                    # fail gracefully for now, we'll try again
                    # the next time a contact operation is required
                    auxdef.callback(None)
                    return

                reactor.callLater(RETRY_TIMEOUT, get_size, auxdef)

            d.addCallback(phonebook_size_cb)
            d.addErrback(phonebook_size_eb)

            return auxdef

        return get_size(deferred)

    def _set_charset(self, charset):
        """
        Checks whether is necessary the change and memorizes the used charset
        """

        def process_charset(reply):
            """
            Only set the new charset if is different from current encoding
            """
            if reply != charset:
                return self.sconn.set_charset(charset)

            # we already have the wanted charset
            self.charset = reply
            return defer.succeed(True)

        d = self.sconn.get_charset()
        d.addCallback(process_charset)
        return d

    def _process_charsets(self, charsets):
        for charset in ["UCS2", "IRA", "GSM"]:
            if charset in charsets:
                return self._set_charset(charset)

        msg = "Couldn't find an appropriated charset in %s"
        raise E.CharsetError(msg % charsets)

    def _setup_encoding(self):
        d = self.sconn.get_charsets()
        d.addCallback(self._process_charsets)
        return d
