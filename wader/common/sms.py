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
from messaging import PDU

from wader.common.interfaces import IMessage

STO_INBOX, STO_DRAFTS, STO_SENT = 1, 2, 3

class Message(object):
    """I am a Message in the system"""
    implements(IMessage)

    def __init__(self, number, text, index=None, where=None,
                 csca=None, _datetime=None):
        self.number = number
        self.text = text
        self.index = index
        self.where = where
        self.csca = csca
        self.datetime = _datetime
        self.ref = None
        self.cnt = None
        self.seq = None

    def __repr__(self):
        return "<Message  number: %s, text: %s>" % (self.number, self.text)

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

def pdu_to_message(pdu):
    """
    Converts ``pdu`` to a :class:`~wader.common.sms.Message` object

    :param pdu: The PDU to convert
    :rtype: ``Message``
    """
    p = PDU()
    sender, datestr, text, csca, ref, cnt, seq = p.decode_pdu(pdu)[:7]
    if datestr:
        try:
            _datetime = extract_datetime(datestr)
        except ValueError:
            _datetime = datetime.now()
    else:
        _datetime = None

    m = Message(sender, text, _datetime=_datetime, csca=csca)
    m.ref, m.cnt, m.seq = ref, cnt, seq

    return m

def message_to_pdu(sms, store=False):
    """Converts ``sms`` to its PDU representation"""
    p = PDU()
    csca = ""
    if sms.csca:
        csca = sms.csca

    return p.encode_pdu(sms.number, sms.text, csca=csca, store=store)

