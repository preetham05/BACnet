#!/usr/bin/python

"""
This simple TCP client application opens a connection to the server and sends
each line as a PDU.  This may end up with more than one TCP data message on the
wire.
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run, stop
from bacpypes.comm import PDU, Client, Server, bind, ApplicationServiceElement
from bacpypes.tcp import TCPClientDirector

from bacpypes.console import ConsoleClient

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
server_addr = ('127.0.0.1', 9000)

console = None
middle_man = None
director = None

#
#   MiddleMan
#

class MiddleMan(Client, Server, Logging):

    def indication(self, pdu):
        if _debug: MiddleMan._debug('indication %r', pdu)

        # no data means EOF, stop
        if not pdu.pduData:
            director.disconnect(server_addr)
            return

        # pass it along
        self.request(PDU(pdu.pduData, destination=server_addr))

    def confirmation(self, pdu):
        if _debug: MiddleMan._debug('confirmation %r', pdu)

        # pass it along
        self.response(pdu)

#
#   ConnectionASE
#

class ConnectionASE(ApplicationServiceElement, Logging):

    def indication(self, *args, **kwargs):
        if _debug: ConnectionASE._debug('ConnectionASE.indication %r %r', args, kwargs)

        if 'addPeer' in kwargs:
            if _debug: ConnectionASE._debug("    - add peer %s", kwargs['addPeer'])

        if 'delPeer' in kwargs:
            if _debug: ConnectionASE._debug("    - delete peer %s", kwargs['delPeer'])

        if _debug: ConnectionASE._debug('    - director.clients: %r', director.clients)
        if not director.clients:
            stop()

#
#   __main__
#

try:
    # parse the command line arguments
    args = ArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")

    console = ConsoleClient()
    middle_man = MiddleMan()
    director = TCPClientDirector()
    bind(console, middle_man, director)
    bind(ConnectionASE(), director)

    # don't wait to connect
    director.connect(server_addr)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

