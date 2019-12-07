#!/usr/bin/python

"""
Time Synchronization Request

Sample console application that sends out a TimeSynchronizationRequest or a 
UTCTimeSynchronizationRequest to a specific address.
"""

import sys
import time
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication

from bacpypes.primitivedata import Date, Time
from bacpypes.basetypes import ServicesSupported, DateTime
from bacpypes.apdu import TimeSynchronizationRequest, UTCTimeSynchronizationRequest, Error, AbortPDU

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a simple application
this_application = None

# time format to interpret the time
# see http://docs.python.org/2/library/time.html#time.strftime
TIME_FORMAT="%d %b %y"

#
#   TestApplication
#

@bacpypes_debugging
class TestApplication(BIPSimpleApplication):

    def __init__(self, *args):
        if _debug: TestApplication._debug("__init__ %r", args)
        BIPSimpleApplication.__init__(self, *args)

    def request(self, apdu):
        if _debug: TestApplication._debug("request %r", apdu)

        # forward it along
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("confirmation %r", apdu)

        if isinstance(apdu, Error):
            sys.stdout.write("error: %s\n" % (apdu.errorCode,))
            sys.stdout.flush()

        elif isinstance(apdu, AbortPDU):
            apdu.debug_contents()

    def indication(self, apdu):
        if _debug: TestApplication._debug("indication %r", apdu)

        # forward it along
        BIPSimpleApplication.indication(self, apdu)

#
#   TestConsoleCmd
#

@bacpypes_debugging
class TestConsoleCmd(ConsoleCmd):

    def sometime(self, klass, now, args):
        if _debug: TestConsoleCmd._debug("sometime %r %r %r", klass, now, args)

        try:
            addr = args[0]

            # look for a time to send
            if (len(args) > 1):
                when = time.strptime(' '.join(args[1:]), TIME_FORMAT)
            else:
                when = now
            if _debug: TestConsoleCmd._debug("    - when: %r", when)

            # build the date and time primitives
            when_date=Date(
                year=when.tm_year - 1900,
                month=when.tm_mon,
                day=when.tm_mday,
                dayOfWeek=when.tm_wday + 1,
                )
            if _debug: TestConsoleCmd._debug("    - when_date: %s", when_date)
            when_time=Time(
                hour=when.tm_hour,
                minute=when.tm_min,
                second=when.tm_sec,
                hundredth=0
                )
            if _debug: TestConsoleCmd._debug("    - when_time: %s", when_time)

            # build a request
            request = klass()
            request.pduDestination = Address(addr)

            # only one simple parameter, happens to be the same for both types
            request.time = DateTime(date=when_date, time=when_time)

            # give it to the application
            this_application.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_time(self, args):
        """time <addr> [ <when> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_time %r", args)

        self.sometime(TimeSynchronizationRequest, time.localtime(), args)

    def do_utctime(self, args):
        """utctime <addr> [ <when> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_utctime %r", args)

        self.sometime(UTCTimeSynchronizationRequest, time.gmtime(), args)

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
