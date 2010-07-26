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
"""MMS related classes and functions"""

from cStringIO import StringIO
from pprint import pformat

from twisted.internet import reactor
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implements


class BinaryDataProducer(object):
    implements(IBodyProducer)

    def __init__(self, data):
        self.data = data
        self.length = len(data)

    def startProducing(self, consumer):
        consumer.write(self.data)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class BinaryDataProtocol(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.received = StringIO()

    def dataReceived(self, data):
        self.received.write(data)

    def connectionLost(self, reason):
        print 'Finished receiving body:', reason.getErrorMessage()
        self.finished.callback(self.received.getvalue())
        self.received.close()


def callback_request(response):
    print 'Response version:', response.version
    print 'Response code:', response.code
    print 'Response phrase:', response.phrase
    print 'Response headers:'
    print pformat(list(response.headers.getAllRawHeaders()))
    finished = Deferred()
    response.deliverBody(BinaryDataProtocol(finished))
    return finished


def get_payload(uri, headers=None):
    if headers is None:
        headers = Headers({'User-Agent': ['Twisted Web Client']})
    else:
        headers = Headers(headers)

    agent = Agent(reactor)
    d = agent.request('GET', uri, headers, None)
    d.addCallback(callback_request)
    return d


def post_payload(uri, data, headers=None):
    if headers is None:
        headers = Headers({'User-Agent': ['Twisted Web Client']})
    else:
        headers = Headers(headers)

    agent = Agent(reactor)
    body = BinaryDataProducer(data)
    return agent.request('POST', uri, headers, body)
