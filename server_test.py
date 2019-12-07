#!/usr/bin/python

"""
This application presents a 'console' prompt to the user asking for Who-Is and I-Am
commands which create the related APDUs, then lines up the coorresponding I-Am
for incoming traffic and prints out the contents.
"""

import sys
import logging
import random
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.consolecmd import ConsoleCmd
from bacpypes.debugging import DebugContents, Logging, ModuleLogger
from bacpypes.core import run
from bacpypes.object import AnalogValueObject
from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import AnalogValueObject, Property, register_object_type
from bacpypes.apdu import WhoIsRequest, IAmRequest
from bacpypes.basetypes import ServicesSupported
from bacpypes.errors import DecodingError
from bacpypes.debugging import bacpypes_debugging
from bacpypes.primitivedata import Real
# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_device = None
this_application = None
this_console = None

#
#   WhoIsIAmApplication
#

@bacpypes_debugging
class WhoIsIAmApplication(BIPSimpleApplication):

    def __init__(self, *args):
        if _debug: WhoIsIAmApplication._debug("__init__ %r", args)
        BIPSimpleApplication.__init__(self, *args)

        # keep track of requests to line up responses
        self._request = None

    def request(self, apdu):
        if _debug: WhoIsIAmApplication._debug("request %r", apdu)

        # save a copy of the request
        self._request = apdu

        # forward it along
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: WhoIsIAmApplication._debug("confirmation %r", apdu)

        # forward it along
        BIPSimpleApplication.confirmation(self, apdu)

    def indication(self, apdu):
        if _debug: WhoIsIAmApplication._debug("indication %r", apdu)

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
        BIPSimpleApplication.indication(self, apdu)
class RandomValueProperty(Property, Logging):

    def __init__(self, identifier):
        if _debug: RandomValueProperty._debug("__init__ %r", identifier)
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug: RandomValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)

        # access an array
        if arrayIndex is not None:
            raise Error(errorClass='property', errorCode='propertyIsNotAnArray')

        # return a random value
        value = random.random() * 100.0
        if _debug: RandomValueProperty._debug("    - value: %r", value)

        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        if _debug: RandomValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r", obj, value, arrayIndex, priority)
        raise Error(errorClass='property', errorCode='writeAccessDenied')

class RandomAnalogValueObject(AnalogValueObject):
    properties = [
        RandomValueProperty('present-value'),
        ]


register_object_type(RandomAnalogValueObject)


#
#   WhoIsIAmConsoleCmd
#


@bacpypes_debugging
class WhoIsIAmConsoleCmd(ConsoleCmd):

    def do_whois(self, args):
        """whois [ <addr>] [ <lolimit> <hilimit> ]"""
        args = args.split()
        if _debug: WhoIsIAmConsoleCmd._debug("do_whois %r", args)

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
            if _debug: WhoIsIAmConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            WhoIsIAmConsoleCmd._exception("exception: %r", e)

    def do_iam(self, args):
        """iam"""
        args = args.split()
        if _debug: WhoIsIAmConsoleCmd._debug("do_iam %r", args)

        try:
            # build a request
            request = IAmRequest()
            request.pduDestination = GlobalBroadcast()

            # set the parameters from the device object
            request.iAmDeviceIdentifier = this_device.objectIdentifier
            request.maxAPDULengthAccepted = this_device.maxApduLengthAccepted
            request.segmentationSupported = this_device.segmentationSupported
            request.vendorID = this_device.vendorIdentifier
            if _debug: WhoIsIAmConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            WhoIsIAmConsoleCmd._exception("exception: %r", e)

#
#   __main__
#

try:
    # parse the command line arguments
    args = ConfigArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make a device object
    this_device = LocalDeviceObject(
        objectName=args.ini.objectname,
        objectIdentifier=int(args.ini.objectidentifier),
        maxApduLengthAccepted=int(args.ini.maxapdulengthaccepted),
        segmentationSupported=args.ini.segmentationsupported,
        vendorIdentifier=int(args.ini.vendoridentifier),
        )

    # build a bit string that knows about the bit names
    pss = ServicesSupported()
    pss['whoIs'] = 1
    pss['iAm'] = 1
    pss['readProperty'] = 1
    pss['writeProperty'] = 1

    # set the property value to be just the bits
    this_device.protocolServicesSupported = pss.value
    raio = RandomAnalogValueObject(objectIdentifier=('analogValue', 1), objectName='Random')
    _log.debug("    - ravo1: %r", raio)
    # make a simple application
    this_application = WhoIsIAmApplication(this_device, args.ini.address)
    this_console = WhoIsIAmConsoleCmd()
    this_application.add_object(raio)
    _log.debug("    - object list: %r", this_device.objectList)
    _log.debug("running")
	
    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

