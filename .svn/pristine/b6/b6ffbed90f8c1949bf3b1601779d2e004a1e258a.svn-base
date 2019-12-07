#!/usr/bin/python

"""
Derived from sample_tcp_server, this application echos arbitrary Python
objects received by connected clients.  At the application layer, the incoming
stream of content has already been converted into Python objects so it can be
sent back down the stack where it will be re-pickled before being streamed
back to the client.
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run
from bacpypes.comm import PDU, Client, bind, ApplicationServiceElement
from bacpypes.tcp import TCPServerDirector, TCPPickleServerActor

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
server_addr = ('127.0.0.1', 9000)

#
#   EchoMaster
#

class EchoMaster(Client, Logging):

    def confirmation(self, pdu):
        if _debug: EchoMaster._debug('confirmation %r', pdu)

        self.request(PDU(pdu.pduData, destination=pdu.pduSource))

#
#   ConnectionASE
#

class ConnectionASE(ApplicationServiceElement, Logging):

    def indication(self, *args, **kwargs):
        if _debug: ConnectionASE._debug('indication %r %r', args, kwargs)

        if 'addPeer' in kwargs:
            if _debug: ConnectionASE._info("    - add peer %s", kwargs['addPeer'])

        if 'delPeer' in kwargs:
            if _debug: ConnectionASE._info("    - delete peer %s", kwargs['delPeer'])

#
#   __main__
#

try:
    # parse the command line arguments
    args = ArgumentParser(description=__doc__).parse_args()

    _log.debug("initialization")

    director = TCPServerDirector(server_addr, actorClass=TCPPickleServerActor)
    echo_master = EchoMaster()
    bind(echo_master, director)
    bind(ConnectionASE(), director)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

