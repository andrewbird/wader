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
from time import mktime

from zope.interface import implements
from twisted.internet.defer import  succeed, gatherResults
from messaging import PDU

from wader.common.interfaces import IMessage

STO_INBOX, STO_DRAFTS, STO_SENT = 1, 2, 3

class CacheIncoherenceError(Exception):
    """Raised when a cache incoherence error happens"""


class MessageAssemblyLayer(object):
    """
    I am a transparent layer to perform operations on concatenated SMS
    """

    def __init__(self, wrappee):
        self.wrappee = wrappee
        self.last_index = 0
        self.sms_map = {}
        self.cached = False
        self.list_sms()

    def _do_add_sms(self, sms, indexes=None):
        """
        Adds ``sms`` to the cache using ``indexes`` if defined

        It returns the logical index where it was stored
        """
        if indexes is None:
            # save the real index
            sms.real_indexes = [sms.index]
        else:
            sms.real_indexes = indexes

        # assign a new logical index
        self.last_index += 1
        sms.index = self.last_index
        # reference the sms by this logical index
        self.sms_map[self.last_index] = sms
        return self.last_index

    def _add_sms(self, sms):
        """
        Adds ``sms`` to the cache

        It returns the logical index where it was stored
        """
        if sms.cnt == 0:
            return self._do_add_sms(sms)
        else:
            for index, value in self.sms_map.iteritems():
                if value.ref == sms.ref:
                    self.sms_map[index].append_sms(sms)
                    return index

            return self._do_add_sms(sms)

    def delete_sms(self, index):
        """Deletes sms identified by ``index``"""
        if index in self.sms_map:
            sms = self.sms_map[index]
            ret = [self.wrappee.delete_sms(i) for i in sms.real_indexes]
            del self.sms_map[index]
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
        res = []

        def gen_cache(messages):
            self.cached = True
            for sms in messages:
                self._add_sms(sms)
            for sms in self.sms_map.values():
                res.append(sms.to_dict())
            return res

        if self.cached:
            for sms in self.sms_map.values():
                res.append(sms.to_dict())
            return succeed(res)

        d = self.wrappee.list_sms()
        d.addCallback(gen_cache)
        return d

    def save_sms(self, sms):
        """Saves ``sms`` in the cache memoizing the resulting indexes"""
        def do_save_sms(indexes):
            result = (self._do_add_sms(sms, indexes),)
            return result

        d = self.wrappee.save_sms(sms)
        d.addCallback(do_save_sms)
        return d


class Message(object):
    """I am a Message in the system"""
    implements(IMessage)

    def __init__(self, number, text, index=None, where=None,
                 csca=None, _datetime=None):
        self.number = number
        self.text = text
        self.index = index
        self.real_indexes = []
        self.where = where
        self.csca = csca
        self.datetime = _datetime
        self.ref = None  # Multipart SMS reference number
        self.cnt = None  # Total number of parts
        self.seq = None  # Part #

    def __repr__(self):
        return "<Message number: %s, text: %s>" % (self.number, self.text)

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
        p = PDU()
        sender, datestr, text, csca, ref, cnt, seq = p.decode_pdu(pdu)[:7]

        _datetime = None
        if datestr:
            try:
                _datetime = extract_datetime(datestr)
            except ValueError:
                _datetime = datetime.now()

        m = cls(sender, text, _datetime=_datetime, csca=csca)
        m.ref, m.cnt, m.seq = ref, cnt, seq

        return m

    def to_dict(self):
        """
        Returns a dict ready to be sent via DBus

        :rtype: dict
        """
        ret = {}

        ret['number'] = self.number
        ret['text'] = self.text
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
        csca = ""
        if self.csca:
            csca = self.csca

        return p.encode_pdu(self.number, self.text, csca=csca, store=store)

    def append_sms(self, sms):
        """Appends ``sms`` text internally"""
        if self.ref == sms.ref:
            if sms.seq < self.seq:
                self.text = sms.text + self.text
            else:
                self.text += sms.text

            self.real_indexes.extend(sms.real_indexes)
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

    from wader.common.oal import osobj
    tz = osobj.get_tzinfo()

    return datetime(year, month, day, hour, mins, seconds, tzinfo=tz)

