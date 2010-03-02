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
"""SMS module for Wader"""

from datetime import datetime
from operator import itemgetter
from time import mktime

from zope.interface import implements
from twisted.internet.defer import  succeed, gatherResults
from twisted.python import log
from messaging import PDU

from wader.common.interfaces import IMessage
from wader.common.signals import SIG_SMS, SIG_SMS_COMP, SIG_SMS_DELV

STO_INBOX, STO_DRAFTS, STO_SENT = 1, 2, 3
# XXX: What should this threshold be?
SMS_DATE_THRESHOLD = 5

SMS_STATUS_REPORT = 0x03


p = PDU()


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


class MessageAssemblyLayer(object):
    """I am a transparent layer to perform operations on concatenated SMS'"""

    def __init__(self, wrappee):
        self.wrappee = wrappee
        self.last_index = 0
        self.sms_map = {}
        self.sms_pending = []
        self.cached = False

    def initialize(self, obj=None):
        debug("MAL::initialize  obj: %s" % obj)
        if obj is not None:
            self.wrappee = obj

        # revert to initial state
        self.last_index = 0
        self.sms_map = {}
        self.sms_pending = []
        self.cached = False
        # populate sms cache
        self.list_sms()

    def _do_add_sms(self, sms, indexes=None):
        """
        Adds ``sms`` to the cache using ``indexes`` if defined

        It returns the logical index where it was stored
        """
        debug("MAL::_do_add_sms  sms: %s  indexes: %s" % (sms, indexes))
        # save the real index if indexes is None
        sms.real_indexes = [sms.index] if indexes is None else indexes
        debug("MAL::_do_add_sms sms.real_indexes %s" % sms.real_indexes)
        # assign a new logical index
        self.last_index += 1
        sms.index = self.last_index
        # reference the sms by this logical index
        self.sms_map[self.last_index] = sms
        return self.last_index

    def _add_sms(self, sms, emit=False):
        """
        Adds ``sms`` to the cache

        It returns the logical index where it was stored
        """
        debug("MAL::_add_sms: %s" % sms)
        if not sms.cnt:
            index = self._do_add_sms(sms)
            debug("MAL::_add_sms  single part SMS added with logical index: %d" % index)
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
                    debug("MAL::_add_sms  multi part SMS with logical index %d, completed %s" % (index, completed))

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
            debug("MAL::_add_sms first part of a multi part SMS added with logical index %d" % index)
            return index

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

    def get_sms(self, index):
        """Returns the sms identified by ``index``"""
        if index in self.sms_map:
            return succeed(self.sms_map[index])

        error = "SMS with logical index %d does not exist"
        raise CacheIncoherenceError(error % index)

    def list_sms(self):
        """Returns all the sms"""
        debug("MAL::list_sms")

        def gen_cache(messages):
            debug("MAL::list_sms::gen_cache")
            for sms in messages:
                self._add_sms(sms)

            self.cached = True
            return [sms.to_dict() for sms in self.sms_map.values()]

        if self.cached:
            debug("MAL::list_sms::cached path")
            return succeed([sms.to_dict() for sms in self.sms_map.values()])

        d = self.wrappee.do_list_sms()
        d.addCallback(gen_cache)
        return d

    def send_sms(self, sms):
        debug("MAL::send_sms: %s" % sms)
        sms.status_request = True
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
        report = p.decode_pdu(pdu)
        sms = Message.from_dict(report)
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
            log.err("Received status report with unknown reference: %d" % sms.ref)

    def on_sms_notification(self, index):
        """Executed when a SMS notification is received"""
        debug("MAL::on_sms_notification: %d" % index)
        d = self.wrappee.do_get_sms(index)
        d.addCallback(self._add_sms, emit=True)
        return d


class Message(object):
    """I am a Message in the system"""

    implements(IMessage)

    def __init__(self, number=None, text=None, index=None, where=None,
                 csca=None, _datetime=None, ref=None, cnt=None, seq=None):
        self.number = number
        self.index = index
        self.real_indexes = []
        self.where = where
        self.csca = csca
        self.datetime = _datetime
        self.ref = ref  # Multipart SMS reference number
        self.cnt = cnt  # Total number of fragments
        self.seq = seq  # fragment number
        self.completed = False
        self.status_request = False
        self.status_references = []
        self.status_reference = None
        self.type = None
        self._fragments = []

        if text is not None:
            # SmsSubmit
            self.add_text_fragment(text)
            self.completed = True

    @property
    def text(self):
        return "".join(text for index, text
                            in sorted(self._fragments, key=itemgetter(0)))

    def __repr__(self):
        import pprint
        import StringIO
        out = StringIO.StringIO()
        props = {'number': self.number,
                 'index': self.index,
                 'real_indexes': self.real_indexes,
                 'csca': self.csca,
                 'datetime': self.datetime,
                 'reference': self.ref,
                 'count': self.cnt,
                 'sequence': self.seq,
                 'completed': self.completed,
                 'fragments': self._fragments}

        pp = pprint.PrettyPrinter(indent=4, stream=out)
        pp.pprint(props)
        return out.getvalue()

    def __eq__(self, m):
        if all([self.index, m.index]):
            return self.index == m.index

        return self.number == m.number and self.text == m.text

    def __ne__(self, m):
        return not self.__eq__(m)

    @classmethod
    def from_dict(cls, d, tz=None):
        """
        Converts ``d`` to a :class:`Message`

        :param d: The dict to be converted
        :param tz: The timezone of the datetime
        :rtype: ``Message``
        """
        m = cls(number=d['number'])

        m.index = d.get('index')
        m.where = d.get('where')
        m.csca = d.get('smsc')
        m.ref = d.get('ref')
        m.status_request = d.get('status_request', False)
        m.cnt = d.get('cnt', 0)
        m.seq = d.get('seq', 0)
        m.type = d.get('type')

        if 'text' in d:
            m.add_text_fragment(d['text'])
            m.completed = True

        if 'timestamp' in d:
            m.datetime = datetime.fromtimestamp(d['timestamp'], tz)

        debug("Message::from_dict returning: %s" % m)
        return m

    @classmethod
    def from_pdu(cls, pdu):
        """
        Converts ``pdu`` to a :class:`Message` object

        :param pdu: The PDU to convert
        :rtype: ``Message``
        """
        debug("Message::from_pdu: %s" % pdu)
        ret = p.decode_pdu(pdu)

        _datetime = None
        if 'date' in ret:
            try:
                _datetime = extract_datetime(ret['date'])
            except ValueError:
                _datetime = datetime.now()


        m = cls(ret['number'], _datetime=_datetime, csca=ret['csca'],
                ref=ret['ref'], cnt=ret['cnt'], seq=ret['seq'])
        m.type = ret.get('type')
        m.add_text_fragment(ret['text'], ret['seq'])

        debug("Message::from_pdu returning: %s" % m)
        return m

    def to_dict(self):
        """
        Returns a dict ready to be sent via DBus

        :rtype: dict
        """
        ret = dict(number=self.number, text=self.text)

        if self.where is not None:
            ret['where'] = self.where
        if self.index is not None:
            ret['index'] = self.index
        if self.datetime is not None:
            ret['timestamp'] = mktime(self.datetime.timetuple())
        if self.csca is not None:
            ret['smsc'] = self.csca
        if self.status_request:
            ret['status_request'] = self.status_request

        return ret

    def to_pdu(self, store=False):
        """Returns the PDU representation of this message"""
        csca = self.csca if self.csca is not None else ""

        return p.encode_pdu(self.number, self.text, csca=csca, store=store,
                            request_status=self.status_request)

    def add_fragment(self, sms):
        self.add_text_fragment(sms.text, sms.seq)

    def add_text_fragment(self, text, pos=0):
        self._fragments.append((pos, text))

    def append_sms(self, sms):
        """
        Appends ``sms`` text internally

        :rtype bool
        :return Whether the sms was successfully assembled or not
        """
        # quick filtering to rule out unwanted fragments
        if self.ref == sms.ref and self.cnt == sms.cnt:
            self.add_fragment(sms)
            self.real_indexes.extend(sms.real_indexes)
            self.real_indexes.sort()

            self.completed = len(self._fragments) == sms.cnt
            return self.completed
        else:
            error = "Cannot assembly SMS fragment with ref %d"
            raise ValueError(error % sms.ref)

    def is_status_report(self):
        if self.type is None:
            return False

        return bool(self.type & SMS_STATUS_REPORT)


def extract_datetime(datestr):
    """
    Returns a ``datetime`` instance out of ``datestr``

    :param datestr: Date string like YY/MM/DD HH:MM:SS
    :rtype: :class:`datetime.datetime`
    """
    #datestr comes like "YY/MM/DD HH:MM:SS"
    date, time = datestr.split(' ')
    year, month, day = map(int, date.split('/'))
    if year < 68:
        year += 2000
    hour, mins, seconds = map(int, time.split(':'))

    return datetime(year, month, day, hour, mins, seconds, tzinfo=None)
