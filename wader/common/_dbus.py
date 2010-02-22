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
"""DBus-related helper classes"""

import dbus
import dbus.service
from twisted.python import log


class DBusExporterHelper(object):
    """I am a helper for classes that export methods over DBus"""

    def __init__(self):
        super(DBusExporterHelper, self).__init__()

    def add_callbacks(self, deferred, async_cb, async_eb):
        """Adds ``async_cb`` and ``async_eb`` to ``deferred``"""
        deferred.addCallback(async_cb)
        deferred.addErrback(self._process_failure, async_eb)
        return deferred

    def add_callbacks_and_swallow(self, deferred, async_cb, async_eb):
        """
        Like previous method but swallows the result

        This method is useful for functions that might return some garbage,
        but we are not interested in the result
        """
        deferred.addCallback(lambda _: async_cb())
        deferred.addErrback(self._process_failure, async_eb)
        return deferred

    def _process_failure(self, failure, async_eb):
        """
        Extracts the exception wrapped in ``failure`` and calls ``async_eb``
        """
        try:
            async_eb(failure.type(failure.value))
        except:
            log.msg(dir(failure.type))
            log.msg(failure.value)


class DelayableDBusObject(dbus.service.Object):
    """Use me in classes that need to make asynchronous a synchronous method"""

    def __init__(self, *args):
        super(DelayableDBusObject, self).__init__(*args)

    def _message_cb(self, connection, message):
        method, parent_method = dbus.service._method_lookup(self,
                                                message.get_member(),
                                                message.get_interface())

        super(DelayableDBusObject, self)._message_cb(connection, message)

        if "_dbus_is_delayable" in dir(parent_method):
        #if hasattr(parent_method, '_dbus_is_delayable'):
            member = message.get_member()
            signature_str = parent_method._dbus_out_signature
            signature = dbus.service.Signature(signature_str)

            def callback(result):
                dbus.service._method_reply_return(connection,
                                                  message,
                                                  member,
                                                  signature,
                                                  *result)

            def errback(e):
                dbus.service._method_reply_error(connection, message, e)

            parent_method._finished(self, callback, errback)


def delayable(func):
    """
    Make a synchronous method asynchronous

    decorator to be used on subclasses of :class:`DelayableDBusObject`
    """
    assert func._dbus_is_method

    def delay_reply():
        func._dbus_async_callbacks_before = func._dbus_async_callbacks
        func._dbus_async_callbacks = True

    def finished(self, cb, eb):
        if func._dbus_async_callbacks == True:
            if not self in func._reply_callbacks:
                func._reply_callbacks[self] = []
            func._reply_callbacks[self].append((cb, eb))
            func._dbus_async_callbacks = func._dbus_async_callbacks_before

    def reply(self, result=None, error=None):
        if self in func._reply_callbacks:
            for callback, errback in func._reply_callbacks[self]:
                if error:
                    errback(error)
                elif result:
                    callback(result)
                else:
                    callback()
            del func._reply_callbacks[self]
            return True
        else:
            return False

    func._reply_callbacks = {}
    func._dbus_is_delayable = True

    func.delay_reply = delay_reply
    func.reply = reply
    func._finished = finished
    return func
