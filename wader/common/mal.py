# -*- coding: utf-8 -*-
# Copyright (C) 2008-2010  Warp Networks, S.L.
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
"""Message Assembly Layer for Wader"""

from time import mktime

from twisted.internet import reactor
from twisted.internet.defer import  succeed, gatherResults, Deferred
from twisted.python import log

from messaging.sms import SmsDeliver
from messaging.sms.wap import (extract_push_notification,
                               is_a_wap_push_notification)

from wader.common.aterrors import (CMSError314, SimBusy, SimNotStarted,
                                   SimFailure)
from wader.common.signals import SIG_MMS, SIG_SMS, SIG_SMS_COMP, SIG_SMS_DELV
from wader.common.sms import Message
from wader.common.mms import dbus_data_to_mms

STO_INBOX, STO_DRAFTS, STO_SENT = 1, 2, 3
# XXX: What should this threshold be?
SMS_DATE_THRESHOLD = 5

MAL_RETRIES = 3
MAL_RETRY_TIMEOUT = 3


def debug(s):
    # Change this to remove debugging
    if 1:
        print s


def should_fragment_be_assembled(sms, fragment):
    """Returns True if ``fragment`` can be assembled to ``sms``"""
    if sms.completed:
        # SMS is completed, no way to assemble it
        return False

    if sms.ref != fragment.ref:
        # different sms id
        return False

    if sms.datetime is not None and fragment.datetime is not None:
        # if datetime is present convert it to unix time
        time1 = mktime(sms.datetime.timetuple())
        time2 = mktime(fragment.datetime.timetuple())
        if abs(time1 - time2) > SMS_DATE_THRESHOLD:
            return False

    if sms.cnt != fragment.cnt:
        # number of parts
        return False

    if sms.number != fragment.number:
        # different sender
        return False

    if sms.csca != fragment.csca:
        # different SMSC
        return False

    debug("MAL: Assembling fragment %s with sms %s" % (fragment, sms))
    return True


class CacheIncoherenceError(Exception):
    """Raised upon a cache incoherence error"""


class NotificationContainer(object):
    """
    I am a WAP push notification container

    I keep a list with all the wap_push notifications
    and provide some operations on it
    """

    def __init__(self, tx_id=None):
        self.notifications = []
        self.tx_id = tx_id

    def add_notification(self, wap_push, notification):
        self.notifications.append((wap_push, notification))

    def get_last_notification(self):
        """Returns the last received notification"""
        # comp function must return an int
        ret = sorted(self.notifications,
                     lambda _, n: int(mktime(n[0].datetime.timetuple())))
        # return the last element
        return ret[-1][1]


class MessageAssemblyLayer(object):
    """I am a transparent layer to perform operations on concatenated SMS"""

    def __init__(self, wrappee):
        self.wrappee = wrappee
        self.last_sms_index = 0
        self.last_wap_index = 0
        self.sms_map = {}
        self.wap_map = {}
        self.sms_pending = []
        self.cached = False

    def initialize(self, obj=None):
        debug("MAL::initialize obj: %s" % obj)
        if obj is not None:
            self.wrappee = obj

        # revert to initial state
        self.last_sms_index = self.last_wap_index = 0
        self.sms_map = {}
        self.sms_pending = []
        self.cached = False
        # populate sms cache
        return self._do_initialize()

    def _do_initialize(self):
        # init counter
        self.wrappee.state_dict['mal_init_retries'] = 0

        deferred = Deferred()

        def list_sms(auxdef):

            def sim_busy_eb(failure):
                failure.trap(SimBusy, SimNotStarted, CMSError314)
                self.wrappee.state_dict['mal_init_retries'] += 1
                if self.wrappee.state_dict['mal_init_retries'] > MAL_RETRIES:
                    raise SimFailure("Could not initialize MAL")

                reactor.callLater(MAL_RETRY_TIMEOUT, list_sms, auxdef)

            d = self.list_sms()
            d.addErrback(sim_busy_eb)
            d.chainDeferred(auxdef)
            return auxdef

        return list_sms(deferred)

    def _do_add_sms(self, sms, indexes=None):
        """
        Adds ``sms`` to the cache using ``indexes`` if defined

        It returns the logical index where it was stored
        """
        debug("MAL::_do_add_sms sms: %s  indexes: %s" % (sms, indexes))
        # save the real index if indexes is None
        sms.real_indexes = [sms.index] if indexes is None else indexes
        debug("MAL::_do_add_sms sms.real_indexes %s" % sms.real_indexes)
        # assign a new logical index
        self.last_sms_index += 1
        sms.index = self.last_sms_index
        # reference the sms by this logical index
        self.sms_map[self.last_sms_index] = sms
        return self.last_sms_index

    def _add_sms(self, sms, emit=False):
        """
        Adds ``sms`` to the cache

        It returns the logical index where it was stored
        """
        debug("MAL::_add_sms: %s" % sms)
        if not sms.cnt:
            index = self._do_add_sms(sms)
            debug("MAL::_add_sms  single part SMS added with "
                  "logical index: %d" % index)
            # being a single part sms, completed == True
            if emit:
                for signal in [SIG_SMS, SIG_SMS_COMP]:
                    self.wrappee.emit_signal(signal, index, True)
            return index
        else:
            for index, value in self.sms_map.iteritems():
                if should_fragment_be_assembled(value, sms):
                    # append the sms and emit the different signals
                    completed = self.sms_map[index].append_sms(sms)
                    debug("MAL::_add_sms  multi part SMS with logical "
                          "index %d, completed %s" % (index, completed))

                    # check if we have just assembled a WAP push notification
                    if completed:
                        notification = self.sms_map[index]
                        if self._is_a_wap_push_notification(notification):
                            self._process_wap_push_notification(index, emit)
                            # there's no need to return an index here as we
                            # have been called by gen_cache and mms have a
                            # different index scheme than mms.
                            return

                    if emit:
                        # only emit signals in runtime, not startup
                        self.wrappee.emit_signal(SIG_SMS, index, completed)
                        if completed:
                            self.wrappee.emit_signal(SIG_SMS_COMP, index,
                                                     completed)

                    # return sms logical index
                    return index

            # this is the first fragment of this multipart sms, add it
            # to cache, emit signal and wait for the rest of fragments
            # to arrive. It returns the logical index where was stored
            index = self._do_add_sms(sms)
            if emit:
                self.wrappee.emit_signal(SIG_SMS, index, False)
            debug("MAL::_add_sms first part of a multi part SMS added with"
                  "logical index %d" % index)
            return index

    def _after_ack_delete_notifications(self, _, index):
        try:
            container = self.wap_map.pop(index)
        except KeyError:
            debug("MessageAssemblyLayer::_after_ack_delete_notifications"
                  " NotificationContainer %d does not exist" % index)
            return

        indexes = []
        for wap_push, _ in container.notifications:
            indexes.extend(wap_push.real_indexes)

        ret = map(self.wrappee.do_delete_sms, indexes)
        return gatherResults(ret)

    def acknowledge_mms(self, index, extra_info):
        d = self.wrappee.do_acknowledge_mms(index, extra_info)
        d.addCallback(self._after_ack_delete_notifications, index)
        return d

    def delete_sms(self, index):
        """Deletes sms identified by ``index``"""
        debug("MAL::delete_sms: %d" % index)
        if index in self.sms_map:
            sms = self.sms_map.pop(index)
            ret = map(self.wrappee.do_delete_sms, sms.real_indexes)
            debug("MAL::delete_sms deleting %s" % sms.real_indexes)
            return gatherResults(ret)

        error = "SMS with logical index %d does not exist"
        raise CacheIncoherenceError(error % index)

    def download_mms(self, index, extra_info):
        container = self.wap_map[index]
        d = self.wrappee.do_download_mms(container.get_last_notification(),
                                         extra_info)
        return d

    def get_sms(self, index):
        """Returns the sms identified by ``index``"""
        if index in self.sms_map:
            return succeed(self.sms_map[index])

        error = "SMS with logical index %d does not exist"
        raise CacheIncoherenceError(error % index)

    def list_available_mms_notifications(self):
        """Returns all the lingering sms wap push notifications"""
        ret = []
        for index, container in self.wap_map.items():
            notification = container.get_last_notification()
            ret.append((index, self._clean_headers(notification)))

        return succeed(ret)

    def _list_sms(self):
        ret = []
        for sms in self.sms_map.values():
            if sms.fmt != 0x04:
                ret.append(sms.to_dict())

        return ret

    def list_sms(self):
        """Returns all the sms"""
        debug("MAL::list_sms")

        def gen_cache(messages):
            debug("MAL::list_sms::gen_cache")
            for sms in messages:
                self._add_sms(sms)

            self.cached = True
            return self._list_sms()

        if self.cached:
            debug("MAL::list_sms::cached path")
            return succeed(self._list_sms())

        d = self.wrappee.do_list_sms()
        d.addCallback(gen_cache)
        return d

    def send_mms(self, mms, extra_info):
        debug("MAL::send_mms: %s" % mms)
        d = self.wrappee.do_send_mms(dbus_data_to_mms(mms), extra_info)
        return d

    def send_sms(self, sms):
        debug("MAL::send_sms: %s" % sms)
        if not sms.status_request:
            return self.wrappee.do_send_sms(sms)

        d = self.wrappee.do_send_sms(sms)
        d.addCallback(self._save_sms_reference, sms)
        return d

    def send_sms_from_storage(self, index):
        debug("MAL::send_sms_from_storage: %d" % index)
        if index in self.sms_map:
            sms = self.sms_map.pop(index)
            indexes = sorted(sms.real_indexes)
            debug("MAL::send_sms_from_storage sending %s" % indexes)
            ret = map(self.wrappee.do_send_sms_from_storage, indexes)
            return gatherResults(ret)

        error = "SMS with logical index %d does not exist"
        raise CacheIncoherenceError(error % index)

    def save_sms(self, sms):
        """Saves ``sms`` in the cache memorizing the resulting indexes"""
        debug("MAL::save_sms: %s" % sms)
        d = self.wrappee.do_save_sms(sms)
        d.addCallback(lambda indexes: self._do_add_sms(sms, indexes))
        d.addCallback(lambda logical_index: [logical_index])
        return d

    def _save_sms_reference(self, indexes, sms):
        sms.status_references.extend(indexes)
        sms.status_reference = indexes[0]
        self.sms_pending.append(sms)
        return [sms.status_reference]

    def on_sms_delivery_report(self, pdu):
        """Executed when a SMS delivery report is received"""
        data = SmsDeliver(pdu).data
        sms = Message.from_dict(data)
        assert sms.is_status_report(), "SMS IS NOT STATUS REPORT"
        # XXX: O(N) here
        for _sms in self.sms_pending:
            if sms.ref in _sms.status_references:
                # one confirmation received
                _sms.status_references.remove(sms.ref)
                # no more status references? Then we are done, remove it from
                # the status_references list and emit signal
                if not _sms.status_references:
                    self.sms_pending.remove(_sms)
                    return self.wrappee.emit_signal(SIG_SMS_DELV,
                                                    _sms.status_reference)
                break
        else:
            log.err("Received status report with "
                    "unknown reference: %d" % sms.ref)

    def on_sms_notification(self, index):
        """Executed when a SMS notification is received"""
        debug("MAL::on_sms_notification: %d" % index)
        d = self.wrappee.do_get_sms(index)
        d.addCallback(self._add_sms, emit=True)
        return d

    def _is_a_wap_push_notification(self, sms):
        """Returns True if ``sms`` is a WAP push notification"""
        if sms.fmt != 0x04:
            return False

        return is_a_wap_push_notification(sms.text)

    def _process_wap_push_notification(self, index, emit):
        """
        Processes WAP push notification identified by ``index``

        If ``emit`` is True, it will emit a MMSReceived signal
        if this the first time we see this notification.
        """
        wap_push = self.sms_map.pop(index)
        notification, tx_id = extract_push_notification(wap_push.text)

        index = None
        _from = notification.headers['From']
        for i, container in self.wap_map.items():
            if container.tx_id != tx_id:
                continue

            noti = container.get_last_notification()
            if _from == noti.headers['From']:
                index = i
                break
        else:
            index = self.last_wap_index
            self.last_wap_index += 1

        container = self.wap_map.get(index, NotificationContainer(tx_id))
        container.add_notification(wap_push, notification)
        self.wap_map[index] = container

        if emit:
            # emit the signal
            notification = container.get_last_notification()
            headers = self._clean_headers(notification)
            self.wrappee.emit_signal(SIG_MMS, index, headers)

    def _clean_headers(self, notification):
        """Clean ``headers`` so its safe to send the dict via DBus"""
        hdrs = notification.headers.copy()
        hdrs['Content-Type'] = notification.content_type
        return hdrs
