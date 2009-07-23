===================================
How to add support for a new device
===================================

How to support a new device
===========================

All devices should inherit from :class:`~wader.common.middleware.WCDMAWrapper`
in order to override its base methods. It accepts two argument for
its constructor, an instance or subclass of
:class:`~wader.common.plugin.DevicePlugin` and the udi of the device to use.

A DevicePlugin contains all the necessary information to speak with
the device: a data port, a control port (if exists), a baudrate, etc.
It also has the following attributes and members that you can
customise for your device plugin:

- ``custom``: An instance or subclass of
  :class:`wader.common.hardware.base.WCDMACustomizer`. See bellow.
- ``sim_klass``: An instance or subclass of
  :class:`wader.common.sim.SIMBaseClass`.
- ``baudrate``: At what speed are we going to talk with this device
  (default 115200).
- ``__remote_name__``: As some devices share the same vendor and product ids,
  we will issue an `AT+GMR` command right at the beginning to find out the
  real device model. Set this attribute to whatever your device replies to the
  `AT+GMR` command.
- ``mapping``: A dictionary that, when is not empty, means that that
  particular combination of vendor and product ids is shared between several
  models from the same company. As the ids are the same, the only way to
  differentiate them is issuing an `AT+GMR` command to get the device model.
  This dict must have an entry for each model and a `default` entry that
  will be used in cases where we do not know about the card model. For more
  information about the mapping dictionary, have a look at the module
  :class:`wader.common.plugins.huawei_exxx`.

The object :class:`wader.common.hardware.base.WCDMACustomizer` acts as a
container for all the device-specific customizations such as:

- ``wrapper_klass``: Specifies the class that will be used to wrap the
  `Device` object. Used in situations where the default commands supplied
  by :class:`wader.common.middleware.WCDMAWrapper` are not enough:
  (i.e. devices with "interesting" firmwares). Some of its commands may
  need an special parsing or an specific workaround.
- ``exporter_klass``: Specifies the class that will export the wrapper
  methods over :term:`DBus`.
- State Machines: Each device its a world on its own, and even though they
  are supposed to support the relevant GSM and 3GPP standards, some devices
  prefer to differ from them. The `custom` object contains references to
  the state machines that the device should use, (on situations where it
  applies, such as with WCDMA devices of course):

  - ``auth_klass``: The state machine used to authenticate against the device,
    default is :class:`wader.common.statem.auth.AuthStateMachine`.
  - ``netr_klass``: The state machine used to register on the network, default
    is :class:`wader.common.statem.networkreg.NetworkRegistrationStateMachine`.
  - ``simp_klass``: The *simple* state machine specified by
    :term:`ModemManager` v0.2. This state machine basically comprises the
    previous two on a single (and simpler) one.

- ``async_regexp``: regular expression object that will match whatever pattern
  of unsolicited notifications the given device sends us.
- ``signal_translations``: Dictionary of tuples, each tuple has two members:
  the first is the signal id and the second is a function that will translate
  the signal arguments and the signal to the internal representation that Wader
  uses. You can find some sample code in the
  :class:`~wader.common.hardware.huawei` module. If a notification should be
  ignored, then add it as a key like the rest, but its value should be a
  tuple ``(None, None)``.
- ``band_dict``: Dictionary with the different bands supported by the device.
  The keys will *always* be a `MM_NETWORK_BAND_FOO` and the value is up to the
  implementor. You can see the supported bands in the
  :mod:`~wader.common.consts` module.
- ``conn_dict``: Dictionary with the different network modes supported by the
  device. The keys will *always* be a `MM_NETWORK_MODE_FOO` and the value is
  up to the implementor. You can see the supported network modes in the
  :mod:`~wader.common.consts` module.
- ``cmd_dict``: Dictionary with information about how each command should be
  processed. ``cmd_dict`` most of the time will be a shallow copy of the
  :class:`~wader.common.command` dict with minor modifications about how a
  particular command is processed on the given device.
- ``device_capabilities``: List with all the unsolicited notifications that
  this device will send us. If the device sends us every RSSI change that
  detects, we don't need to poll manually the device for that information.


Overview of a simple DevicePlugin
=================================

Lets have a look at the NovatelXU870 plugin:

.. literalinclude:: ../../plugins/devices/novatel_xu870.py
    :lines: 18-

In an ideal world, devices have a unique vendor and product id tuple, they
conform to the relevant CDMA or WCDMA specs, and that's it. The device is
identified by its vendor and product ids and double-checked with its
`__remote_name__` attribute (the response to an `AT+GMR` command).
This vendor and product id tuple will usually use the `usb` bus, however
some devices might end up attached to the ``pci`` or `pcmcia` buses. The
last line in the plugin will create an instance of the plugin in wader's
plugin system -otherwise it will not be found!.

Overview of a *relatively* simple DevicePlugin
==============================================

Take for example the HuaweiE620 class:

.. literalinclude:: ../../plugins/devices/huawei_e620.py
    :lines: 19-

The E620 plugin is identical to the XU870 except one small difference
regarding the parsing of the `get_roaming_ids` command. The E620 omits
some information that other devices do output, and the regular expression
object that parses it has to be updated. We get a new copy of the
`cmd_dict` dictionary attribute and modify it with the new regexp the
`get_roaming_ids` entry. The new `cmd_dict` is specified in its
Customizer object.

Overview of a not so simple DevicePlugin
========================================

.. literalinclude:: ../../plugins/devices/huawei_e220.py
    :lines: 19-

Huawei's E220, despite sharing its manufacturer with the E620, has a couple
of minor differences that deserve some explanation. There's a bug in its
firmware that will reset the device if you ask its SMSC. The workaround is
to get once the SMSC before switching to UCS2, you'd be amazed of how long
took me to discover the fix. The second difference with the E620 is that
the E220 can have several product_ids, thus its product_id list has two
elements.

Overview of a complex DevicePlugin
==================================

.. literalinclude:: ../../plugins/devices/option_colt.py
    :lines: 24-

This data card is the buggiest card we've found so far, and has proven to be
an excellent challenge for the extensibility and granularity of our plugin
system. Basically we've found the following bugs on the card's firmware:

- If PIN authentication is disabled and you issue an `AT+CPIN?`, the card
  will reply with a `+CPIN: SIM PUK2`.
- Don't ask me why, but `AT+CPBR=1,250` does not work once the application
  is running. I have tried replacing the command with an equivalent one
  (`AT+CPBF=""`) without luck.

So we had to modify the AuthStateMachine for this particular device and its
`cmd_dict`.

