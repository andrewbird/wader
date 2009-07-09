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
"""Module to obtain an introspection shell"""

from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh

def get_manhole_factory(namespace, **passwords):
    """
    Returns a ``ConchFactory`` instance configured with given settings

    :param namespace: The namespace to use
    :param passwords: The passwords to use
    :rtype: `twisted.conch.manhole_ssh.ConchFactory`
    """
    realm = manhole_ssh.TerminalRealm()
    def getManhole(_):
        return manhole.Manhole(namespace)
    realm.chainedProtocolFactory.protocolFactory = getManhole
    p = portal.Portal(realm)
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(**passwords)
    p.registerChecker(checker)
    f = manhole_ssh.ConchFactory(p)
    return f

