# -*- coding: utf-8 -*-
# Copyright (C) 1995-2007  Tummy.com, Ltd.
# Copyright (C) 2008-2009  Warp Networks, S.L.
#
# Imported for the wader project on 5 June 2008 by Pablo Martí
#
# Author:  Sean Reifschneider
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
#
# This module was fetched from ftp://ftp.tummy.com/pub/tummy/Python/tail.py
# on 15 Jan 2009 by Pablo Marti. Being the TPL a GPL-compatible license,
# I'm redistributing this under the GPLv2.
#
# PabloMarti 15/01/2009:
#     PEP-8'ed the module
#     get rid of the mainloop and __main__ functions
"""
A module which implements a unix-like "tail" of a file.

A callback is executed for every new line found in the file.
"""

import os

class Tail(object):
    """I periodically poll a file and will execute a callback if changed"""

    def __init__(self, filename, callback, tailbytes=0):
        """
        Create a Tail object which periodically polls the specified file looking
        for new data which was written. The callback routine is called for each
        new line found in the file.

        @param filename: File to read.
        @param callback: Executed for every line read
        @param tailbytes: Specifies bytes from end of file to start reading
        """
        super(Tail, self).__init__()
        self.skip = tailbytes
        self.filename = filename
        self.callback = callback
        self.fp = None
        self.last_size = 0
        self.last_inode = -1
        self.data = ''

    def close(self):
        """
        Closes the monitored file and cleans up
        """
        self.fp.close()
        self.fp = None
        self.data = ''

    def process(self):
        """
        Examine file looking for new lines.

        When called, this function will process all lines in the file being
        tailed, detect the original file being renamed or reopened, etc.
        """
        # open file if it's not already open
        if not self.fp:
            try:
                self.fp = open(self.filename, 'r')
                stat = os.stat(self.filename)
                self.last_inode = stat[1]

                if self.skip >= 0 and stat[6] > self.skip:
                    self.fp.seek(0 - (self.skip), 2)

                self.skip = -1
                self.last_size = 0
            except (IOError, OSError):
                if self.fp:
                    self.fp.close()
                self.skip = -1 # if the file doesn't exist, we don't skip
                self.fp = None

        if not self.fp:
            return

        # check to see if file has moved under us
        try:
            stat = os.stat(self.filename)
            this_size = stat[6]
            this_ino = stat[1]
            if this_size < self.last_size or this_ino != self.last_inode:
                raise IOError("File has changed")
        except OSError:
            self.close()
            return

        # read if size has changed
        if self.last_size < this_size:
            while 1:
                data = self.fp.read(4096)
                if not len(data):
                    break

                self.data += data

                # process lines within the data
                while 1:
                    pos = self.data.find('\n')
                    if pos < 0:
                        break
                    line = self.data[:pos]
                    self.data = self.data[pos + 1:]
                    # line is line read from file
                    self.callback(line)

        self.last_size = this_size
        self.last_inode = this_ino

        return True

