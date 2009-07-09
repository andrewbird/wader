How to add support for a new distro/OS
======================================

How to add support for a new distro
+++++++++++++++++++++++++++++++++++

Adding support for a new distro is relatively straightforward, it basically
boils down to:

- Inheriting from :class:`~wader.common.oses.linux.LinuxPlugin`.
- Implementing the ``is_valid`` method. This will return True if we are in
  the given OS/Distro and False otherwise. Usually you will just need to
  check for a well known file that your distro or OS ships with.
- Implement the ``get_timezone`` method. This method returns a string with
  the timezone name (i.e. "Europe/Madrid"). Implementing this method is not
  strictly necessary, and Wader can start up without it, but your SMS dates
  will probably be off by some hours.

Lets have a look at the Fedora plugin:

.. literalinclude:: ../../plugins/oses/fedora.py
    :lines: 21-

As we can see, the Fedora plugin just defines ``is_valid`` and provides an
implementation for ``get_timezone``.

How to add support for a new OS
+++++++++++++++++++++++++++++++

Adding support for a new OS is not as easy as the previous point. You need to
add a new os class to ``wader.common.oses`` with a working
implementation for the following methods/objects:

- ``get_iface_stats``: Accepts just one parameter, the iface name, and
  returns a tuple with tx,rx bytes.
- ``is_valid``: Returns True if the plugin is valid in the context where is
  being run, otherwise returns False.
- ``hw_manager``: A instance of a class that implements the
  :class:`~wader.common.interfaces.IHardwareManager` interface.

