#!/usr/bin/python

"""
This sample application shows how to extend a schedule object to provide a
present value. This is a special kind of object because the present value can
be any atomic type.
"""

from bacpypes.debugging import ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser

from bacpypes.core import run

from bacpypes.primitivedata import Null, Integer, Real
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.basetypes import DailySchedule, TimeValue
from bacpypes.constructeddata import ArrayOf
from bacpypes.object import ScheduleObject

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_device = None
this_application = None

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

    # make a sample application
    this_application = BIPSimpleApplication(this_device, args.ini.address)

    # make a schedule object with an integer value
    so1 = ScheduleObject(
        objectIdentifier=1, objectName='Schedule 1 (integer)',
        presentValue=Integer(8),
        weeklySchedule=ArrayOf(DailySchedule)([
            DailySchedule(
                daySchedule=[
                    TimeValue(time=(8,0,0,0), value=Integer(8)),
                    TimeValue(time=(14,0,0,0), value=Null()),
                    TimeValue(time=(17,0,0,0), value=Integer(42)),
                    TimeValue(time=(0,0,0,0), value=Null()),
                    ]),
            ] * 7),
        scheduleDefault=Integer(0),
        )
    _log.debug("    - so1: %r", so1)

    so2 = ScheduleObject(
        objectIdentifier=2, objectName='Schedule 2 (real)',
        presentValue=Real(73.5),
        weeklySchedule=ArrayOf(DailySchedule)([
            DailySchedule(
                daySchedule=[
                    TimeValue(time=(9,0,0,0), value=Real(78.0)),
                    TimeValue(time=(10,0,0,0), value=Null()),
                    ]),
            ] * 7),
        scheduleDefault=Real(72.0),
        )
    _log.debug("    - so2: %r", so2)

    # add it to the device
    this_application.add_object(so1)
    this_application.add_object(so2)
    _log.debug("    - object list: %r", this_device.objectList)

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

