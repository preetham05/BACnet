#!/usr/bin/python

"""
sample023-bbmd.py
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.bvllservice import UDPMultiplexer, AnnexJCodec, BIPBBMD
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   TestBBMD
#

@bacpypes_debugging
class TestBBMD(BIPBBMD):

    def __init__(self, addr):
        if _debug: TestBBMD._debug("TestBBMD %r", addr)
        BIPBBMD.__init__(self, addr)

        # save the address
        self.address = addr

        # make the lower layers
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.address)

        # bind the bottom layers
        bind(self, self.annexj, self.mux.annexJ)

        # give this a generic network layer service access point and element
        self.nsap = NetworkServiceAccessPoint()
        self.nse = NetworkServiceElement()
        self.nsap.bind(self)
        bind(self.nse, self.nsap)

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

    _log.debug("initialization")

    # read in a configuration file
    config = ConfigParser()
    if ('--ini' in sys.argv):
        indx = sys.argv.index('--ini')
        ini_file = sys.argv[indx + 1]
        if not config.read(ini_file):
            raise RuntimeError, "configuration file %r not found" % (ini_file,)
        del sys.argv[indx:indx+2]
    elif not config.read('BACpypes.ini'):
        raise RuntimeError, "configuration file not found"

    # get the address from the config file
    addr = config.get('BACpypes', 'address')

    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        addr += ':' + sys.argv[i+1]
    _log.debug("    - addr: %r", addr)

    # create the BBMD stack
    bbmd = TestBBMD(addr)

    # add a peer, probably should come from the configuration file
    # bbmd.add_peer(Address("1.2.3.4"))

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
