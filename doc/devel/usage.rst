================================
How to use Wader in your project
================================

ModemManager API
================

Wader is the first project, apart from :term:`ModemManager` itself, that
implements :term:`ModemManager`'s API. This means that Wader can be
seamlessly integrated with :term:`NetworkManager` 0.7.1+.

Wader DBus overview
===================

Wader is a system service, running under a privileged uid. Wader is started
automatically the first time you invoke the Wader service::

    dbus-send --system --dest=org.freedesktop.ModemManager --print-reply \
        /org/freedesktop/ModemManager org.freedesktop.ModemManager.EnumerateDevices
    method return sender=:1.193 -> dest=:1.189 reply_serial=2
       array [
             object path "/org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial"
       ]

Wader has found a Huawei E220 present in the system. The ``EnumerateDevices``
method call returns an array of object paths.

The next operation should **always** be
``org.freedesktop.ModemManager.Modem.Enable``. This method receives a boolean
argument indicating whether the device should be enabled or not::

    dbus-send --system --dest=org.freedesktop.ModemManager --print-reply \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Enable boolean:true
    Error org.freedesktop.ModemManager.Modem.Gsm: SimPinRequired: \
        org.freedesktop.ModemManager.Error.PIN: org.freedesktop.ModemManager.Error.PIN:

In this case, the ``Enable`` operation has raised an exception, PIN/PUK is
needed. The ``Enable`` machinery, and its state, will be resumed if we send
the correct PIN/PUK. Had we been previously authenticated or PIN/PUK were not
enabled, the method would not have returned anything::

    dbus-send --system --dest=org.freedesktop.ModemManager --print-reply \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Card.SendPin string:0000
    method return sender=:1.193 -> dest=:1.191 reply_serial=2

After successfully entering the PIN, the device is given about fifteen seconds
to settle and perform its internal setup. After this point you can interact
with the device as you please.

.. note::

    There are plans to create a `device-specific interface`_ that will ask
    the device when its ready rather than just giving 15 seconds and hoping
    that it will suffice.

    .. _device-specific interface: http://public.warp.es/wader/ticket/77

And how do you obtain the UDIs of the devices then?
+++++++++++++++++++++++++++++++++++++++++++++++++++

Wader internally interacts with :term:`Hal` and requests the UDIs of all the
devices that have modem capabilities. The command
``FindDeviceByCapability("modem")`` returns the object paths of the devices
tagged with the modem capability. Armed with this, Wader obtains all the
serial ports associated with this device, and builds a ``DevicePlugin``
out of it.

Wader will emit a ``DeviceAdded`` :term:`DBus` signal when a new 3G device
has been added, and a ``DeviceRemoved`` signal when a 3G device has been
removed.

As mentioned above, the method
``org.freedesktop.ModemManager.EnumerateDevices`` returns an array of object
paths, one for each device found in the system::

    dbus-send --system --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/ModemManager org.freedesktop.ModemManager.EnumerateDevices
    method return sender=:1.156 -> dest=:1.155 reply_serial=2
       array [
          object path "/org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial"
          object path "/org/freedesktop/Hal/devices/pci_1931_c"
          object path "/org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial_0"
       ]

This is the response of ``EnumerateDevices`` with a Huawei E172, an E870 and an
Option GlobeTrotter 3G+ (Nozomi). Wader is able to detect, configure and use the
three at the same time with no interference between them whatsoever.

Operations you might want to do on a device
===========================================

Once your device is set up, you will probably want to register with a given
operator, or perhaps letting Wader to choose itself? Perhaps you want to do a
high-level operation such as configuring the band and connection mode? We are
going to provide examples for every one of them:

Registering to a network
++++++++++++++++++++++++

Registering to a network will not be necessary most of the time as the
devices themselves will register to its home network. Manually specifying
a :term:`MNC` to connect to an arbitrary network is possible, though::

    dbus-send --type=method_call --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1001_HUAWEI_DEVICE \
        org.freedesktop.ModemManager.Modem.Gsm.Network.Register string:21401
    method return sender=:1.193 -> dest=:1.193 reply_serial=2

It is also possible to pass an empty string, and that will register to the
home network::

    dbus-send --system --dest=org.freedesktop.ModemManager --print-reply \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Network.Register string:
    method return sender=:1.193 -> dest=:1.195 reply_serial=2

    dbus-send --system --dest=org.freedesktop.ModemManager --print-reply \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Network.GetRegistrationInfo
    method return sender=:1.193 -> dest=:1.196 reply_serial=2
       struct {
          uint32 1
          string "21401"
          string "vodafone ES"
       }

The :term:`MNC` ``21401`` is Vodafone Spain's MNC, my current network
provider. If I try to connect to Telefonica's :term:`MNC` ``21407``, the
operation will probably horribly fail::

    dbus-send --type=method_call --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1001_HUAWEI_DEVICE \
        org.freedesktop.ModemManager.Modem.Gsm.Network.Register string:21407
    method return sender=:1.193 -> dest=:1.197 reply_serial=2

Oops, it didn't fail :). Although if I try to connect to Internet it will
fail for sure as the APN is completely different.

Configuring connection settings
+++++++++++++++++++++++++++++++

You might be interested on changing the connection mode from 2G to 3G. Or
perhaps you are interested on changing from `GSM1900` to `GSM850` if you are
roaming. Whatever your needs are, you are looking for the
``org.freedesktop.ModemManager.Modem.Gsm.Network.SetBand`` and
``org.freedesktop.ModemManager.Modem.Gsm.Network.SetNetworkMode``
methods. This methods and their parameters are thoroughly described in
:term:`ModemManager`'s excellent API.

Sending a SMS
+++++++++++++

Sending a SMS can not be any easier::

    from wader.common.sms import Message

    ...

    def sms_cb(indexes): print "SMS sent spanning", indexes
    def sms_eb(e): print "Error sending SMS", e

    sms = Message("+34606575119", "hey dude")
    device.Send(sms.to_dict(),
                dbus_interface=consts.SMS_INTFACE,
                reply_handler=sms_cb,
                error_handler=sms_eb)

And sending an UCS2 encoded SMS can't get any easier either::

    from wader.common.sms import Message

    ...

    def sms_cb(indexes): print "SMS sent spanning", indexes
    def sms_eb(e): print "Error sending SMS", e

    sms = Message("+34606575119", "àèìòù")
    device.Send(sms.to_dict(),
                dbus_interface=consts.SMS_INTFACE,
                reply_handler=sms_cb,
                error_handler=sms_eb)

Adding/Reading a Contact
++++++++++++++++++++++++

Adding a contact to the SIM and getting the index where it was stored::

    dbus-send --system --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Contacts.Add string:Pablo string:+34545665655
    method return sender=:1.54 -> dest=:1.57 reply_serial=2
       uint32 1

And reading it again::

    dbus-send --system --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Contacts.Get uint32:1
    method return sender=:1.54 -> dest=:1.58 reply_serial=2
       struct {
          uint32 1
          string "Pablo"
          string "+34545665655"
       }

Now lets add another contact and read all the contacts in the SIM card::

    dbus-send --system --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Contacts.Add string:John string:+33546657784
    method return sender=:1.54 -> dest=:1.60 reply_serial=2
       uint32 2
    dbus-send --system --print-reply --dest=org.freedesktop.ModemManager \
        /org/freedesktop/Hal/devices/usb_device_12d1_1003_noserial \
        org.freedesktop.ModemManager.Modem.Gsm.Contacts.List
    method return sender=:1.54 -> dest=:1.61 reply_serial=2
       array [
          struct {
             uint32 1
             string "Pablo"
             string "+34545665655"
          }
          struct {
             uint32 2
             string "John"
             string "+33546657784"
          }
       ]

Data calls
==========

Connecting to the Internet just requires knowing the UDI of a device with
modem capabilities and a profile. While the former is obtained through
a ``FindDeviceByCapability("modem")``, the latter requires to create it
explicitly. Be it through Wader or :term:`NetworkManager`, a profile is
required.

Profile creation
++++++++++++++++

Profiles in Wader, known as connections in :term:`NetworkManager` lingo, are
stored using the `GConf`_ configuration system. When a new profile is
written to gconf, a new profile -or connection- is created and exported
on :term:`DBus`. When the profile is ready to be used, a ``NewConnection``
signal is emitted with the profile object path as its only argument.

.. _GConf: http://projects.gnome.org/gconf/

Connecting
++++++++++

Armed with the object paths of the profile and device to use, we just
need to pass this two arguments to
:meth:`~wader.common.dialer.DialerManager.ActivateConnection`. Under the
hood this method will perform the following:

- Get a :class:`~wader.common.dialer.Dialer` instance for this device. If
  :term:`NetworkManager` 0.7.1+ is present, it will use
  :class:`~wader.common.dialers.nm_dialer.NMDialer`, if the device happens
  to be an HSO device it will use
  :class:`~wader.common.dialers.hsolink.HSODialer`, otherwise it will just
  use :class:`~wader.common.dialers.wvdial.WVDialDialer`.
- Configure the given device with the profile settings. If the profile
  specifies a band or a network mode, the band or network mode will be set
  through ``SetBand`` and ``SetNetworkMode``. After waiting a couple of
  seconds so the device can settle, the actual connection process will be
  started.
- The dialer will obtain from the profile the needed settings to connect:
  apn, username, whether DNS should be static or not, etc. Obtaining the
  password associated with a profile is a different story though. Passwords
  are stored in `gnome-keyring-daemon` through the :class:`gnomekeyring`
  module, every profile has an :term:`UUID` that identifies it uniquely. All
  this is abstracted in the module :class:`~wader.gtk.secrets`.

If ``ActivateConnection`` succeeds, it will return the object path of the
connection, connections are identified by it and its required to save
somewhere this object path to stop the connection later on.

Disconnecting
+++++++++++++

Disconnecting could not be easier, you just need to pass the object path
returned by ``ActivateConnection`` to
:meth:`~wader.common.dialer.DialerManager.DeactivateConnection`. This will
deallocate all the resources allocated by ``ActivateConnection``.

Troubleshooting
===============

Operation X failed on my device
+++++++++++++++++++++++++++++++

Every device its a world on its own, sometimes they are shipped with a buggy
firmware, sometimes a device will reply to a command on a slightly different
way that will break the parsing of the reply.

Wader ships with a test suite that might yield some clues about what went
wrong. Instructions to execute it::

    trial -r gtk2 wader.test

Do not forget the :option:`-r gtk2` switch, it will pick the `gtk2` reactor
to run the tests, otherwise all the glib-dependent tests, like the
:meth:`DBus` ones will fail.

.. note::

   Since Wader migrated to a DBus architecture, the tests related to the
   device or DBus no longer work. We think that this was introduced in
   trial, the tool that the twisted framework provides to run unit tests. So
   for now those tests are broken, the goal is to bring them back to life
   around the 0.4.0 release.

