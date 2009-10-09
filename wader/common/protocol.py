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
"""Twisted protocols for serial communication"""

import re

from twisted.internet import protocol, defer, reactor
from twisted.python.failure import Failure
from twisted.python import log

import wader.common.aterrors as E
from wader.common.command import ATCmd
import wader.common.signals as S

# Standard unsolicited notifications
CALL_RECV = re.compile('\r\nRING\r\n')
STK_DEBUG = re.compile('\r\n\+STC:\s\d+\r\n')
# Standard solicited notifications
NEW_SMS = re.compile('\r\n\+CMTI:\s"(?P<where>\w{2,})",(?P<id>\d+)\r\n')
SPLIT_PROMPT = re.compile('^\r\n>\s$')
CREG_REGEXP = re.compile('\r\n\+CREG:\s*(?P<status>\d)\r\n')


class BufferingStateMachine(object, protocol.Protocol):
    """A simple SM that handles low level communication with the device"""

    def __init__(self, device):
        super(BufferingStateMachine, self).__init__()
        self.device = device
        # a reference to the customizer class for notifications
        self.custom = device.custom
        # current AT command
        self.cmd = None
        self.state = 'idle'
        # idle and wait buffers
        self.idlebuf = ""
        self.waitbuf = ""
        # log prefix for situations where the prefix is not appended
        self._prefix = ""

    def _get_log_prefix(self):
        try:
            if not self._prefix:
                if self.device.ports.has_two():
                    self._prefix = self.device.ports.cport.obj.logPrefix()
                else:
                    self._prefix = self.device.ports.dport.obj.logPrefix()
        except AttributeError:
            self._prefix = ''

        return self._prefix

    def _timeout_eb(self):
        """Executed when a command exceeds its timeout"""
        msg = "Command '%r' timed out, this is my waitbuf: %s"
        e = E.SerialResponseTimeout(msg % (self.cmd, self.waitbuf))
        self.notify_failure(e)
        self.transition_to_idle()

    def cancel_current_delayed_call(self):
        """
        Cancels current :class:`~wader.common.command.ATCmd` delayed call
        """
        if self.cmd.call_id and self.cmd.call_id.active():
            self.cmd.call_id.cancel()

    def notify_success(self, result):
        """
        Notify success to current :class:`~wader.common.command.ATCmd`
        """
        self.cancel_current_delayed_call()
        try:
            self.cmd.deferred.callback(result)
        except Exception, e:
            args = (self.cmd, result)
            log.err(e, "'%r' callback failed with args '%s'" % args)

    def notify_failure(self, failure):
        """Notify failure to current :class:`~wader.common.command.ATCmd`"""
        self.cancel_current_delayed_call()
        self.cmd.deferred.errback(failure)

    def set_cmd(self, cmd):
        """
        Sets ``cmd`` as the next command to process

        It also sets an initial timeout and transitions to waiting state
        """
        self.cmd = cmd
        # set the timeout for this command
        self.cmd.call_id = reactor.callLater(cmd.timeout, self._timeout_eb)
        self.set_state('waiting')

    def set_state(self, new_state):
        """Sets the new state ``new_state``"""
        log.msg("state change: %s -> %s" % (self.state, new_state),
                system=self._get_log_prefix())
        # the system line got added because no suffix was being added
        # to the log in set_state
        self.state = new_state

    def transition_to_idle(self):
        """Transitions to idle state and cleans internal buffers"""
        self.cmd = None
        self.set_state('idle')
        self.idlebuf = ""
        self.waitbuf = ""

    def send_splitcmd(self):
        """
        Used to send the second part of a split command after prompt appears
        """
        raise NotImplementedError()

    def emit_signal(self, signal, *args, **kwds):
        """
        Emits ``signal``

        :param signal: The name of the signal to emit
        :param args: The arguments for the signal ``signal``
        :param kwds: The keywords for the signal ``signal``
        """
        method = getattr(self.device.exporter, signal, None)
        if method:
            method(*args, **kwds)
        else:
            log.err("No method registered for signal %s" % signal)

    def dataReceived(self, data):
        """See `twisted.internet.protocol.Protocol.dataReceived`"""
        state = 'handle_%s' % self.state
        getattr(self, state)(data)

    def process_notifications(self, _buffer):
        """
        Processes unsolicited notifications in ``_buffer``

        :param _buffer: Buffer to scan
        """
        if not self.device.custom or not self.device.custom.async_regexp:
            return _buffer

        custom = self.device.custom
        # we have to use re.finditer as some cards like to pipeline
        # several asynchronous notifications in one
        for match in re.finditer(custom.async_regexp, _buffer):
            name, value = match.groups()
            if name in custom.signal_translations:
                # we obtain the signal name and the associated function
                # that will translate the device unsolicited message to
                # the signal used in Wader internally
                signal, func = custom.signal_translations[name]

                # if we have a transform function defined, then use it
                # otherwise use value as args
                if func:
                    try:
                        args = func(value)
                    except Exception, e:
                        msg = "%s can not handle notification %s"
                        log.err(e, msg % (func, value))
                        args = value

                    self.emit_signal(signal, args)

                # remove from the idlebuf the match (but only once please)
                _buffer = _buffer.replace(match.group(), '', 1)

        return _buffer

    def handle_idle(self, data):
        """
        Processes ``data`` in `idle` state

        Being in `idle` state, there are six possible events that must be
        handled:

        - STK init garbage
        - Call received (we're not handling it in waiting)
        - A SMS arrived
        - SMS notification (Not handled yet)
        - Device's own unsolicited notifications
        - Default: i.e. this device originated a notification that we don't
          understand yet, the point is to log it and make it visible so the
          user can report it to us
        """
        log.msg("idle: %r" % data)
        self.idlebuf += data

        # most possible event:
        # device's own unsolicited notifications
        # signal translations stuff
        self.idlebuf = self.process_notifications(self.idlebuf)
        if not self.idlebuf:
            return

        # second most possible event:
        # new SMS arrived
        match = NEW_SMS.match(self.idlebuf)
        if match:
            mal = getattr(self, 'mal', None)
            if mal:
                index = int(match.group('id'))
                mal.on_sms_notification(index)

            self.idlebuf = self.idlebuf.replace(match.group(), '', 1)
            if not self.idlebuf:
                return

        # third most possible event
        match = STK_DEBUG.match(self.idlebuf)
        if match:
            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        # fourth most possible event
        match = CREG_REGEXP.match(self.idlebuf)
        if match:
            status = int(match.group('status'))
            self.emit_signal(S.SIG_CREG, status)
            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        # fifth most possible event:
        match = CALL_RECV.match(self.idlebuf)
        if match:
            self.emit_signal(S.SIG_CALL)

            self.idlebuf = self.idlebuf.replace(match.group(), '')
            if not self.idlebuf:
                return

        log.msg("idle: unmatched data %r" % self.idlebuf)

    def handle_waiting(self, data):
        """Process ``data`` in the wait state"""
        self.waitbuf += data
        self.waitbuf = self.process_notifications(self.waitbuf)
        if not self.waitbuf:
            return

        try:
            cmdinfo = self.custom.cmd_dict[self.cmd.name]
        except KeyError, e:
            log.err(e, 'command %s not present in my cmd dict' % self.cmd)
            return self.transition_to_idle()

        match = cmdinfo['end'].search(self.waitbuf)
        if match: # end of response
            if cmdinfo['extract']:
                # There's an regex to extract info from data
                response = list(re.finditer(cmdinfo['extract'], self.waitbuf))
                resp_repr = str([m.groups() for m in response])
                log.msg("%s: callback = %s" % (self.state, resp_repr))
                self.notify_success(response)

                # now clean self.waitbuf
                for _m in response:
                    self.waitbuf = self.waitbuf.replace(_m.group(), '', 1)
                # now clean end of command
                endmatch = cmdinfo['end'].search(self.waitbuf)
                if endmatch:
                    self.waitbuf = self.waitbuf.replace(endmatch.group(),
                                                        '', 1)
            else:
                # there's no regex in cmdinfo to extract info
                log.msg("%s: no callback registered" % self.state)
                self.notify_success(self.waitbuf)
                self.waitbuf = self.waitbuf.replace(match.group(), '', 1)

            self.transition_to_idle()
        else:
            # there is no end of response detected, so we have either an error
            # or a split command (like send_sms, save_sms, etc.)
            match = E.extract_error(self.waitbuf)
            if match:
                exception, error, m = match
                e = exception(error)
                log.err(e, "waiting")
                # send the failure back
                self.notify_failure(Failure(e))
                # remove the exception string from the waitbuf
                self.waitbuf = self.waitbuf.replace(m.group(), '', 1)
                self.transition_to_idle()
            else:
                match = SPLIT_PROMPT.match(data)
                if match:
                    log.msg("waiting: split command prompt detected")
                    self.send_splitcmd()
                    self.waitbuf = self.waitbuf.replace(match.group(), '', 1)
                else:
                    log.msg("waiting: unmatched data %r" % data)



class SerialProtocol(BufferingStateMachine):
    """
    I define the protocol used to communicate with the SIM card

    SerialProtocol communicates with the SIM synchronously, only one command
    at a time. However, SerialProtocol offers an asynchronous interface
    :meth:`SerialProtocol.queue_at_cmd` which accepts and queues an
    :class:`~wader.common.command.ATCmd` and returns a
    :class:`~twisted.internet.defer.Deferred` that will be callbacked with
    the commands response, or errback if an exception is
    raised.

    SerialProtocol actually is an specially tailored Finite State Machine.
    After several redesigns and simplifications, this FSM has just two states:

    - idle: sitting idle for user input or an unsolicited response, when a
      command is received we send the command and transition to the waiting
      state.
    - waiting: the FSM is buffering and parsing all the SIM's response to the
      command till it matches the regexp that signals the end of the command.
      If the command has an associated regexp to extract information, the
      buffered response will be parsed and the command's deferred will be
      callbacked with the regexp as argument. There are commands that don't
      have an associated regexp to extract information as we are not
      interested in the "all went ok" response, only if an exception
      occurred -e.g. when deleting a contact we are only interested if
      something went wrong, not if all went ok.

    The transition to each state is driven by regular expressions, each
    command has associated a set of regular expressions that make the FSM
    change states. This regexps are defined in
    :obj:`wader.common.command.CMD_DICT` although the plugin mechanism
    offers the possibility of customizing the CMD_DICT through
    :class:`~wader.common.hardware.base.Customizer` if a card uses a
    different AT string than the rest for that particular command.
    """
    def __init__(self, device):
        super(SerialProtocol, self).__init__(device)
        self.queue = defer.DeferredQueue()
        self.mutex = defer.DeferredLock()
        self._check_queue()

    def transition_to_idle(self):
        """Transitions to idle state and processes next queued `ATCmd`"""
        super(SerialProtocol, self).transition_to_idle()
        # release the lock and check the queue
        self.mutex.release()
        self._check_queue()

    def send_splitcmd(self):
        """
        Used to send the second part of a split command after prompt appears
        """
        self.transport.write(self.cmd.splitcmd)

    def _process_at_cmd(self, cmd):
        def _transition_and_send(_):
            log.msg("%s: sending %r" % (self.state, cmd.cmd),
                    system=self._get_log_prefix())
            self.set_cmd(cmd)
            self.transport.write(cmd.get_cmd())

        d = self.mutex.acquire()
        d.addCallback(_transition_and_send)

    def _check_queue(self):
        # when the next element of the queue is put, _process_at_cmd will be
        # callbacked with it
        d = self.queue.get()
        d.addCallback(self._process_at_cmd)

    def queue_at_cmd(self, cmd):
        """
        Queues an :class:`~wader.common.command.ATCmd` ``cmd``

        This deferred will be callbacked with the command's response

        :rtype: `Deferred`
        """
        self.queue.put(cmd)
        return cmd.deferred


class WCDMAProtocol(SerialProtocol):
    """
    A Twisted protocol to chat with WCDMA devices

    I am able to speak with most WCDMA devices, if you want to customize
    the command being sent for a particular command, subclass me.
    """

    def __init__(self, device):
        super(WCDMAProtocol, self).__init__(device)

    def add_contact(self, name, number, index):
        """
        Adds a contact to the SIM card

        :param name: The contact name
        :param number: The contact number
        :param index: The contact index
        """
        category = 145 if number.startswith('+') else 129
        args = (index, number, category, name)
        cmd = ATCmd('AT+CPBW=%d,"%s",%d,"%s"' % args, name='add_contact')
        return self.queue_at_cmd(cmd)

    def change_pin(self, oldpin, newpin):
        """
        Changes ``oldpin`` to ``newpin`` in the SIM card

        :type oldpin: str
        :type newpin: str

        :raise GenericError: When the password is incorrect.
        :raise IncorrectPassword: When the password is incorrect.
        :raise InputValueError: When the PIN != \d{4}
        """
        atstr = 'AT+CPWD="SC","%s","%s"' % (str(oldpin), str(newpin))
        cmd = ATCmd(atstr, name='change_pin')
        return self.queue_at_cmd(cmd)

    def check_pin(self):
        """
        Checks what's necessary to authenticate against the SIM card

        :raise SimBusy: When the SIM is not ready
        :raise SimNotStarted: When the SIM is not ready
        :raise SimFailure: This exception is raised by Option's colt when
                           authentication is disabled
        :rtype: str
        """
        cmd = ATCmd('AT+CPIN?', name='check_pin')
        return self.queue_at_cmd(cmd)

    def delete_all_contacts(self):
        """Deletes all the contacts in SIM card, function useful for tests"""
        d = self.get_used_contact_ids()
        def list_contacts_ids_cb(used):
            if not used:
                return True

            return defer.gatherResults(map(self.delete_contact, used))

        d.addCallback(list_contacts_ids_cb)
        return d

    def delete_all_sms(self):
        """Deletes all the messages in SIM card, function useful for tests"""
        d = self.get_used_sms_ids()
        def delete_all_sms_cb(used):
            if not used:
                return True

            return defer.gatherResults(map(self.delete_sms, used))

        d.addCallback(delete_all_sms_cb)
        return d

    def delete_contact(self, index):
        """Deletes the contact specified by ``index``"""
        cmd = ATCmd('AT+CPBW=%d' % index, name='delete_contact')
        return self.queue_at_cmd(cmd)

    def delete_sms(self, index):
        """Deletes the message specified by ``index``"""
        cmd = ATCmd('AT+CMGD=%d' % index, name='delete_sms')
        return self.queue_at_cmd(cmd)

    def disable_echo(self):
        """Disables echo of AT cmds"""
        cmd = ATCmd('ATE0', name='disable_echo')
        return self.queue_at_cmd(cmd)

    def enable_echo(self):
        """Enables echo of AT cmds"""
        cmd = ATCmd('ATE1', name='enable_echo')
        return self.queue_at_cmd(cmd)

    def enable_pin(self, pin, enable):
        """
        Enables pin authentication at startup

        :type pin: int
        :type enable: bool

        :raise GenericError: If ``pin`` is incorrect.
        :raise IncorrectPassword: If ``pin`` is incorrect.
        :raise ValueError: When ``pin`` != \d{4}
        """
        at_str = 'AT+CLCK="SC",%d,"%s"' % (int(enable), str(pin))
        cmd = ATCmd(at_str, name='enable_pin')
        return self.queue_at_cmd(cmd)

    def enable_radio(self, enable):
        """
        Enables/disable radio stack
        """
        cmd = ATCmd("AT+CFUN=%d" % int(enable), name='enable_radio')
        cmd.timeout = 30
        return self.queue_at_cmd(cmd)

    def find_contacts(self, pattern):
        """Returns a list of contacts that match ``pattern``"""
        cmd = ATCmd('AT+CPBF="%s"' % pattern, name='find_contacts')
        return self.queue_at_cmd(cmd)

    def get_apns(self):
        """Returns all the APNs in the SIM"""
        cmd = ATCmd('AT+CGDCONT?', name='get_apns')
        return self.queue_at_cmd(cmd)

    def get_card_model(self):
        """Returns the SIM card model"""
        cmd = ATCmd('AT+CGMM', name='get_card_model')
        return self.queue_at_cmd(cmd)

    def get_card_version(self):
        """Returns the SIM card version"""
        cmd = ATCmd('AT+CGMR', name='get_card_version')
        return self.queue_at_cmd(cmd)

    def get_charset(self):
        """Returns the current character set name"""
        cmd = ATCmd('AT+CSCS?', name='get_charset')
        return self.queue_at_cmd(cmd)

    def get_charsets(self):
        """Returns the available charsets"""
        cmd = ATCmd('AT+CSCS=?', name='get_charsets')
        return self.queue_at_cmd(cmd)

    def get_contact(self, index):
        """Returns the contact at ``index``"""
        cmd = ATCmd('AT+CPBR=%d' % index, name='get_contact')
        return self.queue_at_cmd(cmd)

    def list_contacts(self):
        """
        Returns all the contacts stored in the SIM card

        :raise GenericError: When no contacts are found.
        :raise NotFound: When no contacts are found.
        :raise SimBusy: When the SIM is not ready.
        :raise SimNotStarted: When the SIM is not ready.

        :rtype: list
        """
        cmd = ATCmd('AT+CPBR=1,%d' % self.device.sim.size,
                    name='list_contacts')
        return self.queue_at_cmd(cmd)

    def get_imei(self):
        """Returns the IMEI number of the SIM card"""
        cmd = ATCmd('AT+CGSN', name='get_imei')
        return self.queue_at_cmd(cmd)

    def get_imsi(self):
        """Returns the IMSI number of the SIM card"""
        cmd = ATCmd('AT+CIMI', name='get_imsi')
        return self.queue_at_cmd(cmd)

    def get_manufacturer_name(self):
        """Returns the manufacturer name of the SIM card"""
        cmd = ATCmd('AT+GMI', name='get_manufacturer_name')
        return self.queue_at_cmd(cmd)

    def get_netreg_status(self):
        """Returns the network registration status"""
        cmd = ATCmd('AT+CREG?', name='get_netreg_status')
        return self.queue_at_cmd(cmd)

    def get_network_info(self):
        """Returns a tuple with the network info"""
        cmd = ATCmd('AT+COPS?', name='get_network_info')
        return self.queue_at_cmd(cmd)

    def get_network_names(self):
        """Returns a tuple with the network info"""
        cmd = ATCmd('AT+COPS=?', name='get_network_names')
        cmd.timeout = 40
        return self.queue_at_cmd(cmd)

    def get_phonebook_size(self):
        """
        Returns the phonebook size of the SIM card

        :raise GenericError: When the SIM is not ready.
        :raise SimBusy: When the SIM is not ready.
        :raise CMSError500: When the SIM is not ready.
        """
        cmd = ATCmd('AT+CPBR=?', name='get_phonebook_size')
        cmd.timeout = 15
        return self.queue_at_cmd(cmd)

    def get_pin_status(self):
        """Checks whether the pin is enabled or disabled"""
        cmd = ATCmd('AT+CLCK="SC",2', name='get_pin_status')
        return self.queue_at_cmd(cmd)

    def get_radio_status(self):
        """Returns whether the radio is enabled or disabled"""
        cmd = ATCmd("AT+CFUN?", name='get_radio_status')
        return self.queue_at_cmd(cmd)

    def get_roaming_ids(self):
        """Returns a list with the networks we can register with"""
        cmd = ATCmd('AT+CPOL?', name='get_roaming_ids')
        return self.queue_at_cmd(cmd)

    def get_signal_quality(self):
        """Returns a tuple with the RSSI and BER of the connection"""
        cmd = ATCmd('AT+CSQ', name='get_signal_quality')
        return self.queue_at_cmd(cmd)

    def list_sms(self):
        """
        Returns all the messages stored in the SIM card

        :raise GenericError: When no messages are found.
        :raise NotFound: When no messages are found.

        :rtype: list
        """
        cmd = ATCmd('AT+CMGL=4', name='list_sms')
        return self.queue_at_cmd(cmd)

    def get_sms(self, index):
        """Returns the message stored at ``index``"""
        cmd = ATCmd('AT+CMGR=%d' % index, name='get_sms')
        return self.queue_at_cmd(cmd)

    def get_sms_format(self):
        """Returns the message stored at ``index``"""
        cmd = ATCmd('AT+CMGF?', name='get_sms_format')
        return self.queue_at_cmd(cmd)

    def get_smsc(self):
        """Returns the SMSC stored in the SIM"""
        cmd = ATCmd('AT+CSCA?', name='get_smsc')
        return self.queue_at_cmd(cmd)

    def get_used_contact_ids(self):
        """Returns a list with the used contact ids"""
        def errback(failure):
            failure.trap(E.NotFound, E.GenericError)
            return []

        d = self.list_contacts()
        d.addCallback(lambda contacts: [int(c.group('id')) for c in contacts])
        d.addErrback(errback)
        return d

    def get_used_sms_ids(self):
        """Returns a list with used SMS ids in the SIM card"""
        d = self.list_sms()
        def errback(failure):
            failure.trap(E.NotFound, E.GenericError)
            return []

        d.addCallback(lambda smslist: [int(s.group('id')) for s in smslist])
        d.addErrback(errback)
        return d

    def register_with_netid(self, netid, mode=1, _format=2):
        """Registers with ``netid``"""
        atstr = 'AT+COPS=%d,%d,"%s"' % (mode, _format, netid)
        cmd = ATCmd(atstr, name='register_with_netid')
        cmd.timeout = 30
        return self.queue_at_cmd(cmd)

    def reset_settings(self):
        """Resets the settings to factory settings"""
        cmd = ATCmd('ATZ', name='reset_settings')
        return self.queue_at_cmd(cmd)

    def save_sms(self, pdu, pdu_len):
        """Returns the index where ``pdu`` was stored"""
        cmd = ATCmd('AT+CMGW=%s' % pdu_len, name='save_sms', eol='\r')
        cmd.splitcmd = '%s\x1a' % pdu
        return self.queue_at_cmd(cmd)

    def send_pin(self, pin):
        """
        Authenticates using ``pin``

        :raise GenericError: Exception raised by Nozomi when PIN is incorrect.
        :raise IncorrectPassword: Exception raised when the PIN is incorrect
        """
        cmd = ATCmd('AT+CPIN="%s"' % str(pin), name='send_pin')
        return self.queue_at_cmd(cmd)

    def send_puk(self, puk, pin):
        """
        Authenticates using ``puk`` and ``pin``

        :raise GenericError: Exception raised by Nozomi when PUK is incorrect.
        :raise IncorrectPassword: Exception raised when the PUK is incorrect
        """
        atstr = 'AT+CPIN="%s","%s"' % (str(puk), str(pin))
        cmd = ATCmd(atstr, name='send_puk')
        return self.queue_at_cmd(cmd)

    def send_sms(self, pdu, pdu_len):
        """Sends the given pdu and returns the index"""
        cmd = ATCmd('AT+CMGS=%d' % pdu_len, name='send_sms', eol='\r')
        cmd.splitcmd = '%s\x1a' % pdu
        return self.queue_at_cmd(cmd)

    def send_sms_from_storage(self, index):
        """Sends the SMS stored at ``index`` and returns the new index"""
        cmd = ATCmd('AT+CMSS=%d' % index, name='send_sms_from_storage')
        return self.queue_at_cmd(cmd)

    def set_apn(self, index, apn):
        """Sets the APN to ``apn`` using ``index``"""
        cmd = ATCmd('AT+CGDCONT=%d,"IP","%s"' % (index, apn), name='set_apn')
        return self.queue_at_cmd(cmd)

    def set_charset(self, charset):
        """Sets the character set used on the SIM"""
        cmd = ATCmd('AT+CSCS="%s"' % charset, name='set_charset')
        return self.queue_at_cmd(cmd)

    def set_netreg_notification(self, val=1):
        """Sets CREG unsolicited notification"""
        cmd = ATCmd('AT+CREG=%d' % val, name='set_netreg_notification')
        return self.queue_at_cmd(cmd)

    def set_network_info_format(self, mode=0, _format=2):
        """Sets the network information format for +COPS queries"""
        cmd = ATCmd('AT+COPS=%d,%d' % (mode, _format),
                    name='set_network_info_format')
        return self.queue_at_cmd(cmd)

    def set_sms_format(self, _format=0):
        """Sets the format of the SMS"""
        cmd = ATCmd('AT+CMGF=%d' % _format, name='set_sms_format')
        return self.queue_at_cmd(cmd)

    def set_sms_indication(self, mode=2, mt=1, bm=0, ds=0, bfr=0):
        """Sets the SMS indication mode"""
        args = 'AT+CNMI=' + ','.join(map(str, [mode, mt, bm, ds, bfr]))
        cmd = ATCmd(args, name='set_sms_indication')
        return self.queue_at_cmd(cmd)

    def set_smsc(self, number):
        """Sets the SMSC"""
        cmd = ATCmd('AT+CSCA="%s"' % number, name='set_smsc')
        return self.queue_at_cmd(cmd)

    def send_at(self, at_str, name='send_at'):
        """Send an arbitrary AT string to the SIM card"""
        cmd = ATCmd(at_str, name=name)
        return self.queue_at_cmd(cmd)

