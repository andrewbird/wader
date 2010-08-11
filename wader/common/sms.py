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
"""Sms-related classes"""

from datetime import datetime
from operator import itemgetter
from time import mktime

from zope.interface import implements

from messaging.sms import SmsSubmit, SmsDeliver
from wader.common.interfaces import IMessage
from wader.common.utils import get_tz_aware_now


class Message(object):
    """I am a Message in the system"""

    implements(IMessage)

    def __init__(self, number=None, text=None, index=None, where=None,
                 fmt=None, csca=None, _datetime=None, ref=None, cnt=None,
                 seq=None):
        self.number = number
        self.index = index
        self.real_indexes = set()
        self.where = where
        self.csca = csca
        self.datetime = _datetime
        self.fmt = fmt
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
        m.fmt = d.get('fmt')
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

        return m

    @classmethod
    def from_pdu(cls, pdu):
        """
        Converts ``pdu`` to a :class:`Message` object

        :param pdu: The PDU to convert
        :rtype: ``Message``
        """
        ret = SmsDeliver(pdu).data

        if 'date' not in ret:
            # XXX: Should we really fake a date?
            ret['date'] = get_tz_aware_now()

        m = cls(ret['number'], _datetime=ret['date'], csca=ret['csca'],
                ref=ret.get('ref'), cnt=ret.get('cnt'), seq=ret.get('seq', 0),
                fmt=ret.get('fmt'))
        m.type = ret.get('type')
        m.add_text_fragment(ret['text'], ret.get('seq', 0))

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
        sms = SmsSubmit(self.number, self.text)

        sms.csca = self.csca
        sms.status_request = self.status_request

        if store:
            sms.validity = None

        return sms.to_pdu()

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
            self.real_indexes.add(sms.index)
            self.completed = len(self._fragments) == sms.cnt
            return self.completed
        else:
            error = "Cannot assembly SMS fragment with ref %d"
            raise ValueError(error % sms.ref)

    def is_status_report(self):
        if self.type is None:
            return False

        return bool(self.type & 0x03)
