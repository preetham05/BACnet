#!/usr/bin/python

"""
sample_tcp_r2r_client
"""

import sys
import os

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run, deferred
from bacpypes.comm import bind

from bacpypes.pdu import Address
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import UDPMultiplexer, AnnexJCodec, BIPSimple
from bacpypes.bsllservice import TCPClientMultiplexer, RouterToRouterService

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_router = None

#
#   TestRouter
#

class TestRouter(Logging):

    def __init__(self, localNetwork, localAddress):
        if _debug: TestRouter._debug("__init__ %r", localAddress)

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)
        
        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(localAddress)

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to localNetwork
        self.nsap.bind(self.bip, localNetwork, localAddress)

        # create a multiplexer for the service
        self.mux = TCPClientMultiplexer()

        # create the service, use 90 as the "hidden" network
        self.r2rService = RouterToRouterService(self.mux, self.nsap, 90)

#
#   __main__
#

try:
    if ('--buggers' in sys.argv):
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            sys.stdout.write(loggerName + '\n')
        sys.exit(0)

    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        i = indx + 1
        while (i < len(sys.argv)) and (not sys.argv[i].startswith('--')):
            ConsoleLogHandler(sys.argv[i])
            i += 1
        del sys.argv[indx:i]

    if ('--config' in sys.argv):
        indx = sys.argv.index('--config')
        configFileName = sys.argv[indx+1]
        del sys.argv[indx:indx+2]
    else:
        configFileName = 'BACpypes.ini'

    _log.debug("initialization")

    # read in the configuration file
    if not os.path.isfile(configFileName):
        raise RuntimeError, "No config file: '%s'" % (configFileName,)
    config = ConfigParser()
    config.read(configFileName)

    # get the address
    addr = config.get('BACpypes', 'address')

    # maybe use a different port
    if '--port' in sys.argv:
        indx = sys.argv.index('--port')
        addr += ':' + sys.argv[indx+1]
        del sys.argv[indx:indx+2]
    _log.debug("    - addr: %r", addr)

    # make a simple router
    this_router = TestRouter(91, Address(addr))

    # get the address of the server
    server_address = Address(sys.argv[1])
    _log.debug("    - server_address: %r", server_address)

    # attempt to connect (deferred until sockets are ready)
    deferred(this_router.r2rService.Connect, server_address)

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
