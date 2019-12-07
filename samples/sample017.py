#!/usr/bin/python

"""
This sample application presents itself to the local network as a router
to a virtual network with a potentially large number of virtual devices.

$ python sample017.py laddr lnet vnet vcount

    laddr       - local address like 192.168.0.1/24
    lnet        - local network number
    vnet        - virtual network number
    vcount      - number of virtual devices to create

Each device will be create with the device identifier (vnet * 100 + i)
and have a single random analog value object.
"""

import sys
import logging
import random

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run
from bacpypes.comm import bind

from bacpypes.pdu import Address
from bacpypes.primitivedata import Real
from bacpypes.object import AnalogValueObject, Property

from bacpypes.vlan import Network, Node
from bacpypes.netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bacpypes.bvllservice import BIPSimple, AnnexJCodec, UDPMultiplexer
from bacpypes.app import LocalDeviceObject, Application
from bacpypes.appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from bacpypes.errors import ExecutionError

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   RandomValueProperty
#

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

#
#   VLANApplication
#

@bacpypes_debugging
class VLANApplication(Application):

    def __init__(self, vlan_device, vlan_address, aseID=None):
        if _debug: VLANApplication._debug("__init__ %r %r aseID=%r", vlan_device, vlan_address, aseID)
        Application.__init__(self, vlan_device, local_address, aseID)

        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()

        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(vlan_device)

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)

        # create a vlan node at the assigned address
        self.vlan_node = Node(vlan_address)

        # bind the stack to the node, no network number
        self.nsap.bind(self.vlan_node)

    def request(self, apdu):
        if _debug: VLANApplication._debug("[%s]request %r", self.vlan_node.address, apdu)
        Application.request(self, apdu)

    def indication(self, apdu):
        if _debug: VLANApplication._debug("[%s]indication %r", self.vlan_node.address, apdu)
        Application.indication(self, apdu)

    def response(self, apdu):
        if _debug: VLANApplication._debug("[%s]response %r", self.vlan_node.address, apdu)
        Application.response(self, apdu)

    def confirmation(self, apdu):
        if _debug: VLANApplication._debug("[%s]confirmation %r", self.vlan_node.address, apdu)
        Application.confirmation(self, apdu)

#
#   VLANRouter
#

@bacpypes_debugging
class VLANRouter:

    def __init__(self, local_address, local_network, vlan_address, vlan_network):
        if _debug: VLANRouter._debug("__init__ %r %r %r %r", local_address, local_network, vlan_address, vlan_network)

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)

        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(local_address)

        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)

        # bind the BIP stack to the local network
        self.nsap.bind(self.bip, local_network, local_address)

        # create a vlan node
        self.vlan_node = Node(vlan_address)

        # bind the stack to the vlan network
        self.nsap.bind(self.vlan_node, vlan_network)

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

    local_address = Address(sys.argv[1])
    local_network = int(sys.argv[2])

    # create a VLAN
    vlan = Network()
    vlan_network = int(sys.argv[3])
    vlan_node_count = int(sys.argv[4])

    # create the VLAN router, bind it to the VLAN at address 1
    router = VLANRouter(local_address, local_network, Address(1), vlan_network)
    vlan.add_node(router.vlan_node)

    # create more nodes, starting at 2
    for i in range(2, vlan_node_count + 2):
        device_instance = vlan_network * 100 + i
        _log.debug("    - device_instance: %r", device_instance)

        # make a vlan device object
        vlan_device = \
            LocalDeviceObject(
                objectName="VLAN Node %d" % (device_instance,),
                objectIdentifier=('device', device_instance),
                maxApduLengthAccepted=1024,
                segmentationSupported='noSegmentation',
                vendorIdentifier=15,
                )
        _log.debug("    - vlan_device: %r", vlan_device)

        # make the application, add it to the network
        vlan_app = VLANApplication(vlan_device, Address(i))
        vlan.add_node(vlan_app.vlan_node)

        # make a random value object
        ravo = RandomAnalogValueObject(
            objectIdentifier=('analogValue', 1),
            objectName='Device%d/Random1' % (device_instance,),
            )
        _log.debug("    - ravo1: %r", ravo)

        # add it to the device
        vlan_app.add_object(ravo)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

