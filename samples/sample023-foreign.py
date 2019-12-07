#!/usr/bin/python

"""
sample023-foreign
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import LocalDeviceObject, BIPForeignApplication
from bacpypes.object import get_object_class, get_datatype

from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest, Error, AbortPDU, ReadPropertyACK
from bacpypes.primitivedata import Unsigned
from bacpypes.constructeddata import Array
from bacpypes.basetypes import ServicesSupported
from bacpypes.errors import DecodingError

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

@bacpypes_debugging
class TestApplication(BIPForeignApplication):

    def __init__(self, *args):
        if _debug: TestApplication._debug("__init__ %r", args)
        BIPForeignApplication.__init__(self, *args)

        # keep track of requests to line up responses
        self._request = None

    def request(self, apdu):
        if _debug: TestApplication._debug("request %r", apdu)

        # save a copy of the request
        self._request = apdu

        # forward it along
        BIPForeignApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("confirmation %r", apdu)

        if isinstance(apdu, Error):
            sys.stdout.write("error: %s\n" % (apdu.errorCode,))
            sys.stdout.flush()

        elif isinstance(apdu, AbortPDU):
            apdu.debug_contents()

        elif (isinstance(self._request, ReadPropertyRequest)) and (isinstance(apdu, ReadPropertyACK)):
            # find the datatype
            datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
            TestApplication._debug("    - datatype: %r", datatype)
            if not datatype:
                raise TypeError, "unknown datatype"

            # special case for array parts, others are managed by cast_out
            if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.cast_out(Unsigned)
                else:
                    value = apdu.propertyValue.cast_out(datatype.subtype)
            else:
                value = apdu.propertyValue.cast_out(datatype)
            TestApplication._debug("    - value: %r", value)

            sys.stdout.write(str(value) + '\n')
            sys.stdout.flush()

    def indication(self, apdu):
        if _debug: TestApplication._debug("indication %r", apdu)

        if (isinstance(self._request, WhoIsRequest)) and (isinstance(apdu, IAmRequest)):
            device_type, device_instance = apdu.iAmDeviceIdentifier
            if device_type != 'device':
                raise DecodingError, "invalid object type"

            if (self._request.deviceInstanceRangeLowLimit is not None) and \
                (device_instance < self._request.deviceInstanceRangeLowLimit):
                pass
            elif (self._request.deviceInstanceRangeHighLimit is not None) and \
                (device_instance > self._request.deviceInstanceRangeHighLimit):
                pass
            else:
                # print out the contents
                sys.stdout.write('pduSource = ' + repr(apdu.pduSource) + '\n')
                sys.stdout.write('iAmDeviceIdentifier = ' + str(apdu.iAmDeviceIdentifier) + '\n')
                sys.stdout.write('maxAPDULengthAccepted = ' + str(apdu.maxAPDULengthAccepted) + '\n')
                sys.stdout.write('segmentationSupported = ' + str(apdu.segmentationSupported) + '\n')
                sys.stdout.write('vendorID = ' + str(apdu.vendorID) + '\n')
                sys.stdout.flush()

        # forward it along
        BIPForeignApplication.indication(self, apdu)

#
#   TestConsoleCmd
#

@bacpypes_debugging
class TestConsoleCmd(ConsoleCmd):

    def do_whois(self, args):
        """whois [ <addr>] [ <lolimit> <hilimit> ]"""
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
                request.deviceInstanceRangeLowLimit = int(args[0])
                request.deviceInstanceRangeHighLimit = int(args[1])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_iam(self, args):
        """iam"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_iam %r", args)

        try:
            # build a request
            request = IAmRequest()
            request.pduDestination = GlobalBroadcast()

            # set the parameters from the device object
            request.iAmDeviceIdentifier = this_device.objectIdentifier
            request.maxAPDULengthAccepted = this_device.maxApduLengthAccepted
            request.segmentationSupported = this_device.segmentationSupported
            request.vendorID = this_device.vendorIdentifier
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_read(self, args):
        """read <addr> <type> <inst> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            addr, obj_type, obj_inst, prop_id = args[:4]

            if obj_type.isdigit():
                obj_type = int(obj_type)
            elif not get_object_class(obj_type):
                raise ValueError, "unknown object type"

            obj_inst = int(obj_inst)

            datatype = get_datatype(obj_type, prop_id)
            if not datatype:
                raise ValueError, "invalid property for object type"

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=(obj_type, obj_inst),
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(addr)

            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

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
    foreign_bbmd = config.get('BACpypes', 'foreignBBMD')

    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        foreign_bbmd += ':' + sys.argv[i+1]
    _log.debug("    - foreign_bbmd: %r", foreign_bbmd)

    # get the time-to-live from the config file
    foreign_ttl = config.getint('BACpypes', 'foreignTTL')

    # maybe use a different ttl
    if '--ttl' in sys.argv:
        i = sys.argv.index('--ttl')
        foreign_ttl = int(sys.argv[i+1])
    _log.debug("    - foreign_ttl: %r", foreign_ttl)

    # make a device object
    this_device = \
        LocalDeviceObject( objectName=config.get('BACpypes','objectName')
            , objectIdentifier=config.getint('BACpypes','objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes','segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
            )

    # build a bit string that knows about the bit names
    pss = ServicesSupported()
    pss['whoIs'] = 1
    pss['iAm'] = 1
    pss['readProperty'] = 1
    pss['writeProperty'] = 1

    # set the property value to be just the bits
    this_device.protocolServicesSupported = pss.value

    # make a simple application
    this_application = TestApplication(
        this_device,    # device object as usual
        ('', 0),        # local host, operating system assigned port
        foreign_bbmd,   # address of BBMD accepted foreign device registration
        foreign_ttl,    # time to live
        )
    this_console = TestConsoleCmd()

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
