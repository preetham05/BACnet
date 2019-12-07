#!/usr/bin/python

"""
This simple TCP server application listens for one or more client connections
and echos the incoming lines back to the client.  There is no conversion from 
incoming streams of content into a line or any other higher-layer concept
of a packet.
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run
from bacpypes.comm import PDU, Client, bind, ApplicationServiceElement
from bacpypes.tcp import TCPServerDirector

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
server_addr = ('127.0.0.1', 9000)
director = None

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
            if _debug: ConnectionASE._debug("    - add peer %s", kwargs['addPeer'])
            
        if 'delPeer' in kwargs:
            if _debug: ConnectionASE._debug("    - delete peer %s", kwargs['delPeer'])

        if _debug: ConnectionASE._debug('    - director.servers: %r', director.servers)

#
#   __main__
#

try:
    # parse the command line arguments
    args = ArgumentParser(description=__doc__).parse_args()

    _log.debug("initialization")

    # create a director listening to the address
    director = TCPServerDirector(server_addr)

    # create an echo
    echo_master = EchoMaster()

    # bind everything together
    bind(echo_master, director)
    bind(ConnectionASE(), director)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

