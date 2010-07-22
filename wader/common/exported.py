# -*- coding: utf-8 -*-
# Copyright (C) 2008 Warp Networks S.L.
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
"""
I export :class:`~wader.common.middleware.WCDMAWrapper` methods over DBus
"""
import dbus
from dbus.service import Object, BusName, method, signal
from twisted.python import log

from wader.common.consts import (SMS_INTFACE, CTS_INTFACE, NET_INTFACE,
                                 CRD_INTFACE, MDM_INTFACE, WADER_SERVICE,
                                 HSO_INTFACE, SPL_INTFACE, USD_INTFACE,
                                 MMS_INTFACE)
from wader.common.sms import Message
from wader.common.contact import Contact
from wader.common._dbus import DBusExporterHelper
from wader.common.utils import (convert_ip_to_int,
                                convert_network_mode_to_access_technology)

# welcome to the multiple inheritance madness!
# python-dbus currently lacks an "export_as" keyword for use cases like
# us. Where we have a main object with dozens of methods that we want to
# export over several interfaces under repeated names, such as:
#   org.freedesktop.ModemManager.Contacts.List
#   org.freedesktop.ModemManager.SMS.List
# currently python-dbus requires you to create a new class and it will find
# the appropiated implementation through the MRO. But this leads to MH madness
# What we can do thou is rely on composition instead of MH for this one


def to_a(_list, signature='u'):
    """
    Returns a :class:`dbus.Array` out of `_list`

    :param signature: The dbus signature of the array
    """
    return dbus.Array(sorted(_list), signature=signature)


class ModemExporter(Object, DBusExporterHelper):
    """I export the org.freedesktop.ModemManager.Modem interface"""

    def __init__(self, device):
        name = BusName(WADER_SERVICE, bus=dbus.SystemBus())
        super(ModemExporter, self).__init__(bus_name=name,
                                            object_path=device.opath)
        self.device = device
        self.sconn = device.sconn

    @method(MDM_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Connect(self, number, async_cb, async_eb):
        """
        Dials in the given number

        :param number: number to dial
        """
        assert 'conn_id' in self.sconn.state_dict, "Did you call SetApn?"
        assert len(number) == 4, "bad number: %s" % number
        assert number[-1] == '#', "bad number: %s" % number

        num = "%s***%d#" % (str(number[:-1]), self.sconn.state_dict['conn_id'])
        d = self.sconn.connect_to_internet(num)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(MDM_INTFACE, in_signature='', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Disconnect(self, async_cb, async_eb):
        """Disconnects modem"""
        d = self.sconn.disconnect_from_internet()
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(MDM_INTFACE, in_signature='b', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Enable(self, enable, async_cb, async_eb):
        """
        Performs some initial setup in the device

        :param enable: whether device should be enabled or disabled
        :type enable: bool
        """
        d = self.sconn.enable_device(enable)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, _property):
        """See org.freedesktop.DBus.Properties documentation"""
        try:
            return self.device.get_property(interface, _property)
        except KeyError:
            args = (interface, _property)
            raise ValueError("Unknown interface %s or property %s" % args)

    @method(dbus.PROPERTIES_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        """See org.freedesktop.DBus.Properties documentation"""
        if interface_name in self.device.props:
            return self.device.props[interface_name]

    @method(MDM_INTFACE, in_signature='', out_signature='(sss)',
            async_callbacks=('async_cb', 'async_eb'))
    def GetInfo(self, async_cb, async_eb):
        """
        Returns the manufacturer, modem model and firmware version

        :rtype: tuple
        """
        d = self.sconn.get_hardware_info()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(MDM_INTFACE, in_signature='', out_signature='(uuuu)',
            async_callbacks=('async_cb', 'async_eb'))
    def GetIP4Config(self, async_cb, async_eb):
        """
        Requests the IP4 configuration from the device

        :rtype: tuple
        """
        d = self.sconn.get_ip4_config()
        d.addCallback(lambda reply: map(convert_ip_to_int, reply))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(MDM_INTFACE, in_signature='', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def FactoryReset(self, async_cb, async_eb):
        """Reset the modem to as close to factory state as possible"""
        d = self.sconn.reset_settings()
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @signal(dbus_interface=MDM_INTFACE, signature='o')
    def DeviceEnabled(self, opath):
        log.msg("emitting DeviceEnabled('%s')" % opath)

    @signal(dbus_interface=MDM_INTFACE, signature='(uuuu)')
    def DialStats(self, (rx_bytes, tx_bytes, rx_rate, tx_rate)):
        pass

    @signal(dbus_interface=dbus.PROPERTIES_IFACE, signature='sa{sv}')
    def MmPropertiesChanged(self, iface, properties):
        log.msg("emitting MmPropertiesChanged: %s %s" % (iface, properties))


class SimpleExporter(ModemExporter):
    """I export the org.freedesktop.ModemManager.Modem.Simple interface"""

    @method(SPL_INTFACE, in_signature='a{sv}', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Connect(self, settings, async_cb, async_eb):
        """
        Connects with the given settings

        :type settings: dict
        :param settings: documented in ModemManager spec
        """
        assert 'number' in settings, "No number in %s" % settings
        number = settings['number']
        assert len(number) == 4, "bad number: %s" % number
        assert number[-1] == '#', "bad number: %s" % number

        d = self.sconn.connect_simple(settings)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(SPL_INTFACE, in_signature='', out_signature='a{sv}',
            async_callbacks=('async_cb', 'async_eb'))
    def GetStatus(self, async_cb, async_eb):
        """
        Get the modem status

        :rtype: dict
        """

        def get_simple_status_cb(status):
            # by default it is converted to Int32
            for name in ['signal_quality', 'band']:
                status[name] = dbus.UInt32(status[name])

            return status

        d = self.sconn.get_simple_status()
        d.addCallback(get_simple_status_cb)
        return self.add_callbacks(d, async_cb, async_eb)


class CardExporter(SimpleExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Card methods"""

    @method(CRD_INTFACE, in_signature='ss', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def ChangePin(self, oldpin, newpin, async_cb, async_eb):
        """
        Changes PIN from ``oldpin`` to ``newpin``

        :param oldpin: The old PIN
        :param newpin: The new PIN
        """
        d = self.sconn.change_pin(oldpin, newpin)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def Check(self, async_cb, async_eb):
        """
        Returns the SIM authentication state

        :raise ``SimPinRequired``: If PIN is required
        :raise ``SimPukRequired``: If PUK is required
        :raise ``SimPuk2Required``: If PUK2 is required
        """
        d = self.sconn.check_pin()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='b', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def EnableEcho(self, enable, async_cb, async_eb):
        """
        Enables or disables echo

        Enabling echo will leave your connection unusable as this
        application assumes that it will be disabled

        :param enable: Whether echo should be disabled or not
        """
        if enable:
            d = self.sconn.enable_echo()
        else:
            d = self.sconn.disable_echo()
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='sb', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def EnablePin(self, pin, enable, async_cb, async_eb):
        """
        Enables or disables PIN authentication

        :param pin: The PIN to use
        :param enable: Whether PIN auth should be enabled or disabled
        """
        d = self.sconn.enable_pin(pin, enable)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def GetCharset(self, async_cb, async_eb):
        """Returns active charset"""
        d = self.sconn.get_charset()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='', out_signature='as',
           async_callbacks=('async_cb', 'async_eb'))
    def GetCharsets(self, async_cb, async_eb):
        """Returns the available charsets in SIM"""
        d = self.sconn.get_charsets()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def GetImei(self, async_cb, async_eb):
        """Returns the IMEI"""
        d = self.sconn.get_imei()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def GetImsi(self, async_cb, async_eb):
        """Returns the IMSI"""
        d = self.sconn.get_imsi()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='s', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def SendATString(self, at_str, async_cb, async_eb):
        """
        Sends an arbitrary AT command

        :param at_str: The AT command to be sent
        """
        d = self.sconn.send_at(at_str)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SendPin(self, pin, async_cb, async_eb):
        """
        Sends ``pin`` to authenticate with SIM

        :param pin: The PIN to authenticate with
        """
        d = self.sconn.send_pin(pin)
        # check_initted_device will check if a Enable call was
        # interrupted because of PINNeededError and will continue
        # if auth is successful
        d.addCallback(self.sconn._check_initted_device)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='ss', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SendPuk(self, puk, pin, async_cb, async_eb):
        """
        Sends ``puk`` and ``pin`` to authenticate with SIM

        :param puk: The PUK to authenticate with
        :param pin: The PIN to authenticate with
        """
        d = self.sconn.send_puk(puk, pin)
        # check_initted_device will check if a Enable call was
        # interrupted because of PUKNeededError and will continue
        # if auth is successful
        d.addCallback(self.sconn._check_initted_device)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CRD_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetCharset(self, charset, async_cb, async_eb):
        """
        Sets the SIM charset to ``charset``

        :param charset: The character set to use
        """
        d = self.sconn.set_charset(charset.encode('utf8'))
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)


class ContactsExporter(CardExporter):
    """
    I export the org.freedesktop.ModemManager.Modem.Gsm.Contacts interface
    """

    @method(CTS_INTFACE, in_signature='ss', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def Add(self, name, number, async_cb, async_eb):
        """
        Adds a contact and returns the index

        :param name: The contact name
        :param number: The contact number
        :rtype: int
        """
        d = self.sconn.add_contact(Contact(name, number))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Delete(self, index, async_cb, async_eb):
        """
        Deletes the contact at ``index``

        :param index: The index of the contact to be deleted
        """
        d = self.sconn.delete_contact(index)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='uss', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def Edit(self, index, name, number, async_cb, async_eb):
        """
        Edits the contact at ``index``

        :param name: The new name of the contact to be edited
        :param number: The new number of the contact to be edited
        :param index: The index of the contact to be edited
        """
        d = self.sconn.add_contact(Contact(name, number, index=index))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='s', out_signature='a(uss)',
            async_callbacks=('async_cb', 'async_eb'))
    def FindByName(self, pattern, async_cb, async_eb):
        """
        Returns list of contacts whose name match ``pattern``

        :param pattern: The pattern to match contacts against
        :rtype: list
        """
        d = self.sconn.find_contacts(pattern)
        d.addCallback(lambda contacts:
                      [(c.index, c.name, c.number) for c in contacts])
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='s', out_signature='a(uss)',
            async_callbacks=('async_cb', 'async_eb'))
    def FindByNumber(self, number, async_cb, async_eb):
        """
        Returns list of contacts whose number match ``number``

        :param number: The number to match contacts against
        :rtype: list
        """
        d = self.sconn.list_contacts()
        d.addCallback(lambda contacts:
                      [(c.index, c.name, c.number) for c in contacts
                            if c.number.endswith(number)])
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='u', out_signature='(uss)',
            async_callbacks=('async_cb', 'async_eb'))
    def Get(self, index, async_cb, async_eb):
        """
        Returns the contact at ``index``

        :param index: The index of the contact to get
        :rtype: tuple
        """
        d = self.sconn.get_contact(index)
        d.addCallback(lambda c: (c.index, c.name, c.number))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def GetCount(self, async_cb, async_eb):
        """Returns the number of contacts in the SIM"""
        d = self.sconn.list_contacts()
        d.addCallback(len)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='', out_signature='i',
            async_callbacks=('async_cb', 'async_eb'))
    def GetPhonebookSize(self, async_cb, async_eb):
        """Returns the phonebook size"""
        d = self.sconn.get_phonebook_size()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(CTS_INTFACE, in_signature='', out_signature='a(uss)',
            async_callbacks=('async_cb', 'async_eb'))
    def List(self, async_cb, async_eb):
        """
        Returns all the contacts in the SIM

        :rtype: list of tuples
        """
        d = self.sconn.list_contacts()
        d.addCallback(lambda contacts:
                      [(c.index, c.name, c.number) for c in contacts])
        return self.add_callbacks(d, async_cb, async_eb)


class NetworkExporter(ContactsExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Network interface"""

    @method(NET_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def GetApns(self, async_cb, async_eb):
        """Returns all the APNS stored in the system"""
        d = self.sconn.get_apns()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def GetBand(self, async_cb, async_eb):
        """Returns the currently used band"""
        d = self.sconn.get_band()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def GetNetworkMode(self, async_cb, async_eb):
        """Returns the network mode"""
        d = self.sconn.get_network_mode()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='(uss)',
            async_callbacks=('async_cb', 'async_eb'))
    def GetRegistrationInfo(self, async_cb, async_eb):
        """
        Returns the network registration status and operator

        :rtype: tuple
        """
        d = self.sconn.get_netreg_info()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='as',
            async_callbacks=('async_cb', 'async_eb'))
    def GetRoamingIDs(self, async_cb, async_eb):
        """Returns all the roaming IDs stored in the SIM"""
        d = self.sconn.get_roaming_ids()
        d.addCallback(lambda objs: [obj.netid for obj in objs])
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='i',
            async_callbacks=('async_cb', 'async_eb'))
    def GetSignalQuality(self, async_cb, async_eb):
        """Returns the signal quality"""
        d = self.sconn.get_signal_quality()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='', out_signature='aa{ss}',
            async_callbacks=('async_cb', 'async_eb'))
    def Scan(self, async_cb, async_eb):
        """Returns the basic information of the networks around"""
        d = self.sconn.get_network_names()

        def process_netnames(netobjs):
            response = []
            for n in netobjs:
                # status should be an int, but it appeared in the
                # ModemManager spec first as a string and in order
                # to not break existing software (it seems that
                # nm-applet in OpenSuSe uses it) we decided not to
                # change it for now.
                net = {'status': str(n.stat),
                       'operator-long': n.long_name,
                       'operator-short': n.short_name,
                       'operator-num': n.netid}

                if n.rat:
                    # some devices won't provide this info
                    net['access-tech'] = str(n.rat)

                response.append(net)

            return response

        d.addCallback(process_netnames)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetAllowedMode(self, mode, async_cb, async_eb):
        """
        Set the access technologies a device is allowed to use when connecting

        :param mode: The allowed mode. Device may not support all modes.
        :type mode: int
        """
        d = self.sconn.set_allowed_mode(mode)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetApn(self, apn, async_cb, async_eb):
        """
        Sets the APN to ``apn``

        :param apn: The APN to use
        """
        d = self.sconn.set_apn(apn)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetBand(self, band, async_cb, async_eb):
        """
        Sets the band to ``band``

        :param band: The band to use
        :type band: int
        """
        d = self.sconn.set_band(band)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetNetworkMode(self, mode, async_cb, async_eb):
        """
        Sets the network mode to ``mode``

        :param mode: The network mode to use
        :type mode: int
        """
        d = self.sconn.set_network_mode(mode)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='b', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetRegistrationNotification(self, active, async_cb, async_eb):
        """
        Sets the network registration notifications

        :param active: Enable registration notifications
        :type active: bool
        """
        d = self.sconn.set_netreg_notification(int(active))
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='uu', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetInfoFormat(self, mode, _format, async_cb, async_eb):
        """
        Sets the network info format

        :param mode: The network mode
        :type mode: int
        :param _format: The network format
        :type _format: int
        """
        d = self.sconn.set_network_info_format(mode, _format)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(NET_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Register(self, netid, async_cb, async_eb):
        """
        Registers with ``netid``

        If netid is an empty string it will try to register with the
        home network or the first provider around whose MNC matches
        with one of the response of +CPOL?

        :param netid: The network id to register with
        :type netid: str
        """
        d = self.sconn.register_with_netid(netid)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @signal(dbus_interface=NET_INTFACE, signature='uss')
    def RegistrationInfo(self, status, operator_code, operator_name):
        args = (status, operator_code, operator_name)
        log.msg("emitting RegistrationInfo(%d, '%s', '%s')" % args)

    @signal(dbus_interface=NET_INTFACE, signature='u')
    def NetworkMode(self, mode):
        log.msg("emitting NetworkMode(%d)" % mode)
        # we will update AccessTechnology from here
        tech = convert_network_mode_to_access_technology(mode)
        self.device.set_property(NET_INTFACE, 'AccessTechnology', tech)

    @signal(dbus_interface=NET_INTFACE, signature='u')
    def CregReceived(self, status):
        log.msg("emitting CregReceived(%d)" % status)

    @signal(dbus_interface=NET_INTFACE, signature='u')
    def SignalQuality(self, rssi):
        log.msg("emitting SignalQuality(%d)" % rssi)


class MmsExporter(NetworkExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Mms interface"""

    @method(MMS_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Acknowledge(self, index, async_cb, async_eb):
        """
        Acknowledges reception of the MMS identified by ``index``

        :param index: The MMS index
        """
        d = self.sconn.acknowledge_mms(index)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(MMS_INTFACE, in_signature='u', out_signature='a{sa{sv}}',
            async_callbacks=('async_cb', 'async_eb'))
    def Download(self, index, async_cb, async_eb):
        """
        Retrieves the MMS identified by ``index``

        :param index: The MMS index
        """
        d = self.sconn.download_mms(index)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(MMS_INTFACE, in_signature='a{sa{sv}}', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def Send(self, mms_data, async_cb, async_eb):
        """
        Sends ``mms_data`` and returns the Message-Id

        :param index: The MMS index
        """
        d = self.sconn.send_mms(mms_data)
        return self.add_callbacks(d, async_cb, async_eb)

    @signal(dbus_interface=MMS_INTFACE, signature='s')
    def Delivered(self, message_id):
        log.msg('Emitting Delivered(%s)' % message_id)

    @signal(dbus_interface=MMS_INTFACE, signature='ua{sv}')
    def MMSReceived(self, index, headers):
        log.msg('Emitting MMSReceived(%d, %s)' % (index, headers))


class SmsExporter(MmsExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Sms interface"""

    @method(SMS_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Delete(self, index, async_cb, async_eb):
        """
        Deletes the SMS at ``index``

        :param index: The SMS index
        """
        d = self.sconn.delete_sms(index)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='u', out_signature='a{sv}',
            async_callbacks=('async_cb', 'async_eb'))
    def Get(self, index, async_cb, async_eb):
        """
        Returns the SMS stored at ``index``

        :param index: The SMS index
        """
        d = self.sconn.get_sms(index)
        d.addCallback(lambda sms: sms.to_dict())
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def GetSmsc(self, async_cb, async_eb):
        """Returns the SMSC number stored in the SIM"""
        d = self.sconn.get_smsc()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='', out_signature='u',
            async_callbacks=('async_cb', 'async_eb'))
    def GetFormat(self, async_cb, async_eb):
        """Returns 1 if SMS format is text and 0 if SMS format is PDU"""
        d = self.sconn.get_sms_format()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='', out_signature='aa{sv}',
            async_callbacks=('async_cb', 'async_eb'))
    def List(self, async_cb, async_eb):
        """Returns all the SMS stored in SIM"""
        d = self.sconn.list_sms()
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='a{sv}', out_signature='au',
            async_callbacks=('async_cb', 'async_eb'))
    def Save(self, sms, async_cb, async_eb):
        """
        Save a SMS ``sms`` and returns the index

        :param sms: dictionary with the settings to use
        :rtype: int
        """
        d = self.sconn.save_sms(Message.from_dict(sms))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='a{sv}', out_signature='au',
            async_callbacks=('async_cb', 'async_eb'))
    def Send(self, sms, async_cb, async_eb):
        """
        Sends SMS ``sms``

        :param sms: dictionary with the settings to use
        :rtype: list
        """
        d = self.sconn.send_sms(Message.from_dict(sms))
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='u', out_signature='au',
            async_callbacks=('async_cb', 'async_eb'))
    def SendFromStorage(self, index, async_cb, async_eb):
        """
        Sends the SMS stored at ``index`` and returns the new index

        :param index: The index of the stored SMS to be sent
        :rtype: int
        """
        d = self.sconn.send_sms_from_storage(index)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='u', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetFormat(self, _format, async_cb, async_eb):
        """Sets the SMS format"""
        if _format not in [0, 1]:
            async_eb(ValueError("Invalid SMS format %s" % repr(_format)))

        d = self.sconn.set_sms_format(_format)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='uuuuu', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetIndication(self, mode, mt, bm, ds, bfr, async_cb, async_eb):
        """Sets the SMS indication"""
        d = self.sconn.set_sms_indication(mode, mt, bm, ds, bfr)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(SMS_INTFACE, in_signature='s', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def SetSmsc(self, smsc, async_cb, async_eb):
        """
        Sets the SMSC to ``smsc``

        :param smsc: The SMSC to use
        """
        d = self.sconn.set_smsc(smsc)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @signal(dbus_interface=SMS_INTFACE, signature='ub')
    def SMSReceived(self, index, completed):
        log.msg('Emitting SMSReceived(%d, %s)' % (index, completed))

    @signal(dbus_interface=SMS_INTFACE, signature='ub')
    def Completed(self, index, completed):
        log.msg('emitting Complete(%d)' % index)

    @signal(dbus_interface=SMS_INTFACE, signature='u')
    def Delivered(self, reference):
        log.msg('emitting Delivered(%d)' % reference)


class UssdExporter(SmsExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Ussd interface"""

    @method(USD_INTFACE, in_signature='', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Cancel(self, ussd, async_cb, async_eb):
        """Cancels an ongoing USSD session"""
        d = self.sconn.cancel_ussd()
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)

    @method(USD_INTFACE, in_signature='s', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def Initiate(self, command, async_cb, async_eb):
        """Sends the USSD command ``command``"""
        d = self.sconn.send_ussd(command)
        return self.add_callbacks(d, async_cb, async_eb)

    @method(USD_INTFACE, in_signature='s', out_signature='s',
            async_callbacks=('async_cb', 'async_eb'))
    def Respond(self, reply, async_cb, async_eb):
        """Sends ``reply`` to the network"""
        d = self.sconn.send_ussd(reply)
        return self.add_callbacks(d, async_cb, async_eb)

    @signal(dbus_interface=USD_INTFACE, signature='s')
    def NotificationReceived(self, message):
        log.msg("emitting NotificationReceived(%s)" % message)

    @signal(dbus_interface=USD_INTFACE, signature='s')
    def RequestReceived(self, message):
        log.msg("emitting RequestReceived(%s)" % message)


class WCDMAExporter(UssdExporter):
    """I export the org.freedesktop.ModemManager.Modem* interface"""

    def __str__(self):
        return self.device.__remote_name__

    __repr__ = __str__


class HSOExporter(WCDMAExporter):
    """I export the org.freedesktop.ModemManager.Modem.Gsm.Hso interface"""

    @method(HSO_INTFACE, in_signature='ss', out_signature='',
            async_callbacks=('async_cb', 'async_eb'))
    def Authenticate(self, user, passwd, async_cb, async_eb):
        """
        Authenticate using ``user`` and ``passwd``

        :param user: The username to be used in authentication
        :param passwd: The password to be used in authentication
        """
        d = self.sconn.hso_authenticate(user, passwd)
        return self.add_callbacks_and_swallow(d, async_cb, async_eb)
