==============
Wader overview
==============

Introduction
============

Wader is a 3G device manager daemon written in Python and tested on Linux and
MacOS X (10.5 with recent `MacPorts`_).

Some of its features are:

- Pluggable architecture that can be extended by plugins
- Make mobile data connections over the network
- Manage your SIM contacts and SMS
- Operator-agnostic
- Implements the :term:`ModemManager` API. Thus writing a device plugin for Wader
  means that your device will work with the *de-facto* tool for managing
  networks
- Service actionable via :term:`DBus`

.. _MacPorts: http://www.macports.org/

History
=======

`Warp Networks`_ developed `Vodafone Mobile Connect Card driver for Linux`_
for `Vodafone Spain R&D`_ between late 2006 and early 2008.

When the project ended, we realized that there were some parts of the
application, like the core, that were pretty good and potentially useful for
other applications of the Linux/Unix desktop ecosystem that wanted to
interact with 3G devices.

So Warp decided to fork it, rewrite some dodgy spots and export all its juicy
bits over :term:`DBus`, which was the missing piece in order to be able to
talk with other applications of the Linux desktop. The project needed a new
name and we chose `Wader`_ for it.

.. _Warp Networks: http://www.warp.es/
.. _Vodafone Mobile Connect Card driver for Linux: http://www.betavine.net/web/linux_drivers/
.. _Vodafone Spain R&D: http://www.vodafone.es/
.. _Wader: http://www.wader-project.org/


