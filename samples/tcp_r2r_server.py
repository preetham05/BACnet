#!/usr/bin/python

"""
sample_tcp_r2r_server
"""

import sys
import os

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import LocalDeviceObject, Application, ApplicationServiceAccessPoint, StateMachineAccessPoint
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import UDPMultiplexer, AnnexJCodec, BIPSimple
from bacpypes.bsllservice import TCPServerMultiplexer, RouterToRouterService

from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_device = None
this_application = None
this_console = None

#
#   TestApplication
#

class TestApplication(Application, Logging):

    def __init__(self, localDevice, localAddress, aseID=None):
        if _debug: TestApplication._debug("__init__ %r %r aseID=%r", localDevice, localAddress, aseID)
        Application.__init__(self, localDevice, localAddress, aseID)
        
        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()
        
        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(localDevice)
        
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)
        
        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)

        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress)

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to network 5, the 'local' network
        self.nsap.bind(self.bip, 5, self.localAddress)

        # create a multiplexer for the service
        self.mux = TCPServerMultiplexer(self.localAddress)

        # create the service, use 90 as the "hidden" network
        self.r2rService = RouterToRouterService(self.mux, self.nsap, 90)

    def request(self, apdu):
        if _debug: TestApplication._debug("Request %r", apdu)
        Application.Request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("Confirmation %r", apdu)

#
#   TestConsoleCmd
#

class TestConsoleCmd(ConsoleCmd, Logging):

    def do_whois(self, args):
        """whois [ <addr> ] [ <lolimit> <hilimit> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_whois %r", args)

        try:
            # build a request
            request = WhoIsRequest()
            if (len(args) == 1) or (len(args) == 3):
                request.pduDestination = Address(args[0])
                del args[0]
            else:
                request.pduDestination = GlobalBroadcast()

            if len(args) == 2:
                loLimit = int(args[0])
                hiLimit = int(args[1])

                request.deviceInstanceRangeLowLimit = int(args[0])
                request.deviceInstanceRangeHighLimit = int(args[1])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)
        
            # give it to the application
            this_application.Request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_iam(self, args):
        """iam [ <addr> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_iam %r", args)

        try:
            # build a request
            request = IAmRequest()
            if (len(args) == 1):
                request.pduDestination = Address(args[0])
                del args[0]
            else:
                request.pduDestination = GlobalBroadcast()
            
            # set the parameters from the device object
            request.iAmDeviceIdentifier = this_device.objectIdentifier
            request.maxAPDULengthAccepted = this_device.maxApduLengthAccepted
            request.segmentationSupported = this_device.segmentationSupported
            request.vendorID = this_device.vendorIdentifier
            TestConsoleCmd._debug("    - request: %r", request)
            
            # give it to the application
            this_application.Request(request)
            
        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_read(self, args):
        """read <addr> <type> <inst> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            addr, objType, objInst, propId = args[:4]
            if objType.isdigit():
                objType = int(objType)
            objInst = int(objInst)

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=(objType, objInst),
                propertyIdentifier=propId,
                )
            request.pduDestination = Address(addr)
            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)
                
            # give it to the application
            this_application.Request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_nsap(self, args):
        """nsap"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_nsap %r", args)

        this_application.nsap.DebugContents()

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

    # make a device object
    this_device = LocalDeviceObject(
        objectName=config.get('BACpypes','objectName'),
        objectIdentifier=config.getint('BACpypes','objectIdentifier'),
        maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted'),
        segmentationSupported=config.get('BACpypes','segmentationSupported'),
        vendorIdentifier=config.getint('BACpypes','vendorIdentifier'),
        )

    # make a simple application
    this_application = TestApplication(this_device, addr)
    this_console = TestConsoleCmd()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

