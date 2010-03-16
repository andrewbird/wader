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
"""
setuptools file for Wader
"""

from os.path import join, isdir, walk
import sys

from ez_setup import use_setuptools
use_setuptools()
from distutils.core import Extension
from setuptools import setup

from wader.common.consts import (APP_VERSION, APP_NAME,
                                 APP_SLUG_NAME)

DATA_DIR = '/usr/share/%s' % APP_SLUG_NAME
BIN_DIR = '/usr/bin'
RESOURCES = join(DATA_DIR, 'resources')
DBUS_SYSTEMD = '/etc/dbus-1/system.d'
DBUS_SYSTEM_SERVICES = '/usr/share/dbus-1/system-services'
UDEV_RULESD = '/etc/udev/rules.d'


def list_files(path, exclude=None):
    result = []

    def walk_callback(arg, directory, files):
        for ext in ['.svn', '.git']:
            if ext in files:
                files.remove(ext)
        if exclude:
            for f in files:
                if f.startswith(exclude):
                    files.remove(f)
        result.extend(join(directory, f) for f in files
                      if not isdir(join(directory, f)))

    walk(path, walk_callback, None)
    return result

data_files = [
   (join(RESOURCES, 'extra'), list_files('resources/extra')),
   (join(RESOURCES, 'config'), list_files('resources/config')),
   (join(DATA_DIR, 'plugins'), list_files('plugins')),
   (DATA_DIR, ['core-tap.py']),
   (BIN_DIR, ['bin/wader-core-ctl']),
]

ext_modules = []

if sys.platform == 'linux2':
    append = data_files.append
    append((DBUS_SYSTEMD,
            ['resources/dbus/org.freedesktop.ModemManager.conf']))
    append((DBUS_SYSTEM_SERVICES,
            ['resources/dbus/org.freedesktop.ModemManager.service']))
    append((UDEV_RULESD, list_files('resources/udev')))

elif sys.platform == 'darwin':
    osxserialports = Extension('osxserialports',
                            sources=['contrib/osxserialports/osxserialportsmodule.c'],
                            extra_link_args=['-framework', 'CoreFoundation',
                                             '-framework', 'IOKit'])
    ext_modules.append(osxserialports)

packages = [
    'wader', 'wader.common', 'wader.common.oses', 'wader.common.backends',
    'wader.common.statem', 'wader.common.hardware', 'wader.contrib',
    'wader.test', 'wader.plugins'
]

setup(name=APP_NAME,
      version=APP_VERSION,
      description='3G device manager for Linux and OSX',
      download_url="http://www.wader-project.org",
      author='Pablo Martí Gamboa',
      author_email='pmarti@warp.es',
      license='GPL',
      packages=packages,
      data_files=data_files,
      ext_modules=ext_modules,
      zip_safe=False,
      test_suite='wader.test',
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Topic :: Communications :: Telephony',
      ]
)
