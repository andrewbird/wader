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
"""AT Commands related classes and help functions"""

import re

from twisted.internet import defer

from wader.common.aterrors import ERROR_REGEXP

OK_REGEXP = re.compile("\r\n(?P<resp>OK)\r\n")


def build_cmd_dict(extract=OK_REGEXP, end=OK_REGEXP, error=ERROR_REGEXP):
    """Returns a dictionary ready to be used in `CMD_DICT`"""
    for regexp in [extract, end, error]:
        if isinstance(regexp, basestring):
            regexp = re.compile(regexp)
        if hasattr(regexp, 'search'):
            pass
        else:
            raise ValueError("Don't know what to do with %r" % regexp)

    return dict(extract=extract, end=end, error=error)


def get_cmd_dict_copy():
    """
    Returns a copy of the `CMD_DICT` dictionary

    Use this instead of importing it directly as you may forget to copy() it
    """
    return CMD_DICT.copy()


CMD_DICT = {

    'add_contact' : build_cmd_dict(),

    'change_pin' : build_cmd_dict(),

    'check_pin' : build_cmd_dict(re.compile(r"""
                                         \r\n
                                         \+CPIN:\s
                                         (?P<resp>
                                            READY      |
                                            SIM\sPIN2? |
                                            SIM\sPUK2?
                                         )
                                         \r\n""", re.X)),

    'delete_contact' : build_cmd_dict(),

    'delete_sms' : build_cmd_dict(),

    'disable_echo' : build_cmd_dict(),

    'enable_echo' : build_cmd_dict(),

    'enable_radio' : build_cmd_dict(),

    'enable_pin' : build_cmd_dict(),

    'find_contacts' : build_cmd_dict(re.compile(r"""
                            \r\n
                            \+CPBF:\s
                            (?P<id>\d+),
                            "(?P<number>[+0-9a-fA-F]+)",
                            (?P<category>\d+),
                            \"(?P<name>.*)\"
                            """, re.X)),

    'get_apns' : build_cmd_dict(re.compile(r"""
                            \r\n
                            \+CGDCONT:\s
                            (?P<index>\d),
                            "[A-Za-z0-9]*",
                            "(?P<apn>.*)",
                            "(?P<ip>.*)",
                            \d,\d""", re.X)),

    'get_charsets': build_cmd_dict(re.compile('"(?P<lang>.*?)",?')),

    'get_contact' : build_cmd_dict(re.compile(r"""
                            \r\n
                            \+CPBR:\s(?P<id>\d+),
                            "(?P<number>[+0-9a-fA-F]+)",
                            (?P<cat>\d+),
                            "(?P<name>.*)"
                            \r\n""", re.X)),

    'list_contacts' : build_cmd_dict(
                        end=re.compile('(\r\n)?\r\n(OK)\r\n'),
                        extract=re.compile(r"""
                            \r\n
                            \+CPBR:\s(?P<id>\d+),
                            "(?P<number>[+0-9a-fA-F]+)",
                            (?P<cat>\d+),
                            "(?P<name>.*)"
                            """, re.X)),

    'get_card_version' : build_cmd_dict(re.compile(
                              '\r\n(\+C?GMR:)?(?P<version>.*)\r\n\r\nOK\r\n')),

    'get_card_model' : build_cmd_dict(re.compile(
                              '\r\n(?P<model>.*)\r\n\r\nOK\r\n')),

    'get_charset': build_cmd_dict(re.compile(
                              '\r\n\+CSCS:\s"(?P<lang>.*)"\r\n')),

    'get_esn': build_cmd_dict(re.compile('\r\n\+ESN:\s"(?P<esn>.*)"\r\n')),

    'get_manufacturer_name': build_cmd_dict(re.compile(
                              '\r\n(?P<name>.*)\r\n\r\nOK\r\n')),

    'get_imei' : build_cmd_dict(re.compile("\r\n(?P<imei>\d+)\r\n")),

    'get_imsi' : build_cmd_dict(re.compile('\r\n(?P<imsi>\d+)\r\n')),

    'get_netreg_status' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CREG:\s
                              (?P<mode>\d),(?P<status>\d+)
                              \r\n
                              """, re.X)),

    'get_network_info' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+COPS:\s+
                              (\d,\d,     # or followed by num,num,str,num
                              "(?P<netname>[^"]*)",
                              (?P<status>\d)
                              |(?P<error>\d)
                              )           # end of group
                              \r\n""", re.X)),

    'get_network_names' : build_cmd_dict(re.compile(r"""
                              \(
                              (?P<id>\d+),
                              "(?P<lname>[^"]*)",
                              "(?P<sname>[^"]*)",
                              "(?P<netid>\d+)",
                              (?P<type>\d)
                              \),?""", re.X),
                              end=re.compile('\r\n\r\nOK\r\n')),

    'get_signal_quality' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CSQ:\s(?P<rssi>\d+),(?P<ber>\d+)
                              \r\n""", re.X)),

    'get_sms_format' : build_cmd_dict(
                              re.compile('\r\n\+CMGF:\s(?P<format>\d)\r\n')),

    'get_phonebook_size' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CPBR:\s
                              \(\d\-(?P<size>\d+)\),\d+,\d+
                              \r\n""", re.X)),

    'get_pin_status' : build_cmd_dict(
                              re.compile('\r\n\+CLCK:\s(?P<status>\d)\r\n')),

    'get_radio_status' : build_cmd_dict(
                              re.compile("\r\n\+CFUN:\s?(?P<status>\d)\r\n")),

    'get_roaming_ids' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CPOL:\s(?P<index>\d+),
                              (?P<type>\d),
                              "(?P<netid>\d+)"
                              """, re.X)),

    'list_sms' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CMGL:\s
                              (?P<id>\d+),
                              (?P<where>\d),,\d+
                              \r\n(?P<pdu>\w+)""", re.X)),

    'get_sms' : build_cmd_dict(re.compile(r"""
                              \r\n
                              \+CMGR:\s
                              (?P<where>\d),,
                              \d+\r\n
                              (?P<pdu>\w+)
                              \r\n""", re.X)),

    'get_smsc' : build_cmd_dict(re.compile(
                              '\r\n\+CSCA:\s"(?P<smsc>.*)",\d+\r\n')),

    'register_with_netid' : build_cmd_dict(),

    'reset_settings' : build_cmd_dict(),

    'save_sms' : build_cmd_dict(re.compile('\r\n\+CMGW:\s(?P<index>\d+)\r\n')),

    'send_at' : build_cmd_dict(),

    'send_sms' : build_cmd_dict(re.compile(
                              '\r\n\+CMGS:\s(?P<index>\d+)\r\n')),

    'send_sms_from_storage' : build_cmd_dict(re.compile(
                              '\r\n\+CMSS:\s(?P<index>\d+)\r\n')),

    'send_pin' : build_cmd_dict(),

    'send_puk' : build_cmd_dict(),

    'set_apn' : build_cmd_dict(),

    'set_charset' : build_cmd_dict(),

    'set_netreg_notification' : build_cmd_dict(),

    'set_network_info_format' : build_cmd_dict(),

    'set_sms_indication' : build_cmd_dict(),

    'set_sms_format' : build_cmd_dict(),

    'set_smsc' : build_cmd_dict(),
}


class ATCmd(object):
    """I encapsulate all the data related to an AT command"""

    def __init__(self, cmd, name=None, eol='\r\n'):
        self.cmd = cmd
        self.name = name
        self.eol = eol
        # Some commands like sending a sms require an special handling this
        # is because we have to wait till we receive a prompt like '\r\n> '
        # if splitcmd is set, the second part will be send 0.1 seconds later
        self.splitcmd = None
        # command's deferred
        self.deferred = defer.Deferred()
        self.timeout = 15  # default timeout
        self.call_id = None # DelayedCall reference

    def __repr__(self):
        args = (self.name, self.get_cmd(), self.timeout)
        return "<ATCmd name: %s raw: %r timeout: %d>" % args

    def get_cmd(self):
        """Returns the raw AT command plus EOL"""
        cmd = self.cmd + self.eol
        return str(cmd)
