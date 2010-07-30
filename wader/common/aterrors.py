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
"""Functions and exceptions that deal with AT errors"""

import re

import dbus
from twisted.python import log

CTS_ERROR = 'org.freedesktop.ModemManager.Error.Contacts'
NET_ERROR = 'org.freedesktop.ModemManager.Error.Network'
PIN_ERROR = 'org.freedesktop.ModemManager.Error.PIN'
MMS_ERROR = 'org.freedesktop.ModemManager.Error.MMS'
SMS_ERROR = 'org.freedesktop.ModemManager.Error.SMS'
GEN_ERROR = 'org.freedesktop.ModemManager.Error'
MM_MODEM_ERROR = 'org.freedesktop.ModemManager.Gsm'

ERROR_REGEXP = re.compile(r"""
# This regexp matches the following patterns:
# ERROR
# +CMS ERROR: 500
# +CME ERROR: foo bar
# +CME ERROR: 30
#
\r\n
(?P<error>                            # group named error
\+CMS\sERROR:\s\d{3}              |   # CMS ERROR regexp
\+CME\sERROR:\s\S+(\s\S+)*        |   # CME ERROR regexp
\+CME\sERROR:\s\d+                |   # CME ERROR regexp
INPUT\sVALUE\sIS\sOUT\sOF\sRANGE  |   # INPUT VALUE IS OUT OF RANGE
ERROR                                 # Plain ERROR regexp
)
\r\n
""", re.VERBOSE)


class GenericError(dbus.DBusException):
    """Exception raised when an ERROR has occurred"""
    _dbus_error_name = GEN_ERROR


class InputValueError(dbus.DBusException):
    """Exception raised when INPUT VALUE IS OUT OF RANGE is received"""
    _dbus_error_name = GEN_ERROR


class SerialResponseTimeout(dbus.DBusException):
    """Serial response timed out"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SerialResponseTimeout')


class Connected(dbus.DBusException):
    """Operation attempted whilst connected"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'Connected')


class PhoneFailure(dbus.DBusException):
    """Phone failure"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'PhoneFailure')


class NoConnection(dbus.DBusException):
    """No connection to phone"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NoConnection')


class LinkReserved(dbus.DBusException):
    """Phone-adaptor linkreserved"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'LinkReserved')


class OperationNotAllowed(dbus.DBusException):
    """Operation not allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'OperationNotAllowed')


class OperationNotSupported(dbus.DBusException):
    """Operation not supported"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'OperationNotSupported')


class PhSimPinRequired(dbus.DBusException):
    """PH-SIM PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'PhSimPinRequired')


class PhFSimPinRequired(dbus.DBusException):
    """PH-FSIM PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'PhFSimPinRequired')


class PhFPukRequired(dbus.DBusException):
    """PH-FSIM PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'PhFPukRequired')


class SimNotInserted(dbus.DBusException):
    """PH-PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimNotInserted')


class SimPinRequired(dbus.DBusException):
    """SIM PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimPinRequired')


class SimPukRequired(dbus.DBusException):
    """SIM PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimPukRequired')


class SimFailure(dbus.DBusException):
    """SIM failure"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimFailure')


class SimBusy(dbus.DBusException):
    """SIM busy"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimBusy')


class SimWrong(dbus.DBusException):
    """SIM wrong"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimWrong')


class SimNotStarted(dbus.DBusException):
    """SIM interface not started"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimNotStarted')


class IncorrectPassword(dbus.DBusException):
    """Incorrect password"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'IncorrectPassword')


class SimPin2Required(dbus.DBusException):
    """SIM PIN2 required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimPin2Required')


class SimPuk2Required(dbus.DBusException):
    """SIM PUK2 required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'SimPuk2Required')


class MemoryFull(dbus.DBusException):
    """Memory full"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'MemoryFull')


class InvalidIndex(dbus.DBusException):
    """Index invalid"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'InvalidIndex')


class NotFound(dbus.DBusException):
    """Not found"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NotFound')


class MemoryFailure(dbus.DBusException):
    """Memory failure"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'MemoryFailure')


class TextTooLong(dbus.DBusException):
    """Text string too long"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'TextTooLong')


class InvalidChars(dbus.DBusException):
    """Invalid characters in text string"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'InvalidChars')


class DialStringTooLong(dbus.DBusException):
    """Invalid dial string"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'DialStringTooLong')


class InvalidDialString(dbus.DBusException):
    """Invalid dial string"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'InvalidDialString')


class NoNetwork(dbus.DBusException):
    """No network service"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NoNetwork')


class NetworkTimeout(dbus.DBusException):
    """Network timeout"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkTimeout')


class NetworkNotAllowed(dbus.DBusException):
    """Only emergency calls are allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkNotAllowed')


class NetworkPinRequired(dbus.DBusException):
    """Network PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkPinRequired')


class NetworkPukRequired(dbus.DBusException):
    """Network PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkPukRequired')


class NetworkSubsetPinRequired(dbus.DBusException):
    """Network subset PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkSubsetPinRequired')


class NetworkSubsetPukRequired(dbus.DBusException):
    """Network subset PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'NetworkSubsetPukRequired')


class ServicePinRequired(dbus.DBusException):
    """Service PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'ServicePinRequired')


class ServicePukRequired(dbus.DBusException):
    """Service PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'ServicePukRequired')


class CharsetError(dbus.DBusException):
    """Raised when Wader can't find an appropriate charset at startup"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'CharsetError')


class CorporatePinRequired(dbus.DBusException):
    """Corporate PIN required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'CorporatePinRequired')


class CorporatePukRequired(dbus.DBusException):
    """Corporate PUK required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'CorporatePukRequired')


class HiddenKeyRequired(dbus.DBusException):
    """Hidden key required"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'HiddenKeyRequired')


class EapMethodNotSupported(dbus.DBusException):
    """EAP method not supported"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'EapMethodNotSupported')


class IncorrectParams(dbus.DBusException):
    """Incorrect params received"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'IncorrectParams')


class Unknown(dbus.DBusException):
    """Unknown error"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'Unknown')


class GprsIllegalMs(dbus.DBusException):
    """Illegal GPRS MS"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsIllegalMs')


class GprsIllegalMe(dbus.DBusException):
    """Illegal GPRS ME"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsIllegalMe')


class GprsServiceNotAllowed(dbus.DBusException):
    """GPRS service not allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsServiceNotAllowed')


class GprsPlmnNotAllowed(dbus.DBusException):
    """GPRS PLMN not allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsPlmnNotAllowed')


class GprsLocationNotAllowed(dbus.DBusException):
    """GPRS location not allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsLocationNotAllowed')


class GprsRoamingNotAllowed(dbus.DBusException):
    """GPRS roaming not allowed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsRoamingNotAllowed')


class GprsOptionNotSupported(dbus.DBusException):
    """GPRS used option not supported"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsOptionNotSupported')


class GprsNotSubscribed(dbus.DBusException):
    """GPRS not susbscribed"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsNotSubscribed')


class GprsOutOfOrder(dbus.DBusException):
    """GPRS out of order"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsOutOfOrder')


class GprsPdpAuthFailure(dbus.DBusException):
    """GPRS PDP authentication failure"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsPdpAuthFailure')


class GprsUnspecified(dbus.DBusException):
    """Unspecified GPRS error"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsUnspecified')


class GprsInvalidClass(dbus.DBusException):
    """Invalid GPRS class"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'GprsInvalidClass')


class ServiceTemporarilyOutOfOrder(dbus.DBusException):
    """Exception raised when service temporarily out of order"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR,
                                  'ServiceTemporarilyOutOfOrder')


class UnknownSubscriber(dbus.DBusException):
    """Exception raised when suscriber unknown"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'UnknownSubscriber')


class ServiceNotInUse(dbus.DBusException):
    """Exception raised when service not in use"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'ServiceNotInUse')


class ServiceNotAvailable(dbus.DBusException):
    """Exception raised when service not available"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'ServiceNotAvailable')


class UnknownNetworkMessage(dbus.DBusException):
    """Exception raised upon unknown network message"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'UnknownNetworkMessage')


class CallIndexError(dbus.DBusException):
    """Exception raised upon call index error"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'CallIndexError')


class CallStateError(dbus.DBusException):
    """Exception raised upon call state error"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, 'IncorrectPassword')


class MalformedUssdPduError(dbus.DBusException):
    """Exception raised when a malformed Ussd Pdu is received"""
    _dbus_error_name = "%s.%s" % (MM_MODEM_ERROR, "MalformedUssdPduError")


class ExpiredNotification(dbus.DBusException):
    """Exception raised when a GET.req petition fails"""
    _dbus_error_name = "%s.%s" % (MMS_ERROR, "ExpiredNotification")


class CMSError300(dbus.DBusException):
    """Phone failure"""


class CMSError301(dbus.DBusException):
    """SMS service of phone reserved """


class CMSError302(dbus.DBusException):
    """Operation not allowed"""


class CMSError303(dbus.DBusException):
    """Operation not supported"""


class CMSError304(dbus.DBusException):
    """Invalid PDU mode parameter"""


class CMSError305(dbus.DBusException):
    """Invalid text mode parameter"""


class CMSError310(dbus.DBusException):
    """SIM not inserted"""


class CMSError311(dbus.DBusException):
    """SIM PIN necessary"""


class CMSError313(dbus.DBusException):
    """SIM failure"""


class CMSError314(dbus.DBusException):
    """SIM busy"""


class CMSError315(dbus.DBusException):
    """SIM wrong"""


class CMSError320(dbus.DBusException):
    """Memory failure"""


class CMSError321(dbus.DBusException):
    """Invalid memory index"""


class CMSError322(dbus.DBusException):
    """Memory full"""


class CMSError330(dbus.DBusException):
    """SMSC address unknown"""


class CMSError331(dbus.DBusException):
    """No network service"""


class CMSError500(dbus.DBusException):
    """Unknown Error"""


ERROR_DICT = {
    # Generic error
    'ERROR': GenericError,

    # CME Errors
    '+CME ERROR: incorrect password': IncorrectPassword,
    '+CME ERROR: invalid characters in dial string': InvalidDialString,
    '+CME ERROR: no network service': NoNetwork,
    '+CME ERROR: not found': NotFound,
    '+CME ERROR: operation not allowed': OperationNotAllowed,
    '+CME ERROR: text string too long': TextTooLong,
    '+CME ERROR: SIM busy': SimBusy,
    '+CME ERROR: SIM failure': SimFailure,
    '+CME ERROR: SIM interface not started': SimNotStarted,
    '+CME ERROR: SIM interface not started yet': SimNotStarted,
    '+CME ERROR: SIM not inserted': SimNotInserted,
    '+CME ERROR: SIM PIN required': SimPinRequired,
    '+CME ERROR: SIM PUK required': SimPukRequired,
    '+CME ERROR: SIM PUK2 required': SimPuk2Required,

    # NUMERIC CME ERRORS
    '+CME ERROR: 0': PhoneFailure,
    '+CME ERROR: 1': NoConnection,
    '+CME ERROR: 3': OperationNotAllowed,
    '+CME ERROR: 4': OperationNotSupported,
    '+CME ERROR: 5': PhSimPinRequired,
    '+CME ERROR: 6': PhFSimPinRequired,
    '+CME ERROR: 7': PhFPukRequired,
    '+CME ERROR: 10': SimNotInserted,
    '+CME ERROR: 11': SimPinRequired,
    '+CME ERROR: 12': SimPukRequired,
    '+CME ERROR: 13': SimFailure,
    '+CME ERROR: 14': SimBusy,
    '+CME ERROR: 15': SimWrong,
    '+CME ERROR: 16': IncorrectPassword,
    '+CME ERROR: 17': SimPin2Required,
    '+CME ERROR: 18': SimPuk2Required,
    '+CME ERROR: 20': MemoryFull,
    '+CME ERROR: 21': InvalidIndex,
    '+CME ERROR: 22': NotFound,
    '+CME ERROR: 23': MemoryFailure,
    '+CME ERROR: 24': TextTooLong,
    '+CME ERROR: 26': DialStringTooLong,
    '+CME ERROR: 27': InvalidDialString,
    '+CME ERROR: 30': NoNetwork,
    '+CME ERROR: 31': NetworkTimeout,
    '+CME ERROR: 32': NetworkNotAllowed,
    '+CME ERROR: 40': NetworkPinRequired,
    '+CME ERROR: 41': NetworkPukRequired,
    '+CME ERROR: 42': NetworkSubsetPinRequired,
    '+CME ERROR: 43': NetworkSubsetPukRequired,
    '+CME ERROR: 44': ServicePinRequired,
    '+CME ERROR: 45': ServicePukRequired,
    '+CME ERROR: 46': CorporatePinRequired,
    '+CME ERROR: 47': CorporatePukRequired,
    '+CME ERROR: 48': HiddenKeyRequired,
    '+CME ERROR: 49': EapMethodNotSupported,
    '+CME ERROR: 50': IncorrectParams,
    '+CME ERROR: 100': Unknown,
    '+CME ERROR: 103': GprsIllegalMs,
    '+CME ERROR: 106': GprsIllegalMe,
    '+CME ERROR: 107': GprsServiceNotAllowed,
    '+CME ERROR: 111': GprsPlmnNotAllowed,
    '+CME ERROR: 112': GprsLocationNotAllowed,
    '+CME ERROR: 113': GprsRoamingNotAllowed,
    '+CME ERROR: 132': GprsOptionNotSupported,
    '+CME ERROR: 133': GprsNotSubscribed,
    '+CME ERROR: 134': GprsOutOfOrder,
    '+CME ERROR: 148': GprsPdpAuthFailure,
    '+CME ERROR: 149': GprsUnspecified,
    '+CME ERROR: 150': GprsInvalidClass,
    # not implemented on ModemManager (yet)
    '+CME ERROR: 260': ServiceTemporarilyOutOfOrder,
    '+CME ERROR: 261': UnknownSubscriber,
    '+CME ERROR: 262': ServiceNotInUse,
    '+CME ERROR: 263': ServiceNotAvailable,
    '+CME ERROR: 264': UnknownNetworkMessage,
    '+CME ERROR: 65281': CallStateError,

    # CMS Errors
    '+CMS ERROR: 300': CMSError300,
    '+CMS ERROR: 301': CMSError301,
    '+CMS ERROR: 302': CMSError302,
    '+CMS ERROR: 303': CMSError303,
    '+CMS ERROR: 304': CMSError304,
    '+CMS ERROR: 305': CMSError305,
    '+CMS ERROR: 310': CMSError310,
    '+CMS ERROR: 311': CMSError311,
    '+CMS ERROR: 313': CMSError313,
    '+CMS ERROR: 314': CMSError314,
    '+CMS ERROR: 315': CMSError315,
    '+CMS ERROR: 320': CMSError320,
    '+CMS ERROR: 321': CMSError321,
    '+CMS ERROR: 322': CMSError322,
    '+CMS ERROR: 330': CMSError330,
    '+CMS ERROR: 331': CMSError331,
    '+CMS ERROR: 500': CMSError500,

    # USER GARBAGE ERRORS
    'INPUT VALUE IS OUT OF RANGE': InputValueError,
}


def extract_error(s):
    """
    Scans ``s`` looking for AT Errors

    Returns a tuple with the exception, error and the match
    """
    try:
        match = ERROR_REGEXP.search(s)
        if match:
            try:
                error = match.group('error')
                exception = ERROR_DICT[error]
                return exception, error, match
            except KeyError, e:
                log.err(e, "%r didn't map to any of my keys" % error)

    except AttributeError:
        return None


def error_to_human(e):
    """Returns a human error out of ``e``"""
    name = e.get_dbus_name().split('.')[-1]
    return EXCEPT_TO_HUMAN[name]

EXCEPT_TO_HUMAN = {
    'PhoneFailure': "Phone failure",
    'NoConnection': "No Connection to phone",
    'LinkReserved': "Phone-adaptor link reserved",
    'OperationNotAllowed': "Operation not allowed",
    'OperationNotSupported': "Operation not supported",
    'PhSimPinRequired': "PH-SIM PIN required",
    'PhFSimPinRequired': "PH-FSIM PIN required",
    'PhFSimPukRequired': "PH-FSIM PUK required",
    'SimNotInserted': "SIM not inserted",
    'SimPinRequired': "SIM PIN required",
    'SimPukRequired': "SIM PUK required",
    'SimFailure': "SIM failure",
    'SimBusy': "SIM busy",
    'SimWrong': "SIM wrong",
    'IncorrectPassword': "Incorrect password",
    'SimPin2Required': "SIM PIN2 required",
    'SimPuk2Required': "SIM PUK2 required",
    'MemoryFull': "Memory full",
    'InvalidIndex': "Invalid index",
    'NotFound': "Not found",
    'MemoryFailure': "Memory failure",
    'TextTooLong': "Text string too long",
    'InvalidChars': "Invalid characters in text string",
    'DialStringTooLong': "Dial string too long",
    'InvalidDialString': "Invalid dial string",
    'NoNetwork': "No network service",
    'NetworkTimeout': "Network timeout",
    'NetworkNotAllowed': "Network not allowed - Emergency calls only",
    'NetworkPinRequired': "Network personalization PIN required",
    'NetworkPukRequired': "Network personalization PUK required",
    'NetworkSubsetPinRequired': "Network subset personalization PIN required",
    'NetworkSubsetPukRequired': "Network subset personalization PUK required",
    'ServicePinRequired': "Service provider personalization PIN required",
    'ServicePukRequired': "Service provider personalization PUK required",
    'CorporatePinRequired': "Corporate personalization PIN required",
    'CorporatePukRequired': "Corporate personalization PUK required",
    'HiddenKeyRequired': "Hidden key required",
    'EapMethodNotSupported': "EAP method not supported",
    'IncorrectParams': "Incorrect parameters",
    'Unknown': "Unknown error",
    'GprsIllegalMs': "Illegal MS",
    'GprsIllegalMe': "Illegal ME",
    'GprsServiceNotAllowed': "GPRS services not allowed",
    'GprsPlmnNotAllowed': "PLMN not allowed",
    'GprsLocationNotAllowed': "Location are not allowed",
    'GprsRoamingNotAllowed': "Roaming not allowed in this location area",
    'GprsOptionNotSupported': "Service option not supported",
    'GprsNotSuscribed': "Requested service option not suscribed",
    'GprsOutOfOrder': "Service temporarily out of order",
    'GprsPdpAuthFailure': "PDP authentication failure",
    'GprsUnspecified': "Unspecified GPRS error",
    'GprsInvalidClass': "Invalid mobile class",

    # Wader's own errors
    'NetworkRegistrationError': "Could not register with home network",
}
