#!/usr/bin/python

"""
Decode Hex

Take a hex encoding of the UDP contents of a packet and decode it.  This is useful
for decoding UDP packets on non-standard ports.  Select the UDP data portion of the
packet in Wireshark, right-click and select Copy / Bytes / Hex Stream.

$ python DecodeHex.py 8104001c0ac0020abac00128ffff00100f0119fd10080a02351a0235
    pduSource = <RemoteStation 4111:25>
    pduDestination = <GlobalBroadcast *:*>
    pduExpectingReply = False
    pduNetworkPriority = 0
    apduType = 1
    apduService = 8
    deviceInstanceRangeLowLimit = 565L
    deviceInstanceRangeHighLimit = 565L
    pduData = x''

"""

import time
import socket

from bacpypes.debugging import ModuleLogger, bacpypes_debugging
from bacpypes.consolelogging import ArgumentParser

from bacpypes.pdu import PDU
from bacpypes.bvll import BVLPDU, bvl_pdu_types, ForwardedNPDU, \
    DistributeBroadcastToNetwork, OriginalUnicastNPDU, OriginalBroadcastNPDU
from bacpypes.npdu import NPDU, npdu_types
from bacpypes.apdu import APDU, apdu_types, confirmed_request_types, unconfirmed_request_types, complex_ack_types, error_types, \
    ConfirmedRequestPDU, UnconfirmedRequestPDU, SimpleAckPDU, ComplexAckPDU, SegmentAckPDU, ErrorPDU, RejectPDU, AbortPDU

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# protocol map
_protocols = {
    socket.IPPROTO_TCP:'tcp',
    socket.IPPROTO_UDP:'udp',
    socket.IPPROTO_ICMP:'icmp',
    }

#
#   _hexify
#

def _hexify(s, sep='.'):
    return sep.join('%02X' % ord(c) for c in s)

#
#   strftimestamp
#

def strftimestamp(ts):
    return time.strftime("%d-%b-%Y %H:%M:%S", time.localtime(ts)) \
            + (".%06d" % ((ts - int(ts)) * 1000000,))

#
#   decode_packet
#

@bacpypes_debugging
def decode_packet(data):
    """decode the data, return some kind of PDU."""
    if _debug: decode_packet._debug("decode_packet %r", data)

    # convert the hex data to an octet string
    data = ''.join(chr(int(data[i:i+2], 16)) for i in range(0, len(data), 2))

    # build a PDU
    pdu = PDU(data)

    # check for a BVLL header
    if (pdu.pduData[0] == '\x81'):
        if _debug: decode_packet._debug("    - BVLL header found")

        xpdu = BVLPDU()
        xpdu.decode(pdu)
        if _debug: decode_packet._debug("    - xpdu: %r", xpdu)
        pdu = xpdu

        # make a more focused interpretation
        atype = bvl_pdu_types.get(pdu.bvlciFunction)
        if not atype:
            if _debug: decode_packet._debug("    - unknown BVLL type: %r", pdu.bvlciFunction)
            return pdu

        # decode it as one of the basic types
        try:
            xpdu = pdu
            bpdu = atype()
            bpdu.decode(pdu)
            if _debug: decode_packet._debug("    - bpdu: %r", bpdu)

            pdu = bpdu

            # lift the address for forwarded NPDU's
            if atype is ForwardedNPDU:
                pdu.pduSource = bpdu.bvlciAddress
            # no deeper decoding for some
            elif atype not in (DistributeBroadcastToNetwork, OriginalUnicastNPDU, OriginalBroadcastNPDU):
                return pdu

        except Exception, err:
            if _debug: decode_packet._debug("    - decoding Error: %r", err)
            return xpdu

    # check for version number
    if (pdu.pduData[0] != '\x01'):
        if _debug: decode_packet._debug("    - not a version 1 packet: %s...", _hexify(pdu.pduData[:30]))
        return None

    # it's an NPDU
    try:
        npdu = NPDU()
        npdu.decode(pdu)
        if _debug: decode_packet._debug("    - npdu: %r", npdu)
    except Exception, err:
        if _debug: decode_packet._debug("    - decoding Error: %r", err)
        return None

    # application or network layer message
    if npdu.npduNetMessage is None:
        if _debug: decode_packet._debug("    - not a network layer message, try as an APDU")

        # decode as a generic APDU
        try:
            xpdu = APDU()
            xpdu.decode(npdu)
            if _debug: decode_packet._debug("    - xpdu: %r", xpdu)
            apdu = xpdu
        except Exception, err:
            if _debug: decode_packet._debug("    - decoding Error: %r", err)
            return npdu

        # "lift" the source and destination address
        if npdu.npduSADR:
            apdu.pduSource = npdu.npduSADR
        else:
            apdu.pduSource = npdu.pduSource
        if npdu.npduDADR:
            apdu.pduDestination = npdu.npduDADR
        else:
            apdu.pduDestination = npdu.pduDestination

        # make a more focused interpretation
        atype = apdu_types.get(apdu.apduType)
        if not atype:
            if _debug: decode_packet._debug("    - unknown APDU type: %r", apdu.apduType)
            return apdu

        # decode it as one of the basic types
        try:
            xpdu = apdu
            apdu = atype()
            apdu.decode(xpdu)
            if _debug: decode_packet._debug("    - apdu: %r", apdu)
        except Exception, err:
            if _debug: decode_packet._debug("    - decoding Error: %r", err)
            return xpdu

        # decode it at the next level
        if isinstance(apdu, ConfirmedRequestPDU):
            atype = confirmed_request_types.get(apdu.apduService)
            if not atype:
                if _debug: decode_packet._debug("    - no confirmed request decoder: %r", apdu.apduService)
                return apdu

        elif isinstance(apdu, UnconfirmedRequestPDU):
            atype = unconfirmed_request_types.get(apdu.apduService)
            if not atype:
                if _debug: decode_packet._debug("    - no unconfirmed request decoder: %r", apdu.apduService)
                return apdu

        elif isinstance(apdu, SimpleAckPDU):
            atype = None

        elif isinstance(apdu, ComplexAckPDU):
            atype = complex_ack_types.get(apdu.apduService)
            if not atype:
                if _debug: decode_packet._debug("    - no complex ack decoder: %r", apdu.apduService)
                return apdu

        elif isinstance(apdu, SegmentAckPDU):
            atype = None

        elif isinstance(apdu, ErrorPDU):
            atype = error_types.get(apdu.apduService)
            if not atype:
                if _debug: decode_packet._debug("    - no error decoder: %r", apdu.apduService)
                return apdu

        elif isinstance(apdu, RejectPDU):
            atype = None

        elif isinstance(apdu, AbortPDU):
            atype = None
        if _debug: decode_packet._debug("    - atype: %r", atype)

        # deeper decoding
        try:
            if atype:
                xpdu = apdu
                apdu = atype()
                apdu.decode(xpdu)
                if _debug: decode_packet._debug("    - apdu: %r", apdu)
        except Exception, err:
            if _debug: decode_packet._debug("    - decoding error: %r", err)
            return xpdu

        # success
        return apdu

    else:
        # make a more focused interpretation
        ntype = npdu_types.get(npdu.npduNetMessage)
        if not ntype:
            if _debug: decode_packet._debug("    - no network layer decoder: %r", npdu.npduNetMessage)
            return npdu
        if _debug: decode_packet._debug("    - ntype: %r", ntype)

        # deeper decoding
        try:
            xpdu = npdu
            npdu = ntype()
            npdu.decode(xpdu)
            if _debug: decode_packet._debug("    - npdu: %r", npdu)
        except Exception, err:
            if _debug: decode_packet._debug("    - decoding error: %r", err)
            return xpdu

        # success
        return npdu

#
#   __main__
#

try:
    # parse the command line arguments
    parser = ArgumentParser(description=__doc__)

    # add an argument for interval
    parser.add_argument('packet', type=str, nargs='+',
          help='packet contents in hex',
          )

    # now parse the arguments
    args = parser.parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    for data in args.packet:
        packet = decode_packet(data)
        packet.debug_contents()

except KeyboardInterrupt:
    pass
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

