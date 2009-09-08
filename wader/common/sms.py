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
from messaging import PDU

from wader.common.interfaces import IMessage
from wader.common.signals import SIG_SMS, SIG_SMS_COMP

STO_INBOX, STO_DRAFTS, STO_SENT = 1, 2, 3
# XXX: What should this threshold be?
SMS_DATE_THRESHOLD = 5

def should_fragment_be_assembled(sms, fragment):
    """
    Returns True if ``fragment`` can be assembled to ``sms``
    """
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

    print "MAL: Assembling fragment %s with sms %s" % (fragment, sms)
    return True

class CacheIncoherenceError(Exception):
    """Raised upon a cache incoherence error"""


class MessageAssemblyLayer(object):
    """
    I am a transparent layer to perform operations on concatenated SMS'
    """
    def __init__(self, wrappee):
        self.wrappee = wrappee
        self.last_index = 0
        self.sms_map = {}
        self.cached = False

    def initialize(self, obj=None, force=False):
        print "MAL::initialize  obj: %s  force: %s" % (obj, force)
        if obj is not None:
            self.wrappee = obj

        if force or not self.cached:
            # revert to initial state
            self.last_index = 0
            self.sms_map = {}
            # populate sms cache
            self.list_sms()

    def _do_add_sms(self, sms, indexes=None):
        """
        Adds ``sms`` to the cache using ``indexes`` if defined

        It returns the logical index where it was stored
        """
        print "MAL::_do_add_sms", sms, indexes
        # save the real index if indexes is None
        sms.real_indexes = [sms.index] if indexes is None else indexes
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
        print "MAL::_add_sms", sms
        if not sms.cnt:
            index = self._do_add_sms(sms)
            print "MAL::_add_sms  single part SMS added with logical index", index
            # being a single part sms, completed == True
            if emit:
                self.wrappee.emit_signal(SIG_SMS, index, True)
                self.wrappee.emit_signal(SIG_SMS_COMP, index, True)
            return index
        else:
            for index, value in self.sms_map.iteritems():
                if should_fragment_be_assembled(value, sms):
                    # append the sms and emit the different signals
                    completed = self.sms_map[index].append_sms(sms)
                    print "MAL::_add_sms  multi part SMS with logical index %d, completed %s" % (index, completed)

                    if emit:
                        # only emit signals in runtime, not startup
                        emit_signal = self.wrappee.emit_signal
                        emit_signal(SIG_SMS, index, completed)
                        if completed:
                            emit_signal(SIG_SMS_COMP, index, completed)

                    # return sms logical index
                    return index

            # this is the first fragment of this multipart sms, add it
            # to cache, emit signal and wait for the rest of fragments
            # to arrive. It returns the logical index where was stored
            index = self._do_add_sms(sms)
            self.wrappee.emit_signal(SIG_SMS, index, False)
            print "MAL::_add_sms first part of a multi part SMS added with logical index %d" % index
            return index

    def delete_sms(self, index):
        """Deletes sms identified by ``index``"""
        print "MAL::delete_sms", index
        if index in self.sms_map:
            sms = self.sms_map.pop(index)
            ret = map(self.wrappee.do_delete_sms, sms.real_indexes)
            print "MAL::delete_sms deleting %s" % sms.real_indexes
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
        print "MAL::list_sms"
        def gen_cache(messages):
            print "MAL::list_sms::gen_cache"
            for sms in messages:
                self._add_sms(sms)

            self.cached = True
            return [sms.to_dict() for sms in self.sms_map.values()]

        if self.cached:
            print "MAL::list_sms::cached path"
            return succeed([sms.to_dict() for sms in self.sms_map.values()])

        d = self.wrappee.do_list_sms()
        d.addCallback(gen_cache)
        return d

    def save_sms(self, sms):
        """Saves ``sms`` in the cache memoizing the resulting indexes"""
        print "MAL::save_sms", sms
        d = self.wrappee.do_save_sms(sms)
        d.addCallback(lambda indexes: self._do_add_sms(sms, indexes))
        d.addCallback(lambda ret: [ret])
        return d

    def on_sms_notification(self, index):
        """Executed when a SMS notification is received"""
        print "MAL::on_sms_notification", index
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
        import pprint, StringIO
        out = StringIO.StringIO()
        props = {'number' : self.number,
                 'index' : self.index,
                 'real_indexes' : self.real_indexes,
                 'csca' : self.csca,
                 'datetime' : self.datetime,
                 'reference' : self.ref,
                 'count' : self.cnt,
                 'sequence' : self.seq,
                 'completed' : self.completed,
                 'fragments' : self._fragments}

        pp = pprint.PrettyPrinter(indent=4, stream=out)
        pp.pprint(props)
        return out.getvalue()

    def __eq__(self, m):
        if IMessage.providedBy(m):
            return self.number == m.number and self.text == m.text

        return False

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
        m = cls(d['number'], d['text'])
        if 'index' in d:
            m.index = d['index']
        if 'where' in d:
            m.where = d['where']
        if 'smsc' in d:
            m.csca = d['smsc']
        if 'timestamp' in d:
            m.datetime = datetime.fromtimestamp(d['timestamp'], tz)

        return m

    @classmethod
    def from_pdu(cls, pdu):
        """
        Converts ``pdu`` to a :class:`Message` object

        :param pdu: The PDU to convert
        :rtype: ``Message``
        """
        print "Message::from_pdu", pdu
        p = PDU()
        sender, datestr, text, csca, ref, cnt, seq = p.decode_pdu(pdu)[:7]

        _datetime = None
        if datestr:
            try:
                _datetime = extract_datetime(datestr)
            except ValueError:
                _datetime = datetime.now()

        m = cls(sender, _datetime=_datetime, csca=csca, ref=ref, cnt=cnt, seq=seq)
        print "Message::from_pdu inserting fragment '%s' in pos %d" % (text, seq)
        m.add_text_fragment(text, seq)
        print "Message::from_pdu returning", m
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

        return ret

    def to_pdu(self, store=False):
        """Returns the PDU representation of this message"""
        p = PDU()
        csca = self.csca if self.csca is not None else ""

        return p.encode_pdu(self.number, self.text, csca=csca, store=store)

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

