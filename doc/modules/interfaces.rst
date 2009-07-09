:mod:`wader.common.interfaces`
==============================

.. automodule:: wader.common.interfaces

Classes
--------

.. autoclass:: IContact
   :show-inheritance:

   .. method:: to_csv()

      Returns a csv string with the contact info

.. autoclass:: IMessage
   :show-inheritance:

.. autoclass:: ICollaborator
   :show-inheritance:

   .. method:: get_pin()

      Returns the PIN

      :rtype: `Deferred`

   .. method:: get_puk()

      Returns a tuple with the PUK and PIN

      :rtype: `Deferred`

   .. method:: get_puk2()

      Returns a tuple with the PUK2 and PIN

      :rtype: `Deferred`

.. autoclass:: IDialer
   :show-inheritance:

   .. method:: configure(config, device)

      Configures the dialer with `config` for `device`

      :rtype: `Deferred`

   .. method:: connect()

      Connects to Internet

      :rtype: `Deferred`

   .. method:: disconnect()

      Disconnects from Internet

      :rtype: `Deferred`

   .. method:: stop()

      Stops an ongoing connection attempt

      :rtype: `Deferred`

.. autoclass:: IWaderPlugin
   :show-inheritance:

   .. method:: initialize()

      Initializes the plugin

      :rtype: `Deferred`

   .. method:: close()

      Closes the plugin

      :rtype: `Deferred`

.. autoclass:: IDevicePlugin
   :show-inheritance:

.. autoclass:: IRemoteDevicePlugin
   :show-inheritance:

.. autoclass:: IOSPlugin
   :show-inheritance:

   .. method:: is_valid()

      Returns True if we are in the given OS/distro

      :rtype: bool

   .. method:: add_default_route(iface)

      Sets ``iface`` as the default route

   .. method:: delete_default_route(iface)

      Unsets ``iface`` as the default route

   .. method:: add_dns_info(dnsinfo, iface=None)

      Sets up DNS ``dnsinfo`` for ``iface``

   .. method:: delete_dns_info(dnsinfo, iface=None)

      Deletes ``dnsinfo`` from ``iface``

   .. method:: configure_iface(iface, ip='', action='up')

      Configures `iface` with `ip` and `action`

      :param action: can be either 'up' or 'down'
      :param ip: only used when ``action`` == 'up'

   .. method:: get_timezone()

      Returns the timezone of the OS

      :rtype: str

   .. method:: get_tzinfo(dnsinfo, iface=None)

      Returns a :class:`pytz.timezone` out the timezone


.. autoclass:: IHardwareManager
   :show-inheritance:

   .. method:: get_devices()

      Returns a list with all the devices present in the system

      :rtype: `Deferred`

   .. method:: register_controller(controller)

      Registers ``controller`` as the driver class of this HW manager

      This reference will be used to emit Device{Add,Remov}ed signals
      upon hotplugging events.

