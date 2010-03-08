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
"""Wader interfaces"""

from zope.interface import Interface, Attribute


class IContact(Interface):
    """Interface that all contact backends must implement"""
    name = Attribute("""Contact's name""")
    number = Attribute("""Contact's number""")
    index = Attribute("""Contact's index""")

    def to_csv():
        """Returns a list with the name and number formatted for csv"""


class IMessage(Interface):
    """Interface that all message backends must implement"""
    number = Attribute("""SMS sender""")
    text = Attribute("""SMS text""")
    index = Attribute("""Contact's index""")



class IBackend(Interface):
    """Interface that all the integration backends must implement"""

    def get_dialer_klass(device):
        """Returns the dialer class that ``device`` will use for dialing up"""

    def get_profile_manager(arg=None):
        """
        Returns this backend's profile manager

        ``arg`` is optional and is used in backends that require an
        initialization argument.
        """

    def get_keyring():
        """Returns an instance of the keyring manager for this platform"""

    def should_be_used():
        """Returns True if this backend should be used"""


class IProfileManagerBackend(Interface):
    """Interface that all the profile managers backends must implement"""

    def add_profile(opts):
        """Adds a profile with the given ``opts``"""

    def get_profile_by_uuid(uuid):
        """Returns the profile identified by ``uuid``"""

    def get_profile_by_object_path(opath):
        """Returns the profile with object path ``opath``"""

    def get_profile_options_from_network(network):
        """Returns the profile options out of ``network``"""

    def get_profiles():
        """Returns all the profiles in the system"""

    def remove_profile(profile):
        """Removes ``profile`` from the system"""

    def update_profile(profile, opts):
        """Updates ``profile`` with ``opts``"""


class IProfile(Interface):
    """Interface that all the profile objects must implement"""

    def get_settings():
        """Returns a dictionary with all the settings"""

    def get_secrets():
        """Returns the connection secrets"""

    def get_timestamp():
        """Returns the last time the profile was used"""

    def is_good():
        """Has this profile been successfully used?"""

    def update(props):
        """Updates the profile with ``props``"""

    def remove():
        """Removes the profile"""


class ICollaborator(Interface):
    """
    ICollaborator aids AuthStateMachine providing necessary PIN/PUK/Whatever

    AuthStateMachine needs an object that provides ICollaborator in order to
    work. ICollaborator abstracts the mechanism through wich the PIN/PUK is
    obtained.
    """

    def get_pin():
        """
        Returns the PIN

        :rtype: `Deferred`
        """

    def get_puk():
        """
        Returns a (puk, sim) tuple

        :rtype: `Deferred`
        """

    def get_puk2():
        """
        Returns a (puk2, sim) tuple

        :rtype: `Deferred`
        """


class IDialer(Interface):

    def close(arg):
        """Frees internal dialer resources"""

    def configure(config, device):
        """Configures the dialer with `config` for `device`"""

    def connect():
        """
        Connects to Internet

        :rtype: `Deferred`
        """

    def disconnect():
        """
        Disconnects from Internet

        :rtype: `Deferred`
        """

    def stop():
        """
        Stops the connection attempt

        :rtype: `Deferred`
        """


class IWaderPlugin(Interface):
    """Base interface for all Wader plugins"""
    name = Attribute("""Plugin's name""")
    version = Attribute("""Plugin's version""")
    author = Attribute("""Plugin's author""")

    def initialize(init_obj):
        """
        Initializes the plugin using ``init_obj``

        :type init_obj: dict
        """

    def close():
        """Closes the plugin"""


class IDevicePlugin(IWaderPlugin):
    """Interface that all device plugins should implement"""

    baudrate = Attribute("""At which speed should we talk with this guy""")
    custom = Attribute("""Container with all the device's customizations""")
    sim = Attribute("""SIM object""")
    sconn = Attribute("""Reference to the serial connection instance""")
    __properties__ = Attribute("""
            pairs of properties that must be satisfied by DBus backend""")


class IRemoteDevicePlugin(IDevicePlugin):
    """Interface that all remote device plugins should implent"""

    __remote_name__ = Attribute("""Response of an AT+CGMM command""")


class IOSPlugin(IWaderPlugin):

    distrib_id = Attribute("""Name of the OS/Distro""")
    distrib_version = Attribute("""Version of the OS/Distro""")

    def add_default_route(iface):
        """Sets a default route for ``iface``"""

    def delete_default_route(iface):
        """Deletes default route for ``iface``"""

    def add_dns_info(dnsinfo, iface=None):
        """
        Adds ``dnsinfo`` to ``iface``

        type dnsinfo: tuple
        """

    def delete_dns_info(dnsinfo, iface=None):
        """Deletes ``dnsinfo`` from ``iface``"""

    def configure_iface(iface, ip='', action='up'):
        """
        Configures ``iface`` with ``ip`` and ``action``

        ``action`` can be either 'up' or 'down'. If you bring down
        an iface, ip will be ignored.
        """

    def get_iface_stats(iface):
        """Returns ``iface`` network statistics"""

    def get_timezone():
        """
        Returns the timezone of the OS

        :rtype: str
        """

    def get_tzinfo():
        """Returns a :class:`pytz.timezone` out the timezone"""

    def is_valid():
        """Returns True if we are on the given OS/Distro"""


class IHardwareManager(Interface):

    def get_devices():
        """
        Returns a list with all the devices present in the system

        :rtype: `Deferred`
        """

    def register_controller(controller):
        """
        Registers ``controller`` as the driver class of this HW manager

        This reference will be used to emit Device{Add,Remov}ed signals
        upon hotplugging events.
        """


class IContactProvider(IWaderPlugin):

    def add_contact(data):
        """
        Returns a subclass of :class:`~wader.common.contact.Contact`

        ``data`` has two required keys, `name` and `number`

        :type data: dict
        """

    def edit_contact(contact):
        """
        Edits ``contact`` with the new values

        :raises: NotImplementedError if the backend cannot edit contacts
        """

    def find_contacts_by_name(name):
        """
        Returns an iterator with all the contacts whose name match ``name``
        """

    def find_contacts_by_number(number):
        """
        Returns an iterator with all the contacts whose number match ``number``
        """

    def list_contacts():
        """Returns a generator with all the contacts in the backend"""

    def remove_contact(contact):
        """Removes ``contact``"""
