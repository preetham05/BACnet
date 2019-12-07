#!/usr/bin/python

"""
Sample console application that sends out a GetAlarmSummaryRequest to a specific
address and prints out the result.
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication

from bacpypes.apdu import GetAlarmSummaryRequest, GetAlarmSummaryACK, Error, AbortPDU
from bacpypes.basetypes import ServicesSupported

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a simple application
this_application = None

#
#   TestApplication
#

@bacpypes_debugging
class TestApplication(BIPSimpleApplication):

    def __init__(self, *args):
        if _debug: TestApplication._debug("__init__ %r", args)
        BIPSimpleApplication.__init__(self, *args)

        # keep track of requests to line up responses
        self._request = None

    def request(self, apdu):
        if _debug: TestApplication._debug("request %r", apdu)

        # save a copy of the request
        self._request = apdu

        # forward it along
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("confirmation %r", apdu)

        if isinstance(apdu, Error):
            sys.stdout.write("error: %s\n" % (apdu.errorCode,))
            sys.stdout.flush()

        elif isinstance(apdu, AbortPDU):
            apdu.debug_contents()

        elif (isinstance(self._request, GetAlarmSummaryRequest)) and (isinstance(apdu, GetAlarmSummaryACK)):
            for alarm_summary in apdu.listOfAlarmSummaries:
                sys.stdout.write("%s, %s, %s\n" % (
                    alarm_summary.objectIdentifier, 
                    alarm_summary.alarmState,
                    alarm_summary.acknowledgedTransitions,
                    ))
            sys.stdout.flush()

    def indication(self, apdu):
        if _debug: TestApplication._debug("indication %r", apdu)

        # forward it along
        BIPSimpleApplication.indication(self, apdu)

#
#   TestConsoleCmd
#

@bacpypes_debugging
class TestConsoleCmd(ConsoleCmd):

    def do_getalarmsummary(self, args):
        """getalarmsummary <addr>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_getalarmsummary %r", args)

        try:
            addr = args[0]

            # build a request
            request = GetAlarmSummaryRequest()
            request.pduDestination = Address(addr)

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
    addr = config.get('BACpypes', 'address')

    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        addr += ':' + sys.argv[i+1]
    _log.debug("    - addr: %r", addr)

    # make a device object
    this_device = LocalDeviceObject(
        objectName=config.get('BACpypes','objectName'),
        objectIdentifier=config.getint('BACpypes','objectIdentifier'),
        maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted'),
        segmentationSupported=config.get('BACpypes','segmentationSupported'),
        vendorIdentifier=config.getint('BACpypes','vendorIdentifier'),
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
    this_application = TestApplication(this_device, addr)
    TestConsoleCmd()

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
