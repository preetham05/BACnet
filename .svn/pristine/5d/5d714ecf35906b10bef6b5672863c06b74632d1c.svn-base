#!/usr/bin/python

"""
sample_tcp_proxy
"""

import sys
import os

from ConfigParser import ConfigParser

from bacpypes.debugging import ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address

from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import UDPMultiplexer, AnnexJCodec, BIPSimple
from bacpypes.bsllservice import TCPClientMultiplexer, ProxyClientService, UserInformation

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   Test User
#

test_user = UserInformation(
    username='Joel',
    password='P@ssw0rd',
    allServices=True,
    )

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

    # maybe use a different port
    addr = config.get('BACpypes', 'address')
    if '--port' in sys.argv:
        indx = sys.argv.index('--port')
        addr += ':' + sys.argv[indx+1]
        del sys.argv[indx:indx+2]
    _log.debug("    - addr: %r", addr)

    # a network service access point will be needed
    nsap = NetworkServiceAccessPoint()

    # give the NSAP a generic network layer service element
    nse = NetworkServiceElement()
    bind(nse, nsap)

    # create a generic BIP stack, bound to the Annex J server on the UDP multiplexer
    bip = BIPSimple()
    annexj = AnnexJCodec()
    udpmux = UDPMultiplexer(Address(addr))

    # we need a way to make outgoing TCP connections and manage the proxy client service state
    tcpmux = TCPClientMultiplexer()

    # get the address of the server
    server_address = Address(sys.argv[1])
    _log.debug("    - server_address: %r", server_address)

    # create a ProxyClientService
    proxy_client = ProxyClientService(tcpmux, server_address, testUser)

    # bind everything together
    bind(proxy_client, bip, annexj, udpmux.annexJ)

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

