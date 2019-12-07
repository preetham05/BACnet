import random

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser
from datetime import datetime
from bacpypes.core import run
import time
from bacpypes.primitivedata import Real
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import AnalogValueObject, Property, register_object_type
from bacpypes.errors import ExecutionError
from polling import TimeoutException, poll

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_device = None
this_application = None

#
#   RandomValueProperty
#
print("Hello I belong to Server")
@bacpypes_debugging
class RandomValueProperty(Property):

    def __init__(self, identifier):
        if _debug: RandomValueProperty._debug("__init__ %r", identifier)
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug: RandomValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)

        # access an array
        if arrayIndex is not None:
            raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

        # return a random value
        value = random.random() * 100.0
        if _debug: RandomValueProperty._debug("    - value: %r", value)
	with open("C:\Users\Preetham\Documents\PreethamMasters\Third_semester\Specialisation_Module_v2\CORE\BACnet_server\log_server.txt", 'a') as file:
    		file.write('The value at: %s is %d\n' %(datetime.now(), value))
		file.close()
        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None, direct=False):
        if _debug: RandomValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r direct=%r", obj, value, arrayIndex, priority, direct)
        raise ExecutionError(errorClass='property', errorCode='writeAccessDenied')

#
#   Random Value Object Type
#

@bacpypes_debugging
class RandomAnalogValueObject(AnalogValueObject):

    properties = [
        RandomValueProperty('presentValue'),

                ]

    def __init__(self, **kwargs):
        if _debug: RandomAnalogValueObject._debug("__init__ %r", kwargs)
        AnalogValueObject.__init__(self, **kwargs)

register_object_type(RandomAnalogValueObject)

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
        objectIdentifier=('device', int(args.ini.objectidentifier)),
        maxApduLengthAccepted=int(args.ini.maxapdulengthaccepted),
        segmentationSupported=args.ini.segmentationsupported,
        vendorIdentifier=int(args.ini.vendoridentifier),
        )

    # make a sample application
    this_application = BIPSimpleApplication(this_device, args.ini.address)

    # make a random input object
    ravo1 = RandomAnalogValueObject(
        objectIdentifier=('analogValue', 1), objectName='Random1',description='normal',
        )
    _log.debug("    - ravo1: %r", ravo1)



    # add it to the device
    this_application.add_object(ravo1)

    _log.debug("    - object list: %r", this_device.objectList)

    print this_device._dict_contents()
    def sense_value():
        ravo1d = ravo1._dict_contents().popitem()
        b=ravo1d[1]
        return b
    #a,b=ravo1d.split(",")
    run()
    while True:
            time.sleep(10)
            value=sense_value()
            if value>=40:
                print("High",value)
            else:
                print("low")

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")


