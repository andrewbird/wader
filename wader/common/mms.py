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

from array import array
from cStringIO import StringIO
import socket

from twisted.internet import threads

from messaging.mms.message import MMSMessage, DataPart


def mms_to_dbus_data(mms):
    import dbus
    """Converts ``mms`` to a tuple ready to be sent via DBus"""

    headers = {}
    data_parts = []
    # Convert headers
    for key, val in mms.headers.items():
        if key == 'Content-Type':
            headers[key] = val[0]
        else:
            headers[key] = val

    del headers['Date']

    # Set up data
    for data_part in mms.data_parts:
        part = {'Content-Type': data_part.content_type,
                'data': dbus.ByteArray(data_part.data)}
        if data_part.headers['Content-Type'][1]:
            part['parameters'] = data_part.headers['Content-Type'][1]

        data_parts.append(part)

    return headers, data_parts


def dbus_data_to_mms(headers, data_parts):
    """Returns a `MMSMessage` out of ``dbus_data``"""
    mms = MMSMessage()
    content_type = ''

    for key, val in headers:
        if key == 'Content-Type':
            content_type = val
        else:
            mms.headers[key] = val

    mms.content_type = content_type

    # add data parts
    for data_part in data_parts:
        content_type = data_part['Content-Type']
        data = array("B", data_part['data'])
        parameters = data_part.get('parameters', {})

        dp = DataPart()
        dp.set_data(data, content_type, parameters)
        # XXX: MMS message with no SMIL support

        # Content-Type: application/vnd.wap.multipart.mixed
        mms.add_data_part(dp)

    return mms


def do_get_payload(url, extra_info):
    host, port = extra_info['wap2'].split(':')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, int(port)))
    s.send("GET %s HTTP/1.0\r\n\r\n" % url)

    buf = StringIO()

    while True:
        data = s.recv(4096)
        if not data:
            break

        buf.write(data)

    s.close()
    _, data = buf.getvalue().split('\r\n\r\n')
    buf.close()
    return array("B", data)


def get_payload(uri, extra_info):
    """
    Downloads ``uri`` and returns a `MMSMessage` from it

    :param extra_info: dict with connection information
    """
    d = threads.deferToThread(do_get_payload, uri, extra_info)
    d.addCallback(MMSMessage.from_data)
    return d


def do_post_payload(extra_info, payload):
    host, port = extra_info['wap2'].split(':')
    mmsc = extra_info['mmsc']

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, int(port)))
    s.send("POST %s HTTP/1.0\r\n\r\n" % mmsc)
    s.send("Content-type: application/vnd.wap.mms-message\r\n")
    s.send("Content-Length: %d\r\n" % len(payload))
    s.send("\r\n")

    s.sendall(payload)

    buf = StringIO()

    while True:
        data = s.recv(4096)
        if not data:
            break

        buf.write(data)

    s.close()
    _, data = buf.getvalue().split('\r\n\r\n')
    buf.close()
    return array("B", data)


def post_payload(extra_info, data):
    d = threads.deferToThread(do_post_payload, extra_info, data)
    d.addCallback(MMSMessage.from_data)
    return d


def send_m_notifyresp_ind(extra_info, tx_id):
    mms = MMSMessage()
    mms.headers['Transaction-Id'] = tx_id
    mms.headers['Message-Type'] = 'm-notifyresp-ind'
    mms.headers['Status'] = 'Retrieved'

    return post_payload(extra_info, mms.encode())


def send_m_send_req(extra_info, dbus_data):
    # sanitize headers
    headers = dbus_data['headers']
    if 'To' not in headers:
        raise ValueError("You need to provide a recipient 'To'")

    if not headers['To'].endswith('/TYPE=PLMN'):
        headers['To'] += '/TYPE=PLMN'

    # set headers
    mms = dbus_data_to_mms(dbus_data)
    for key, val in headers.items():
        mms.headers[key] = val

    # set type the last one so is always the right type
    mms.headers['Message-Type'] = 'm-send-req'

    d = post_payload(extra_info, mms.encode())
    d.addCallback(MMSMessage.from_data)
    return d
