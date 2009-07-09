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
"""Contact related classes and utilities"""

from zope.interface import implements

from wader.common.encoding import to_u
from wader.common.interfaces import IContact

class Contact(object):
    """I am a Contact on Wader"""
    implements(IContact)

    def __init__(self, name, number, index=None):
        super(Contact, self).__init__()
        self.name = to_u(name)
        self.number = to_u(number)
        self.index = index

    def __repr__(self):
        if self.index:
            args = (self.index, self.name, self.number)
            return '<Contact index="%d" name="%s" number="%s">' % args

        return '<Contact name="%s" number="%s">' % (self.name, self.number)

    __str__ = __repr__

    def __eq__(self, c):
        if self.index is not None and c.index is not None:
            return self.index == c.index

        return self.name == c.name and self.number == c.number

    def __ne__(self, c):
        return not self.__eq__(c)

    def to_csv(self):
        """See :meth:`wader.common.interfaces.IContact.to_csv`"""
        name = '"%s"' % self.name
        number = '"%s"' % self.number
        return [name, number]

