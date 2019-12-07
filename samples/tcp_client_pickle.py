#!/usr/bin/python

"""
Derived from sample_tcp_client, this application pickles arbitrary Python
objects and sends them to the server.  The input into the application is passed
to eval() to turn into an object, one line each.
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run, stop
from bacpypes.comm import PDU, Client, Server, bind, ApplicationServiceElement
from bacpypes.tcp import TCPClientDirector, TCPPickleClientActor

from bacpypes.console import ConsoleClient

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
server_addr = ('127.0.0.1', 9000)
director = None
middle_man = None

#
#   MiddleMan
#

class MiddleMan(Client, Server, Logging):

    def __init__(self):
        if _debug: MiddleMan._debug("__init__")
        Client.__init__(self)
        Server.__init__(self)

        # not connected
        self.connected = False

    def indication(self, pdu):
        if _debug: MiddleMan._debug('indication %r (connected %r)', pdu, self.connected)

        # no data means EOF, stop
        if not pdu.pduData:
            if _debug: MiddleMan._debug('    - flushing')

            # get the actor and tell it to flush and close
            director.get_actor(server_addr).flush()
            stop()
            return

        # empty lines are ignored
        if pdu.pduData == '\n':
            return

        # turn it into something to pickle
        try:
            data = eval(pdu.pduData[:-1])
            if _debug: MiddleMan._debug('    - data: %r', data)
        except Exception, err:
            if _debug: MiddleMan._debug("eval exception: %r", err)
            return

        self.request(PDU(data, destination=server_addr))

    def confirmation(self, pdu):
        if _debug: MiddleMan._debug('confirmation %r', pdu)

        # turn it back into something to print
        data = repr(pdu.pduData) + '\n'

        self.response(PDU(data))

    def set_connected(self):
        """The slave has connected to the master."""
        if _debug: MiddleMan._debug("set_connected")
        
        # good to go
        self.connected = True
        
    def set_disconnected(self):
        """The slave is disconnected from the master."""
        if _debug: MiddleMan._debug("set_disconnected")

        # no longer connected
        self.connected = False

    def terminate(self):
        if _debug: MiddleMan._debug("terminate")

#
#   ConnectionASE
#

class ConnectionASE(ApplicationServiceElement, Logging):

    def indication(self, *args, **kwargs):
        if _debug: ConnectionASE._debug('ConnectionASE.indication %r %r', args, kwargs)

        if 'addPeer' in kwargs:
            if _debug: ConnectionASE._info("    - add peer %s", kwargs['addPeer'])
            middle_man.set_connected()

        if 'delPeer' in kwargs:
            if _debug: ConnectionASE._info("    - delete peer %s", kwargs['delPeer'])
            middle_man.set_disconnected()

#
#   __main__
#

try:
    # parse the command line arguments
    args = ArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")

    console = ConsoleClient()
    middle_man = MiddleMan()
    director = TCPClientDirector(timeout=10, actorClass=TCPPickleClientActor)
    bind(console, middle_man, director)
    bind(ConnectionASE(), director)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

