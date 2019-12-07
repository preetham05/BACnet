#!/usr/bin/python2.3

import sys
import types
import exceptions
import re
import socket
import struct
import time
import thread
import threading
import random

import CSThread

# some debugging flags and functions
_debug = 0
_debugVLAN = _debug or 0
_debugAdapterRefs = _debug or 0
_debugSegmentation = _debug or 0
_debugAPDUcodec = _debug or 0

def StringToHex(x,sep=''):
    return sep.join(["%02X" % (ord(c),) for c in x])

def HexToString(x,sep=''):
    return ''.join([chr(int(x[i:i+2],16)) for i in range(0,len(x),len(sep)+2)])

#
#   Exceptions
#

class ConfigurationError(exceptions.ValueError):

    def __init__(self,args=None):
        self.args = args

class EncodingError(exceptions.ValueError):

    def __init__(self,args=None):
        self.args = args

class DecodingError(exceptions.ValueError):

    def __init__(self,args=None):
        self.args = args

#
#   Address
#

IPAddrMaskPortRE = re.compile(r'^(?:(\d+):)?(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?(?::(\d+))?$' )

class Address:
    nullAddr = 0
    localBroadcastAddr = 1
    localStationAddr = 2
    remoteBroadcastAddr = 3
    remoteStationAddr = 4
    globalBroadcastAddr = 5

    def __init__(self,*args):
        self.addrType = Address.nullAddr
        self.addrNet = None
        self.addrLen = 0
        self.addrAddr = ''

        if len(args) == 1:
            self.DecodeAddress(args[0])
        elif len(args) == 2:
            self.DecodeAddress(args[1])
            if self.addrType == Address.localStationAddr:
                self.addrType = Address.remoteStationAddr
                self.addrNet = args[0]
            elif self.addrType == Address.localBroadcastAddr:
                self.addrType = Address.remoteBroadcastAddr
                self.addrNet = args[0]
            else:
                raise ValueError, "unrecognized address ctor form"

    def DecodeAddress(self,addr):
        """Initialize the address from a string.  Lots of different forms are supported."""
        if _debug:
            print self, "DecodeAddress", addr

        # start out assuming this is a local station
        self.addrType = Address.localStationAddr
        self.addrNet = None

        if addr == "*":
            self.addrType = Address.localBroadcastAddr
            self.addrNet = None
            self.addrAddr = None
            self.addrLen = None

        elif addr == "*:*":
            self.addrType = Address.globalBroadcastAddr
            self.addrNet = None
            self.addrAddr = None
            self.addrLen = None

        elif isinstance(addr,types.IntType):
            if (addr < 0) or (addr >= 256):
                raise ValueError, "address out of range"
            self.addrAddr = chr(addr)
            self.addrLen = 1

        elif isinstance(addr,types.StringType):
            m = IPAddrMaskPortRE.match(addr)
            if m:
                net, addr, mask, port = m.groups()
                if not mask: mask = '32'
                if not port: port = '47808'

                if net:
                    net = int(net)
                    if (net >= 65535):
                        raise ValueError, "network out of range"
                    self.addrType = Address.remoteStationAddr
                    self.addrNet = net

                self.addrPort = int(port)
                self.addrTuple = (addr,self.addrPort)

                addrstr = socket.inet_aton(addr)
                self.addrIP = struct.unpack('!L',addrstr)[0]
                self.addrMask = -1L << (32 - int(mask))
                self.addrHost = (self.addrIP & ~self.addrMask)
                self.addrSubnet = (self.addrIP & self.addrMask)

                bcast = (self.addrSubnet | ~self.addrMask)
                self.addrBroadcastTuple = (socket.inet_ntoa(struct.pack('!L',bcast)),self.addrPort)

                self.addrAddr = addrstr + struct.pack('!H',self.addrPort)
                self.addrLen = 6

            elif re.match(r"^\d+$",addr):
                addr = int(addr)
                if (addr > 255):
                    raise ValueError, "address out of range"

                self.addrAddr = chr(addr)
                self.addrLen = 1

            elif re.match(r"^\d+:[*]$",addr):
                addr = int(addr[:-2])
                if (addr >= 65535):
                    raise ValueError, "network out of range"

                self.addrType = Address.remoteBroadcastAddr
                self.addrNet = addr
                self.addrAddr = None
                self.addrLen = None

            elif re.match(r"^\d+:\d+$",addr):
                net, addr = addr.split(':')
                net = int(net)
                addr = int(addr)
                if (net >= 65535):
                    raise ValueError, "network out of range"
                if (addr > 255):
                    raise ValueError, "address out of range"

                self.addrType = Address.remoteStationAddr
                self.addrNet = net
                self.addrAddr = chr(addr)
                self.addrLen = 1

            elif re.match(r"^0x([0-9A-Fa-f][0-9A-Fa-f])+$",addr):
                self.addrAddr = HexToString(addr[2:])
                self.addrLen = len(self.addrAddr)

            elif re.match(r"^X'([0-9A-Fa-f][0-9A-Fa-f])+'$",addr):
                self.addrAddr = HexToString(addr[2:-1])
                self.addrLen = len(self.addrAddr)

            elif re.match(r"^\d+:0x([0-9A-Fa-f][0-9A-Fa-f])+$",addr):
                net, addr = addr.split(':')
                net = int(net)
                if (net >= 65535):
                    raise ValueError, "network out of range"

                self.addrType = Address.remoteStationAddr
                self.addrNet = net
                self.addrAddr = HexToString(addr[2:])
                self.addrLen = len(self.addrAddr)

            elif re.match(r"^\d+:X'([0-9A-Fa-f][0-9A-Fa-f])+'$",addr):
                net, addr = addr.split(':')
                net = int(net)
                if (net >= 65535):
                    raise ValueError, "network out of range"

                self.addrType = Address.remoteStationAddr
                self.addrNet = net
                self.addrAddr = HexToString(addr[2:-1])
                self.addrLen = len(self.addrAddr)

            else:
                raise ValueError, "unrecognized format"

        elif isinstance(addr,types.TupleType):
            addr, port = addr
            self.addrPort = int(port)

            if isinstance(addr,types.StringType):
                addrstr = socket.inet_aton(addr)
                self.addrTuple = (addr,self.addrPort)
            elif isinstance(addr,types.LongType):
                addrstr = struct.pack('!L',addr)
                self.addrTuple = (socket.inet_ntoa(addrstr),self.addrPort)
            else:
                raise TypeError, "tuple must be (string,port) or (long,port)"

            self.addrIP = struct.unpack('!L',addrstr)[0]
            self.addrMask = -1L
            self.addrHost = None
            self.addrSubnet = None
            self.addrBroadcastTuple = self.addrTuple

            self.addrAddr = addrstr + struct.pack('!H',self.addrPort)
            self.addrLen = 6
        else:
            raise TypeError, "integer, string or tuple required"

    def __str__(self):
        if self.addrType == Address.nullAddr:
            return 'Null'
        elif self.addrType == Address.localBroadcastAddr:
            return '*'
        elif self.addrType == Address.localStationAddr:
            rslt = ''
            if self.addrLen == 1:
                rslt += str(ord(self.addrAddr[0]))
            else:
                port = ord(self.addrAddr[-2]) * 256 + ord(self.addrAddr[-1])
                if (len(self.addrAddr) == 6) and (port >= 47808) and (port <= 47823):
                    rslt += '.'.join(["%d" % ord(x) for x in self.addrAddr[0:4]])
                    if port != 47808:
                        rslt += ':' + str(port)
                else:
                    rslt += '0x' + StringToHex(self.addrAddr)
            return rslt
        elif self.addrType == Address.remoteBroadcastAddr:
            return '%d:*' % (self.addrNet,)
        elif self.addrType == Address.remoteStationAddr:
            rslt = '%d:' % (self.addrNet,)
            if self.addrLen == 1:
                rslt += str(ord(self.addrAddr[0]))
            else:
                port = ord(self.addrAddr[-2]) * 256 + ord(self.addrAddr[-1])
                if (len(self.addrAddr) == 6) and (port >= 47808) and (port <= 47823):
                    rslt += '.'.join(["%d" % ord(x) for x in self.addrAddr[0:4]])
                    if port != 47808:
                        rslt += ':' + str(port)
                else:
                    rslt += '0x' + StringToHex(self.addrAddr)
            return rslt
        elif self.addrType == Address.globalBroadcastAddr:
            return '*:*'
        else:
            raise TypeError, "unknown address type %d" % self.addrType

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.__str__())

    def __hash__(self):
        return hash( (self.addrType, self.addrNet, self.addrAddr) )

    def __eq__(self,arg):
        # try an coerce it into an address
        if not isinstance(arg,Address):
            arg = Address(arg)

        # all of the components must match
        return (self.addrType == arg.addrType) and (self.addrNet == arg.addrNet) and (self.addrAddr == arg.addrAddr)

    def __ne__(self,arg):
        return not self.__eq__(arg)

def IPAddrPack(addr):
    return socket.inet_aton(addr[0]) + struct.pack('!H',addr[1])

def IPAddrUnpack(addr):
    return (socket.inet_ntoa(addr[0:4]), struct.unpack('!H',addr[4:6])[0] )

#

class LocalStation(Address):

    def __init__(self,addr):
        self.addrType = Address.localStationAddr
        self.addrNet = None
        if isinstance(addr,types.IntType):
            if (addr < 0) or (addr >= 256):
                raise ValueError, "address out of range"
            self.addrAddr = chr(addr)
            self.addrLen = 1
        else:
            self.addrAddr = addr
            self.addrLen = len(addr)

class RemoteStation(Address):

    def __init__(self,net,addr):
        if (net < 0) or (net >= 65535):
            raise ValueError, "network out of range"

        self.addrType = Address.remoteStationAddr
        self.addrNet = net
        if isinstance(addr,types.IntType):
            if (addr < 0) or (addr >= 256):
                raise ValueError, "address out of range"
            self.addrAddr = chr(addr)
            self.addrLen = 1
        else:
            self.addrAddr = addr
            self.addrLen = len(addr)

class LocalBroadcast(Address):

    def __init__(self):
        self.addrType = Address.localBroadcastAddr
        self.addrNet = None
        self.addrAddr = None
        self.addrLen = None

class RemoteBroadcast(Address):

    def __init__(self,net):
        if (net < 0) or (net >= 65535):
            raise ValueError, "network out of range"

        self.addrType = Address.remoteBroadcastAddr
        self.addrNet = net
        self.addrAddr = None
        self.addrLen = None

class GlobalBroadcast(Address):

    def __init__(self):
        self.addrType = Address.globalBroadcastAddr
        self.addrNet = None
        self.addrAddr = None
        self.addrLen = None

#
#   PDUData
#

class PDUData:

    def __init__(self, data=''):
        if isinstance(data,PDUData):
            self.pduData = data.pduData
        elif isinstance(data,types.StringType):
            self.pduData = data
        else:
            raise ValueError, "PDUData ctor parameter must be PDUData or a string"

    def Get(self):
        if len(self.pduData) == 0:
            raise DecodingError, "no more packet data"

        ch = self.pduData[0]
        self.pduData = self.pduData[1:]
        return ord(ch)

    def GetShort(self):
        if len(self.pduData) < 2:
            raise DecodingError, "no more packet data"

        rslt = (ord(self.pduData[0]) << 8) + ord(self.pduData[1])
        self.pduData = self.pduData[2:]
        return rslt

    def GetLong(self):
        return struct.unpack('>L',self.GetData(4))[0]

    def GetData(self, dlen):
        if len(self.pduData) < dlen:
            raise DecodingError, "no more packet data"

        data = self.pduData[:dlen]
        self.pduData = self.pduData[dlen:]
        return data

    def Put(self, ch):
        self.pduData += chr(ch)

    def PutShort(self, n):
        self.pduData += chr((n >> 8) & 0xFF) + chr(n & 0xFF)

    def PutLong(self, n):
        self.pduData += struct.pack('>L',n)

    def PutData(self, data):
        self.pduData += data

    def __str__(self):
        """Useful for debugging."""
        return "PDUData(" + StringToHex(self.pduData,'.') + ")"

#
#   Tag
#

class Tag:
    applicationTagClass     = 0
    contextTagClass         = 1
    openingTagClass         = 2
    closingTagClass         = 3

    nullAppTag              = 0
    booleanAppTag           = 1
    unsignedAppTag          = 2
    integerAppTag           = 3
    realAppTag              = 4
    doubleAppTag            = 5
    octetStringAppTag       = 6
    characterStringAppTag   = 7
    bitStringAppTag         = 8
    enumeratedAppTag        = 9
    dateAppTag              = 10
    timeAppTag              = 11
    objectIdentifierAppTag  = 12
    reservedAppTag13        = 13
    reservedAppTag14        = 14
    reservedAppTag15        = 15

    _applicationTagName = \
        [ 'null', 'boolean', 'unsigned', 'integer'
        , 'real', 'double', 'octetString', 'characterString'
        , 'bitString', 'enumerated', 'date', 'time'
        , 'objectIdentifier', 'reserved13', 'reserved14', 'reserved15'
        ]
    _applicationTagClass = [] # defined later

    def __init__(self, *args):
        self.tagClass = None
        self.tagNumber = None
        self.tagLVT = None
        self.tagData = None

        if args:
            if (len(args) == 1) and isinstance(args[0],PDUData):
                self.Decode(args[0])
            elif (len(args) >= 2):
                self.Set(*args)
            else:
                raise ValueError, "invalid Tag ctor arguments"

    def Set(self, tclass, tnum, tlvt=0, tdata=''):
        """Set the values of the tag."""
        self.tagClass = tclass
        self.tagNumber = tnum
        self.tagLVT = tlvt
        self.tagData = tdata

    def SetAppData(self, tnum, tdata):
        """Set the values of the tag."""
        self.tagClass = Tag.applicationTagClass
        self.tagNumber = tnum
        self.tagLVT = len(tdata)
        self.tagData = tdata

    def Encode(self, pdu):
        # check for special encoding of open and close tags
        if (self.tagClass == Tag.openingTagClass):
            pdu.Put(((self.tagNumber & 0x0F) << 4) + 0x0E)
            return
        if (self.tagClass == Tag.closingTagClass):
            pdu.Put(((self.tagNumber & 0x0F) << 4) + 0x0F)
            return

        # check for context encoding
        if (self.tagClass == Tag.contextTagClass):
            data = 0x08
        else:
            data = 0x00

        # encode the tag number part
        if (self.tagNumber < 15):
            data += (self.tagNumber << 4)
        else:
            data += 0xF0

        # encode the length/value/type part
        if (self.tagLVT < 5):
            data += self.tagLVT
        else:
            data += 0x05

        # save this and the extended tag value
        pdu.Put( data )
        if (self.tagNumber >= 15):
            pdu.Put(self.tagNumber)

        # really short lengths are already done
        if (self.tagLVT >= 5):
            if (self.tagLVT <= 253):
                pdu.Put( self.tagLVT )
            elif (self.tagLVT <= 65535):
                enc.Put( 254 )
                pdu.PutShort( self.tagLVT )
            else:
                pdu.Put( 255 )
                pdu.PutLong( self.tagLVT )

        # now put the data
        pdu.PutData(self.tagData)

    def Decode(self, pdu):
        tag = pdu.Get()

        # extract the type
        self.tagClass = (tag >> 3) & 0x01

        # extract the tag number
        self.tagNumber = (tag >> 4)
        if (self.tagNumber == 0x0F):
            self.tagNumber = dec.Get()

        # extract the length
        self.tagLVT = tag & 0x07
        if (self.tagLVT == 5):
            self.tagLVT = pdu.Get()
            if (self.tagLVT == 254):
                self.tagLVT = pdu.GetShort()
            elif (self.tagLVT == 255):
                self.tagLVT = pdu.GetLong()
        elif (self.tagLVT == 6):
            self.tagClass = Tag.openingTagClass
            self.tagLVT = 0
        elif (self.tagLVT == 7):
            self.tagClass = Tag.closingTagClass
            self.tagLVT = 0

        # application tagged boolean has no more data
        if (self.tagClass == Tag.applicationTagClass) and (self.tagNumber == Tag.booleanAppTag):
            # tagLVT contains value
            self.tagData = ''
        else:
            # tagLVT contains length
            self.tagData = pdu.GetData(self.tagLVT)

    def AppToCtx(self, context):
        """Return a context encoded tag."""
        if self.tagClass != Tag.applicationTagClass:
            raise ValueError, "application tag required"

        # application tagged boolean now has data
        if (self.tagNumber == Tag.booleanAppTag):
            return ContextTag(context, chr(self.tagLVT))
        else:
            return ContextTag(context, self.tagData)

    def CtxToApp(self, dataType):
        """Return an application encoded tag."""
        if self.tagClass != Tag.contextTagClass:
            raise ValueError, "context tag required"

        # context booleans have value in data
        if (dataType == Tag.booleanAppTag):
            return Tag(Tag.applicationTagClass, Tag.booleanAppTag, ord(self.tagData[0]), '')
        else:
            return ApplicationTag(dataType, self.tagData)

    def AppToObject(self):
        """Return the application object encoded by the tag."""
        if self.tagClass != Tag.applicationTagClass:
            raise ValueError, "application tag required"

        # get the class to build
        klass = self._applicationTagClass[self.tagNumber]
        if not klass:
            return None

        # build an object, tell it to decode this tag, and return it
        return klass(self)

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            if self.tagClass == Tag.openingTagClass:
                desc = "(open(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.closingTagClass:
                desc = "(close(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.contextTagClass:
                desc = "(context(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.applicationTagClass:
                desc = "(%s)" % (self._applicationTagName[self.tagNumber],)
            else:
                raise ValueError, "invalid tag class"
        except:
            desc = "(?)"

        return '<' + sname + desc + ' instance at 0x%08x' % (xid,) + '>'

    def __eq__(self, tag):
        return (self.tagClass == tag.tagClass) \
            and (self.tagNumber == tag.tagNumber) \
            and (self.tagLVT == tag.tagLVT) \
            and (self.tagData == tag.tagData)

    def __ne__(self,arg):
        return not self.__eq__(arg)

#
#   ApplicationTag
#

class ApplicationTag(Tag):

    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], PDUData):
            Tag.__init__(self, args[0])
            if self.tagClass != Tag.applicationTagClass:
                raise DecodingError, "application tag not decoded"
        elif len(args) == 2:
            tnum, tdata = args
            Tag.__init__(self, Tag.applicationTagClass, tnum, len(tdata), tdata)
        else:
            raise ValueError, "ApplicationTag ctor requires a type and data or PDUData"

#
#   ContextTag
#

class ContextTag(Tag):

    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], PDUData):
            Tag.__init__(self, args[0])
            if self.tagClass != Tag.contextTagClass:
                raise DecodingError, "context tag not decoded"
        elif len(args) == 2:
            tnum, tdata = args
            Tag.__init__(self, Tag.contextTagClass, tnum, len(tdata), tdata)
        else:
            raise ValueError, "ContextyTag ctor requires a type and data or PDUData"

#
#   OpeningTag
#

class OpeningTag(Tag):

    def __init__(self, context):
        if isinstance(context, PDUData):
            Tag.__init__(self, context)
            if self.tagClass != Tag.openingTagClass:
                raise DecodingError, "opening tag not decoded"
        elif isinstance(context, types.IntType):
            Tag.__init__(self, Tag.openingTagClass, context)
        else:
            raise TypeError, "OpeningTag ctor requires an integer or PDUData"

#
#   ClosingTag
#

class ClosingTag(Tag):

    def __init__(self, context):
        if isinstance(context, PDUData):
            Tag.__init__(self, context)
            if self.tagClass != Tag.closingTagClass:
                raise DecodingError, "closing tag not decoded"
        elif isinstance(context, types.IntType):
            Tag.__init__(self, Tag.closingTagClass, context)
        else:
            raise TypeError, "OpeningTag ctor requires an integer or PDUData"

#
#   DebugTag
#

def DebugTag(tag):
    print "DebugTag", tag

    print "    tagClass =", tag.tagClass,
    if tag.tagClass == Tag.applicationTagClass: print 'application'
    elif tag.tagClass == Tag.contextTagClass: print 'context'
    elif tag.tagClass == Tag.openingTagClass: print 'opening'
    elif tag.tagClass == Tag.closingTagClass: print 'closing'
    else: print "?"

    print "    tagNumber =", tag.tagNumber,
    if tag.tagClass == Tag.applicationTagClass:
        try:
            print tag._applicationTagName[tag.tagNumber]
        except:
            print "?"
    else: print

    print "    tagLVT =", tag.tagLVT,
    if tag.tagLVT != len(tag.tagData): print "(length does not match data)"
    else: print "(length match)"

    print "    tagData = '%s'" % (StringToHex(tag.tagData,'.'),)

#
#   TagList
#

class TagList:

    def __init__(self, arg=None):
        self.tagList = []

        if isinstance(arg, types.ListType):
            self.tagList = arg
        elif isinstance(arg, TagList):
            self.tagList = arg.tagList[:]
        elif isinstance(arg, PDUData):
            self.Decode(arg)

    def append(self, tag):
        self.tagList.append(tag)

    def extend(self, taglist):
        self.tagList.extend(taglist)

    def __getitem__(self, item):
        return self.tagList[item]

    def __len__(self):
        return len(self.tagList)

    def Peek(self):
        """Return the tag at the front of the list."""
        if self.tagList:
            tag = self.tagList[0]
        else:
            tag = None

        if _debug:
            print "(peek)", tag

        return tag

    def Push(self, tag):
        """Return a tag back to the front of the list."""
        if _debug:
            print "(push)", tag

        self.tagList = [tag] + self.tagList

    def Pop(self):
        """Remove the tag from the front of the list and return it."""
        if self.tagList:
            tag = self.tagList[0]
            del self.tagList[0]
        else:
            tag = None

        if _debug:
            print "(pop)", tag

        return tag

    def GetContext(self, context):
        """Return a tag or a list of tags context encoded."""
        # forward pass
        i = 0
        while i < len(self.tagList):
            tag = self.tagList[i]

            # skip application stuff
            if tag.tagClass == Tag.applicationTagClass:
                pass

            # check for context encoded atomic value
            elif tag.tagClass == Tag.contextTagClass:
                if tag.tagNumber == context:
                    return tag

            # check for context encoded group
            elif tag.tagClass == Tag.openingTagClass:
                keeper = tag.tagNumber == context
                rslt = []
                i += 1
                lvl = 0
                while i < len(self.tagList):
                    tag = self.tagList[i]
                    if tag.tagClass == Tag.openingTagClass:
                        lvl += 1
                    elif tag.tagClass == Tag.closingTagClass:
                        lvl -= 1
                        if lvl < 0: break

                    rslt.append(tag)
                    i += 1

                # make sure everything balances
                if lvl >= 0:
                    raise DecodingError, "mismatched open/close tags"

                # get everything we need?
                if keeper:
                    return TagList(rslt)
            else:
                raise DecodingError, "unexpected tag"

            # try the next tag
            i += 1

        # nothing found
        return None

    def Encode(self, pdu):
        """Encode the tag list into a PDU."""
        for tag in self.tagList:
            tag.Encode(pdu)

    def Decode(self, pdu):
        """Decode the tags from a PDU."""
        while pdu.pduData:
            self.tagList.append( Tag(pdu) )

#
#   DebugTagList
#

def DebugTagList(tags):
    print "DebugTagList", tags
    for tag in tags.tagList:
        print "   ", tag

#
#   Atomic
#

class Atomic:

    _appTag = None

    def __cmp__(self, other):
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # now compare the values
        if (self.value < other.value):
            return -1
        elif (self.value > other.value):
            return 1
        else:
            return 0

#
#   Null
#

class Null(Atomic):

    _appTag = Tag.nullAppTag

    def __init__(self, arg=None):
        self.value = ()

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.TupleType):
            if len(arg) != 0:
                raise ValueError, "empty tuple required"
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        tag.SetAppData(Tag.nullAppTag, '')

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.nullAppTag):
            raise ValueError, "null application tag required"

        self.value = ()

    def __str__(self):
        return "Null"

#
#   Boolean
#

class Boolean(Atomic):

    _appTag = Tag.booleanAppTag

    def __init__(self, arg=None):
        self.value = False

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.BooleanType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        tag.Set(Tag.applicationTagClass, Tag.booleanAppTag, int(self.value), '')

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.booleanAppTag):
            raise ValueError, "boolean application tag required"

        # get the data
        self.value = bool(tag.tagLVT)

    def __str__(self):
        return "Boolean(%s)" % (str(self.value), )

#
#   Unsigned
#

class Unsigned(Atomic):

    _appTag = Tag.unsignedAppTag

    def __init__(self,arg = None):
        self.value = 0L

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.IntType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"
            self.value = long(arg)
        elif isinstance(arg,types.LongType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # rip apart the number
        data = [ord(c) for c in struct.pack('>L',self.value)]

        # reduce the value to the smallest number of octets
        while (len(data) > 1) and (data[0] == 0):
            del data[0]

        # encode the tag
        tag.SetAppData(Tag.unsignedAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.unsignedAppTag):
            raise ValueError, "unsigned application tag required"

        # get the data
        rslt = 0L
        for c in tag.tagData:
            rslt = (rslt << 8) + ord(c)

        # save the result
        self.value = rslt

    def __str__(self):
        return "Unsigned(%s)" % (self.value, )

#
#   Integer
#

class Integer(Atomic):

    _appTag = Tag.integerAppTag

    def __init__(self,arg = None):
        self.value = 0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.IntType):
            self.value = arg
        elif isinstance(arg,types.LongType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # rip apart the number
        data = [ord(c) for c in struct.pack('>I',self.value)]

        # reduce the value to the smallest number of bytes, be
        # careful about sign extension
        if self.value < 0:
            while (len(data) > 1):
                if (data[0] != 255):
                    break
                if (data[1] < 128):
                    break
                del data[0]
        else:
            while (len(data) > 1):
                if (data[0] != 0):
                    break
                if (data[1] >= 128):
                    break
                del data[0]

        # encode the tag
        tag.SetAppData(Tag.integerAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.integerAppTag):
            raise ValueError, "integer application tag required"

        # get the data
        rslt = ord(tag.tagData[0])
        if (rslt & 0x80) != 0:
            rslt = (-1 << 8) | rslt

        for c in tag.tagData[1:]:
            rslt = (rslt << 8) | ord(c)

        # save the result
        self.value = rslt

    def __str__(self):
        return "Integer(%s)" % (self.value, )

#
#   Real
#

class Real(Atomic):

    _appTag = Tag.realAppTag

    def __init__(self, arg=None):
        self.value = 0.0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.FloatType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.realAppTag, struct.pack('>f',self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.realAppTag):
            raise ValueError, "real application tag required"

        # extract the data
        self.value = struct.unpack('>f',tag.tagData)[0]

    def __str__(self):
        return "Real(%g)" % (self.value,)

#
#   Double
#

class Double(Atomic):

    _appTag = Tag.doubleAppTag

    def __init__(self,arg = None):
        self.value = 0.0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.FloatType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.doubleAppTag, struct.pack('>d',self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.doubleAppTag):
            raise ValueError, "double application tag required"

        # extract the data
        self.value = struct.unpack('>d',tag.tagData)[0]

    def __str__(self):
        return "Double(%g)" % (self.value,)

#
#   OctetString
#

class OctetString(Atomic):

    _appTag = Tag.octetStringAppTag

    def __init__(self, arg=None):
        self.value = ''

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.StringType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.octetStringAppTag, self.value)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.octetStringAppTag):
            raise ValueError, "octet string application tag required"

        self.value = tag.tagData

    def __str__(self):
        return "OctetString(X'" + StringToHex(self.value) + "')"

#
#   CharacterString
#

class CharacterString(Atomic):

    _appTag = Tag.characterStringAppTag

    def __init__(self, arg=None):
        self.value = ''
        self.strEncoding = 0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.StringType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.characterStringAppTag, chr(self.strEncoding)+self.value)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.characterStringAppTag):
            raise ValueError, "character string application tag required"

        # extract the data
        self.strEncoding = tag.tagData[0]
        self.value = tag.tagData[1:]

    def __str__(self):
        return "CharacterString(%d," % (self.strEncoding,) + repr(self.value) + ")"

#
#   BitString
#

class BitString(Atomic):

    _appTag = Tag.bitStringAppTag
    bitNames = {}
    bitLen = 0

    def __init__(self, arg = None):
        self.value = [0] * self.bitLen

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.ListType):
            allInts = allStrings = True
            for elem in arg:
                allInts = allInts and ((elem == 0) or (elem == 1))
                allStrings = allStrings and self.bitNames.has_key(elem)

            if allInts:
                self.value = arg
            elif allStrings:
                for bit in arg:
                    bit = self.bitNames[bit]
                    if (bit < 0) or (bit > len(self.value)):
                        raise IndexError, "constructor element out of range"
                    self.value[bit] = 1
            else:
                raise TypeError, "invalid constructor list element(s)"
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # compute the unused bits to fill out the string
        _, used = divmod(len(self.value), 8)
        unused = used and (8 - used) or 0

        # start with the number of unused bits
        data = chr(unused)

        # build and append each packed octet
        bits = self.value + [0] * unused
        for i in range(0,len(bits),8):
            x = 0
            for j in range(0,8):
                x |= bits[i + j] << (7 - j)
            data += chr(x)

        # encode the tag
        tag.SetAppData(Tag.bitStringAppTag, data)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.bitStringAppTag):
            raise ValueError, "bit string application tag required"

        # extract the number of unused bits
        unused = ord(tag.tagData[0])

        # extract the data
        data = []
        for c in tag.tagData[1:]:
            x = ord(c)
            for i in range(8):
                if (x & (1 << (7 - i))) != 0:
                    data.append( 1 )
                else:
                    data.append( 0 )

        # trim off the unused bits
        self.value = data[:-unused]

    def __str__(self):
        # flip the bit names
        bitNames = {}
        for key, value in self.bitNames.iteritems():
            bitNames[value] = key

        # build a list of values and/or names
        valueList = []
        for value, index in zip(self.value,range(len(self.value))):
            if bitNames.has_key(index):
                if value:
                    valueList.append(bitNames[index])
                else:
                    valueList.append('!' + bitNames[index])
            else:
                valueList.append(str(value))

        # bundle it together
        return "BitString(" + ','.join(valueList) + ")"

    def __getitem__(self,bit):
        if isinstance(bit,types.IntType):
            pass
        elif isinstance(bit,types.StringType):
            if not self.bitNames.has_key(bit):
                raise IndexError, "unknown bit name '%s'" % (bit,)

            bit = self.bitNames[bit]
        else:
            raise TypeError, "bit index must be an integer or bit name"

        if (bit < 0) or (bit > len(self.value)):
            raise IndexError, "list index out of range"

        return self.value[bit]

    def __setitem__(self,bit,value):
        if isinstance(bit,types.IntType):
            pass
        elif isinstance(bit,types.StringType):
            if not self.bitNames.has_key(bit):
                raise IndexError, "unknown bit name '%s'" % (bit,)

            bit = self.bitNames[bit]
        else:
            raise TypeError, "bit index must be an integer or bit name"

        if (bit < 0) or (bit > len(self.value)):
            raise IndexError, "list index out of range"

        # funny cast to a bit
        self.value[bit] = value and 1 or 0

#
#   Enumerated
#

class Enumerated(Atomic):

    _appTag = Tag.enumeratedAppTag

    enumerations = {}
    _xlateTable = {}

    def __init__(self, arg=None):
        self.value = 0L

        # see if the class has a translate table
        if not self.__class__.__dict__.has_key('_xlateTable'):
            ExpandEnumerations(self.__class__)

        # initialize the object
        if arg is None:
            pass
        elif isinstance(arg, Tag):
            self.Decode(arg)
        elif isinstance(arg, types.IntType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"

            # convert it to a string if you can
            try: self.value = self._xlateTable[arg]
            except KeyError: self.value = long(arg)
        elif isinstance(arg, types.LongType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"

            # convert it to a string if you can
            try: self.value = self._xlateTable[arg]
            except KeyError: self.value = long(arg)
        elif isinstance(arg,types.StringType):
            if self._xlateTable.has_key(arg):
                self.value = arg
            else:
                raise ValueError, "undefined enumeration '%s'" % (arg,)
        else:
            raise TypeError, "invalid constructor datatype"

    def __getitem__(self, item):
        return self._xlateTable[item]

    def GetLong(self):
        if isinstance(self.value, types.LongType):
            return self.value
        elif isinstance(self.value, types.StringType):
            return long(self._xlateTable[self.value])
        else:
            raise TypeError, "%s is an invalid enumeration value datatype" % (type(self.value),)

    def keylist(self):
        """Return a list of names in order by value."""
        items = self.enumerations.items()
        items.sort(lambda a, b: cmp(a[1], b[1]))

        # last item has highest value
        rslt = [None] * (items[-1][1] + 1)

        # map the values
        for key, value in items:
            rslt[value] = key

        # return the result
        return rslt

    def __cmp__(self, other):
        """Special function to make sure comparisons are done in enumeration
        order, not alphabetic order."""
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # get the numeric version
        a = self.GetLong()
        b = other.GetLong()

        # now compare the values
        if (a < b):
            return -1
        elif (a > b):
            return 1
        else:
            return 0

    def Encode(self, tag):
        if isinstance(self.value, types.IntType):
            value = long(self.value)
        if isinstance(self.value, types.LongType):
            value = self.value
        elif isinstance(self.value, types.StringType):
            value = self._xlateTable[self.value]
        else:
            raise TypeError, "%s is an invalid enumeration value datatype" % (type(self.value),)

        # rip apart the number
        data = [ord(c) for c in struct.pack('>L',value)]

        # reduce the value to the smallest number of octets
        while (len(data) > 1) and (data[0] == 0):
            del data[0]

        # encode the tag
        tag.SetAppData(Tag.enumeratedAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.enumeratedAppTag):
            raise ValueError, "enumerated application tag required"

        # get the data
        rslt = 0L
        for c in tag.tagData:
            rslt = (rslt << 8) + ord(c)

        # convert it to a string if you can
        try: rslt = self._xlateTable[rslt]
        except KeyError: pass

        # save the result
        self.value = rslt

    def __str__(self):
        return "Enumerated(%s)" % (self.value,)

#
#   ExpandEnumerations
#

# translate lowers to uppers, keep digits, toss everything else
_ExpandTranslateTable = ''.join([c.isalnum() and c.upper() or '-' for c in [chr(cc) for cc in range(256)]])
_ExpandDeleteChars = ''.join([chr(cc) for cc in range(256) if not chr(cc).isalnum()])

def ExpandEnumerations(klass):
    # build a value dictionary
    xlateTable = {}
    for name, value in klass.enumerations.iteritems():
        # save the results
        xlateTable[name] = value
        xlateTable[value] = name

        # translate the name for a class const
        name = name.translate(_ExpandTranslateTable, _ExpandDeleteChars)

        # save the name in the class
        setattr(klass, name, value)

    # save the dictionary in the class
    setattr(klass, '_xlateTable', xlateTable)

#
#   Date
#

class Date(Atomic):

    _appTag = Tag.dateAppTag

    DONT_CARE = 255

    def __init__(self, arg=None, year=255, month=255, day=255, dayOfWeek=255):
        self.value = (year, month, day, dayOfWeek)

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg, types.TupleType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Now(self):
        tup = time.gmtime()

        self.value = (tup[0]-1900, tup[1], tup[2], tup[6] + 1)

        return self

    def CalcDayOfWeek(self):
        """Calculate the correct day of the week."""
        # rip apart the value
        year, month, day, dayOfWeek = self.value

        # make sure all the components are defined
        if (year != 255) and (month != 255) and (day != 255):
            today = time.mktime( (year + 1900, month, day, 0, 0, 0, 0, 0, -1) )
            dayOfWeek = time.gmtime(today)[6] + 1

        # put it back together
        self.value = (year, month, day, dayOfWeek)

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.dateAppTag, ''.join(chr(c) for c in self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.dateAppTag):
            raise ValueError, "date application tag required"

        # rip apart the data
        self.value = tuple(ord(c) for c in tag.tagData)

    def __str__(self):
        # rip it apart
        year, month, day, dayOfWeek = self.value

        rslt = "Date("
        if month == 255:
            rslt += "*/"
        else:
            rslt += "%d/" % (month,)
        if day == 255:
            rslt += "*/"
        else:
            rslt += "%d/" % (day,)
        if year == 255:
            rslt += "* "
        else:
            rslt += "%d " % (year + 1900,)
        if dayOfWeek == 255:
            rslt += "*)"
        else:
            rslt += ['','Mon','Tue','Wed','Thu','Fri','Sat','Sun'][dayOfWeek] + ")"

        return rslt

#
#   Time
#

class Time(Atomic):

    _appTag = Tag.timeAppTag

    DONT_CARE = 255

    def __init__(self, arg=None, hour=255, minute=255, second=255, hundredth=255):
        # put it together
        self.value = (hour, minute, second, hundredth)

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg, types.TupleType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Now(self):
        now = time.time()
        tup = time.gmtime(now)

        self.value = (tup[3], tup[4], tup[5], int((now - int(now)) * 100))

        return self

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.timeAppTag, ''.join(chr(c) for c in self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.timeAppTag):
            raise ValueError, "time application tag required"

        # rip apart the data
        self.value = tuple(ord(c) for c in tag.tagData)

    def __str__(self):
        # rip it apart
        hour, minute, second, hundredth = self.value

        rslt = "Time("
        if hour == 255:
            rslt += "*:"
        else:
            rslt += "%02d:" % (hour,)
        if minute == 255:
            rslt += "*:"
        else:
            rslt += "%02d:" % (minute,)
        if second == 255:
            rslt += "*."
        else:
            rslt += "%02d." % (second,)
        if hundredth == 255:
            rslt += "*)"
        else:
            rslt += "%02d)" % (hundredth,)

        return rslt

#
#   ObjectType
#

class ObjectType(Enumerated):
    enumerations = \
        { 'analog-input':0 \
        , 'analog-output':1 \
        , 'analog-value':2 \
        , 'binary-input':3 \
        , 'binary-output':4 \
        , 'binary-value':5 \
        , 'calendar':6 \
        , 'command':7 \
        , 'device':8 \
        , 'event-enrollment':9 \
        , 'file':10 \
        , 'group':11 \
        , 'loop':12 \
        , 'multi-state-input':13 \
        , 'multi-state-output':14 \
        , 'notification-class':15 \
        , 'program':16 \
        , 'schedule':17 \
        , 'averaging':18 \
        , 'multi-state-value':19 \
        , 'trend-log':20 \
        , 'life-safety-point':21 \
        , 'life-safety-zone':22 \
        , 'accumulator':23 \
        , 'pulse-converter':24 \
        }

ExpandEnumerations(ObjectType)

#
#   ObjectIdentifier
#

class ObjectIdentifier(Atomic):

    _appTag = Tag.objectIdentifierAppTag
    objectTypeClass = ObjectType

    def __init__(self, *args):
        self.value = ('analog-input', 0)

        if len(args) == 0:
            pass
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, Tag):
                self.Decode(arg)
            elif isinstance(arg, types.IntType):
                self.SetLong(long(arg))
            elif isinstance(arg, types.LongType):
                self.SetLong(arg)
            elif isinstance(arg, types.TupleType):
                self.SetTuple(*arg)
            else:
                raise TypeError, "invalid constructor datatype"
        elif len(args) == 2:
            self.SetTuple(*args)
        else:
            raise ValueError, "invalid constructor parameters"

    def SetTuple(self, objType, objInstance):
        # allow a type name as well as an integer
        if isinstance(objType, types.IntType):
            try:
                # try and make it pretty
                objType = self.objectTypeClass()[objType]
            except KeyError:
                pass
        elif isinstance(objType, types.StringType):
            try:
                # make sure the type is known
                self.objectTypeClass()[objType]
            except KeyError:
                raise ValueError, "unrecognized object type '%s'" % (objType,)
        else:
            raise TypeError, "invalid datatype for objType"

        # pack the components together
        self.value = (objType, objInstance)

    def GetTuple(self):
        """Return the unsigned integer tuple of the identifier."""
        objType, objInstance = self.value

        if isinstance(objType, types.IntType):
            pass
        elif isinstance(objType, types.LongType):
            objType = int(objType)
        elif isinstance(objType, types.StringType):
            # turn it back into an integer
            objType = self.objectTypeClass()[objType]
        else:
            raise TypeError, "invalid datatype for objType"

        # pack the components together
        return (objType, objInstance)

    def SetLong(self, value):
        # suck out the type
        objType = (value >> 22) & 0x03FF
        try:
            # try and make it pretty
            objType = self.objectTypeClass()[objType]
        except IndexError:
            pass

        # suck out the instance
        objInstance = value & 0x003FFFFF

        # save the result
        self.value = (objType, objInstance)

    def GetLong(self):
        """Return the unsigned integer representation of the identifier."""
        objType, objInstance = self.GetTuple()

        # pack the components together
        return long((objType << 22) + objInstance)

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.objectIdentifierAppTag, struct.pack('>L',self.GetLong()))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.objectIdentifierAppTag):
            raise ValueError, "object identifier application tag required"

        # extract the data
        self.SetLong( struct.unpack('>L',tag.tagData)[0] )

    def __str__(self):
        # rip it apart
        objType, objInstance = self.value

        if isinstance(objType, types.StringType):
            typestr = objType
        elif objType < 0:
            typestr = "Bad %d" % (objType,)
        elif self.objectTypeClass._xlateTable.has_key(objType):
            typestr = self.objectTypeClass._xlateTable[objType]
        elif (objType < 128):
            typestr = "Reserved %d" % (objType,)
        else:
            typestr = "Vendor %d" % (objType,)
        return "ObjectIdentifier(%s,%d)" % (typestr, objInstance)

    def __hash__(self):
        return hash(self.value)

    def __cmp__(self, other):
        """Special function to make sure comparisons are done in enumeration
        order, not alphabetic order."""
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # get the numeric version
        a = self.GetLong()
        b = other.GetLong()

        # now compare the values
        if (a < b):
            return -1
        elif (a > b):
            return 1
        else:
            return 0

#
#   Application Tag Classes
#
#   This list is set in the Tag class so that the AppToObject
#   function can return one of the appliction datatypes.  It
#   can't be provided in the Tag class definition because the
#   classes aren't defined yet.
#

Tag._applicationTagClass = \
    [ Null, Boolean, Unsigned, Integer
    , Real, Double, OctetString, CharacterString
    , BitString, Enumerated, Date, Time
    , ObjectIdentifier, None, None, None
    ]

#
#   Element
#

class Element:

    def __init__(self, name, klass, context=None, optional=False):
        self.name = name
        self.klass = klass
        self.context = context
        self.optional = optional

#
#   Sequence
#

class Sequence:

    sequenceElements = []

    def __init__(self, **kwargs):
        for element in self.sequenceElements:
            setattr(self, element.name, kwargs.get(element.name, None))

    def Encode(self, taglist):
        if _debug:
            print "%s.Encode" % (self.__class__.__name__,), taglist
        global _SequenceOfClasses

        for element in self.sequenceElements:
            value = getattr(self, element.name, None)
            if element.optional and value is None:
                continue
            if not element.optional and value is None:
                raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)
            if _SequenceOfClasses.has_key(element.klass):
                # might need to encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                if _debug:
                    print "    - build sequence helper", element.klass, value
                helper = element.klass(value)

                # encode the value
                helper.Encode(taglist)

                # might need to encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
            elif issubclass(element.klass, Atomic):
                # a helper cooperates between the atomic value and the tag
                if _debug:
                    print "    - build helper", element.klass, value
                helper = element.klass(value)

                # build a tag and encode the data into it
                tag = Tag()
                helper.Encode(tag)

                # convert it to context encoding iff necessary
                if element.context is not None:
                    tag = tag.AppToCtx(element.context)

                # now append the tag
                taglist.append(tag)
            elif isinstance(value, element.klass):
                # might need to encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                # encode the value
                value.Encode(taglist)

                # might need to encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
            else:
                raise TypeError, "'%s' must be a %s" % (element.name, element.klass.__name__)

    def Decode(self, taglist):
        if _debug:
            print "%s.Decode" % (self.__class__.__name__,), taglist

        for element in self.sequenceElements:
            tag = taglist.Peek()

            # no more elements
            if tag is None:
                if not element.optional:
                    raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)

                # omitted optional element
                setattr(self, element.name, None)

            # we have been enclosed in a context
            elif tag.tagClass == Tag.closingTagClass:
                if not element.optional:
                    raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)

                # omitted optional element
                setattr(self, element.name, None)

            # check for a sequence element
            elif _SequenceOfClasses.has_key(element.klass):
                # check for context encoding
                if element.context is not None:
                    if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected opening tag %d" % (element.name, element.context)
                        else:
                            # omitted optional element
                            setattr(self, element.name, [])
                            continue
                    taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass()
                helper.Decode(taglist)

                # now save the value
                setattr(self, element.name, helper.value)

                # check for context closing tag
                if element.context is not None:
                    tag = taglist.Pop()
                    if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                        raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

            # check for an atomic element
            elif issubclass(element.klass, Atomic):
                # convert it to application encoding
                if element.context is not None:
                    if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected context tag %d" % (element.name, element.context)
                        else:
                            setattr(self, element.name, None)
                            continue
                    tag = tag.CtxToApp(element.klass._appTag)
                else:
                    if tag.tagClass != Tag.applicationTagClass or tag.tagNumber != element.klass._appTag:
                        if not element.optional:
                            raise DecodingError, "'%s' expected application tag %s" % (element.name, Tag._applicationTagName[element.klass._appTag])
                        else:
                            setattr(self, element.name, None)
                            continue

                # consume the tag
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass(tag)

                # now save the value
                setattr(self, element.name, helper.value)

            # some kind of structure
            else:
                if element.context is not None:
                    if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected opening tag %d" % (element.name, element.context)
                        else:
                            setattr(self, element.name, None)
                            continue
                    taglist.Pop()

                try:
                    # make a backup of the tag list in case the structure manages to
                    # decode some content but not all of it.  This is not supposed to
                    # happen if the ASN.1 has been formed correctly.
                    backup = taglist.tagList[:]

                    # build a value and decode it
                    value = element.klass()
                    value.Decode(taglist)

                    # save the result
                    setattr(self, element.name, value)
                except DecodingError:
                    # if the context tag was matched, the substructure has to be decoded
                    # correctly.
                    if element.context is None and element.optional:
                        # omitted optional element
                        setattr(self, element.name, None)

                        # restore the backup
                        taglist.tagList = backup
                    else:
                        raise

                if element.context is not None:
                    tag = taglist.Pop()
                    if (not tag) or tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                        raise DecodingError, "'%s' expected closing tag %d" % (element.name, element.context)

#
#   SequenceOf
#

_SequenceOfMap = {}
_SequenceOfClasses = {}

def SequenceOf(klass):
    """Function to return a class that can encode and decode a list of
    some other type."""
    global _SequenceOfMap
    global _SequenceOfClasses

    # if this has already been built, return the cached one
    if _SequenceOfMap.has_key(klass):
        return _SequenceOfMap[klass]

    # no SequenceOf(SequenceOf(...)) allowed
    if _SequenceOfClasses.has_key(klass):
        raise TypeError, "nested sequences disallowed"

    # define a generic class for lists
    class SequenceOf:

        subtype = None

        def __init__(self,value=None):
            if value is None:
                self.value = []
            elif isinstance(value,types.ListType):
                self.value = value
            else:
                raise TypeError, "invalid constructor datatype"

        def append(self, value):
            if issubclass(self.subtype, Atomic):
                pass
            elif not isinstance(value, self.subtype):
                raise TypeError, "%s value required" % (value, self.subtype.__name__,)
            self.value.append(value)

        def __getitem__(self, item):
            return self.value[item]

        def __len__(self):
            return len(self.value)

        def Encode(self, taglist):
            if _debug:
                print "%s.Encode" % (self.__class__.__name__,), taglist
            for value in self.value:
                if issubclass(self.subtype, Atomic):
                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(value)

                    # build a tag and encode the data into it
                    tag = Tag()
                    helper.Encode(tag)

                    # now encode the tag
                    taglist.append(tag)
                elif isinstance(value, self.subtype):
                    # it must have its own encoder
                    value.Encode(taglist)
                else:
                    raise TypeError, "%s must be a %s" % (value, self.subtype.__name__)

        def Decode(self, taglist):
            if _debug:
                print "%s.Decode" % (self.__class__.__name__,), taglist

            while len(taglist) != 0:
                tag = taglist.Peek()
                if tag.tagClass == Tag.closingTagClass:
                    return

                if issubclass(self.subtype, Atomic):
                    if _debug:
                        print "    - building helper", self.subtype, tag
                    taglist.Pop()

                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(tag)

                    # save the value
                    self.value.append(helper.value)
                else:
                    if _debug:
                        print "    - building value", self.subtype
                    # build an element
                    value = self.subtype()

                    # let it decode itself
                    value.Decode(taglist)

                    # save what was built
                    self.value.append(value)

    # constrain it to a list of a specific type of item
    setattr(SequenceOf, 'subtype', klass)
    SequenceOf.__name__ = 'SequenceOf(%s.%s)' % (klass.__module__, klass.__name__)

    # cache this type
    _SequenceOfMap[klass] = SequenceOf
    _SequenceOfClasses[SequenceOf] = 1

    # return this new type
    return SequenceOf

def DebugSequenceOfClasses():
    print "DebugSequenceOfClasses"
    for klass in _SequenceOfClasses:
        print "   ", klass

#
#   Choice
#

class Choice:

    choiceElements = []

    def __init__(self, **kwargs):
        for element in self.choiceElements:
            setattr(self, element.name, kwargs.get(element.name, None))

    def Encode(self, taglist):
        if _debug:
            print "%s.Encode" % (self.__class__.__name__,), taglist

        for element in self.choiceElements:
            value = getattr(self, element.name, None)
            if value is None:
                continue

            if issubclass(element.klass,Atomic):
                # a helper cooperates between the atomic value and the tag
                helper = element.klass(value)

                # build a tag and encode the data into it
                tag = Tag()
                helper.Encode(tag)

                # convert it to context encoding
                if element.context is not None:
                    tag = tag.AppToCtx(element.context)

                # now encode the tag
                taglist.append(tag)
                break

            elif isinstance(value, element.klass):
                # encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                # encode the value
                value.Encode(taglist)

                # encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
                break

            else:
                raise TypeError, "'%s' must be a %s" % (element.name, element.klass.__name__)
        else:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

    def Decode(self, taglist):
        if _debug:
            print "%s.Decode" % (self.__class__.__name__,), taglist

        # peek at the element
        tag = taglist.Peek()
        if tag is None:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)
        if tag.tagClass == Tag.closingTagClass:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

        # keep track of which one was found
        foundElement = {}

        # figure out which choice it is
        for element in self.choiceElements:
            if _debug:
                print "    - checking choice", element.name

            # check for a sequence element
            if _SequenceOfClasses.has_key(element.klass):
                # check for context encoding
                if element.context is None:
                    raise NotImplementedError, "choice of a SequenceOf must be context encoded"
                # match the context tag number
                if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                    continue
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass()
                helper.Decode(taglist)

                # now save the value
                foundElement[element.name] = helper.value

                # check for context closing tag
                tag = taglist.Pop()
                if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                    raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

                # done
                if _debug:
                    print "    - found choice (sequence)"
                break

            # check for an atomic element
            elif issubclass(element.klass, Atomic):
                # convert it to application encoding
                if element.context is not None:
                    if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                        continue
                    tag = tag.CtxToApp(element.klass._appTag)
                else:
                    if tag.tagClass != Tag.applicationTagClass or tag.tagNumber != element.klass._appTag:
                        continue

                # consume the tag
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass(tag)

                # now save the value
                foundElement[element.name] = helper.value

                # done
                if _debug:
                    print "    - found choice (atomic)"
                break

            # some kind of structure
            else:
                # check for context encoding
                if element.context is None:
                    raise NotImplementedError, "choice of non-atomic data must be context encoded"
                if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                    continue
                taglist.Pop()

                # build a value and decode it
                value = element.klass()
                value.Decode(taglist)

                # now save the value
                foundElement[element.name] = value

                # check for the correct closing tag
                tag = taglist.Pop()
                if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                    raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

                # done
                if _debug:
                    print "    - found choice (structure)"
                break
        else:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

        # now save the value and None everywhere else
        for element in self.choiceElements:
            setattr(self, element.name, foundElement.get(element.name, None))

#
#   Any
#

class Any:

    def __init__(self, *args):
        self.tagList = []

        # cast in the args
        for arg in args:
            self.CastIn(arg)

    def Encode(self, taglist):
        if _debug:
            print "Any.Encode", taglist

        taglist.extend(self.tagList)

    def Decode(self, taglist):
        if _debug:
            print "Any.Decode", taglist

        lvl = 0
        while len(taglist) != 0:
            tag = taglist.Peek()
            if tag.tagClass == Tag.openingTagClass:
                lvl += 1
            elif tag.tagClass == Tag.closingTagClass:
                lvl -= 1
                if lvl < 0: break

            self.tagList.append(taglist.Pop())

        # make sure everything balances
        if lvl > 0:
            raise DecodingError, "mismatched open/close tags"

    def CastIn(self, element):
        """Encode the element into the internal tag list."""
        if _debug:
            print "Any.CastIn", element

        t = TagList()
        if isinstance(element, Atomic):
            tag = Tag()
            element.Encode(tag)
            t.append(tag)
        else:
            element.Encode(t)

        self.tagList.extend(t.tagList)

    def CastOut(self, klass):
        """Interpret the content as a particular class."""
        if _debug:
            print "Any.CastOut", klass

        # check for a sequence element
        if _SequenceOfClasses.has_key(klass):
            # build a sequence helper
            helper = klass()

            # make a copy of the tag list
            t = TagList(self.tagList[:])

            # let it decode itself
            helper.Decode(t)

            # make sure everything was consumed
            if len(t) != 0:
                raise DecodingError, "incomplete cast"

            # return what was built
            return helper.value

        elif issubclass(klass, Atomic):
            # make sure there's only one piece
            if len(self.tagList) == 0:
                raise DecodingError, "missing cast component"
            if len(self.tagList) > 1:
                raise DecodingError, "too many cast components"

            if _debug:
                print "    - building helper", klass

            # a helper cooperates between the atomic value and the tag
            helper = klass(self.tagList[0])

            # return the value
            return helper.value

        else:
            if _debug:
                print "    - building value", klass

            # build an element
            value = klass()

            # make a copy of the tag list
            t = TagList(self.tagList[:])

            # let it decode itself
            value.Decode(t)

            # make sure everything was consumed
            if len(t) != 0:
                raise DecodingError, "incomplete cast"

            # return what was built
            return value

#
#   PDU
#

class PDU(PDUData):

    def __init__(self, *args):
        PDUData.__init__(self, *args)
        self.pduSource = None
        self.pduDestination = None
        self.pduExpectingReply = 0                          # see 6.2.2 (1 or 0)
        self.pduNetworkPriority = 0                         # see 6.2.2 (0..3)

#
#   DebugPDUContents
#

def DebugPDUContents(pdu):
    """Print the contents of a message."""
    print "    source =", pdu.pduSource
    print "    destination =", pdu.pduDestination
    print "    expecting reply =", pdu.pduExpectingReply
    print "    network priority =", pdu.pduNetworkPriority
    print "    data =", StringToHex(pdu.pduData,'.')

#
#   Client
#

class Client:

    def __init__(self):
        self.clientPeer = None

    def Request(self,*args,**kwargs):
        assert self.clientPeer, "unbound client"
        self.clientPeer.Indication(*args,**kwargs)

    def Confirmation(self,*args,**kwargs):
        assert 0, "Confirmation() must be overridden"
        
#
#   Server
#

class Server:

    def __init__(self):
        self.serverPeer = None

    def Indication(self,*args,**kwargs):
        assert 0, "Indication() must be overridden"
        
    def Response(self,*args,**kwargs):
        assert self.serverPeer, "unbound server"
        self.serverPeer.Confirmation(*args,**kwargs)
        
#
#   AppClient
#

class AppClient:

    def __init__(self):
        self.appClientPeer = None

    def AppRequest(self,*args,**kwargs):
        assert self.appClientPeer, "unbound application client"
        self.appClientPeer.AppIndication(*args,**kwargs)

    def AppConfirmation(self,*args,**kwargs):
        assert 0, "AppConfirmation must be overridden"

#
#   AppServer
#

class AppServer:

    def __init__(self):
        self.appServerPeer = None

    def AppIndication(self,*args,**kwargs):
        assert 0, "AppIndication() must be overridden"

    def AppResponse(self,*args,**kwargs):
        assert self.appServerPeer, "unbound application server"
        self.appServerPeer.AppConfirmation(*args,**kwargs)

#
#   Port
#

class Port(Server):

    def __init__(self):
        self.portStatus = 'unbound port'
        self.portLocalAddress = None
        self.portBroadcastAddress = None
    
    def SendData(self,data):
        pass

    def FilterData(self,data,sending):
        pass

    def Indication(self,pdu):
        assert 0, "Indication() must be overridden"

#
#   Task
#

gTaskManager = None

class Task:
    oneShotTask         = 0     # run once
    oneShotDeleteTask   = 1     # not completely necessary, but might help with garbage collection
    recurringTask       = 2     # run, then reschedule

    _taskTypes = ['oneShotTask', 'oneShotDeleteTask', 'recurringTask']

    def __init__(self, typ = 0, delay = 0, tim = 0):
        self.taskType = typ
        self.taskInterval = delay
        self.taskTime = tim
        self.isScheduled = False

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = Task._taskTypes[self.taskType]
        except:
            stype = str(self.taskType)

        return '<%s(%s) instance at 0x%08x>' % (sname, stype, xid)

    def InstallTask(self, typ = None, delay = None, tim = None):
        global gTaskManager

        # override the type
        if typ is not None:
            self.taskType = typ

        # override the delay
        if delay is not None:
            self.taskInterval = delay

        # if the time is specified, schedule it for that time, otherwise
        # schedule it to go off after its interval (which may be zero)
        if tim is not None:
            self.taskTime = tim
        else:
            self.taskTime = time.time() + (self.taskInterval / 1000)

        # pass along to the task manager
        gTaskManager.InstallTask(self)

    def SuspendTask(self):
        global gTaskManager

        gTaskManager.SuspendTask(self)

    def ResumeTask(self):
        global gTaskManager

        gTaskManager.ResumeTask(self)

    def ProcessTask(self):
        assert 0, "ProcessTask() must be overridden"

#
#   TaskManager
#

class TaskManager(CSThread.Thread):

    def __init__(self):
        global gTaskManager

        assert not gTaskManager, "task manager already created"
        gTaskManager = self

        """Initialize a new event queue."""
        CSThread.Thread.__init__(self,"BACnet Task Manager")
        self.mutex = thread.allocate_lock()
        self.event = threading.Event()
        self.tasks = []
        self.maxWaitTime = 60

        self.go = 0
        self.setDaemon(1)

    def run(self):
        """Monitor the pending elements for those that have expired
        and transfer them to the avail queue."""
        self.go = 1
        while self.go:
            task, delta = self.GetNextTask()

            if task:
                self.ProcessTask(task)

            if delta:
                self.event.wait(min(self.maxWaitTime,delta))
                self.event.clear()

    def halt(self):
        """Stop the thread."""
        self.go = 0
        self.event.set()

    def InstallTask(self,task):
        if (task.taskType == task.recurringTask) and (task.taskInterval == 0):
            raise ValueError, "zero interval recurring tasks not supported"

        # lock down the task list
        self.mutex.acquire()

        # find out where to insert this guy
        for i in xrange(len(self.tasks)):
            if task.taskTime < self.tasks[i].taskTime:
                self.tasks[i:i] = [task]
                break
        else:
            self.tasks.append( task )

        # ready to rock
        task.isScheduled = True

        # release the mutex
        self.mutex.release()

        # set the event to wake up the manager
        self.event.set()

    def SuspendTask(self,task):
        # lock down the task list
        self.mutex.acquire()

        # remove this guy
        try:
            self.tasks.remove(task)
        except ValueError:
            pass

        # no longer scheduled
        task.isScheduled = False

        # release the mutex
        self.mutex.release()

        # set the event to wake up the manager
        self.event.set()

    def ResumeTask(self,task):
        # just re-install it
        self.InstallTask(task)

    def GetNextTask(self):
        """Get the next task and how long to wait for the next one."""
        # lock down the task list
        self.mutex.acquire()

        # get the time
        now = time.time()

        task = None
        delta = self.maxWaitTime

        if self.tasks:
            # how long before the first thing is supposed to run
            delta = max(0, self.tasks[0].taskTime - now)

            # do it now
            if delta == 0:
                task = self.tasks[0]
                del self.tasks[0]
                task.isScheduled = False

                if self.tasks:
                    # how long before the next thing is supposed to run
                    delta = max(0, self.tasks[0].taskTime - now)

        # release the mutex
        self.mutex.release()

        # return the task to run and how long to wait for the next one
        return (task, delta)

    def ProcessTask(self,task):
        # process the task
        task.ProcessTask()

        # see if it should be reschedule
        if task.taskType == task.oneShotTask:
            pass
        elif task.taskType == task.oneShotDeleteTask:
            del task
        elif task.taskType == task.recurringTask:
            task.taskTime += (task.taskInterval / 1000.0)
            self.InstallTask( task )

#
#   VLANMessage
#

class VLANMessage(Task,PDU):
    """VLANMessage objects are used to transfer content from the VLAN port threads
    to the task manager thread."""

    def __init__(self,lan):
        Task.__init__(self, Task.oneShotDeleteTask)
        PDU.__init__(self)

        self.lan = lan

    def ProcessTask(self):
        if _debugVLAN:
            print
            print
            print "-" * 80
            print

        self.lan.ProcessPDU(self)

#
#   VLAN
#

class VLAN:

    def __init__(self, dropPercent=0):
        if _debugVLAN:
            print self, "VLAN.__init__"

        self.nodes = []
        self.dropPercent = dropPercent

    def AddNode(self, node):
        if _debugVLAN:
            print self, "VLAN.AddNode", node

        self.nodes.append(node)
        node.lan = self

    def RemoveNode(self, node):
        if _debugVLAN:
            print self, "VLAN.RemoveNode", node

        self.nodes.remove(node)
        node.lan = None

    def ProcessPDU(self, pdu):
        """Process a PDU from a station."""
        if _debugVLAN:
            print self, "VLAN.ProcessPDU", pdu
            DebugPDUContents(pdu)

        if self.dropPercent != 0:
            if (random.random() * 100.0) < self.dropPercent:
                if _debugVLAN:
                    print "    - *** packet dropped ***"
                return

        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            for n in self.nodes:
                if not(pdu.pduSource == n.portLocalAddress):
                    n.Response(pdu)
        else:
            for n in self.nodes:
                if n.promiscuous or (pdu.pduDestination == n.portLocalAddress):
                    n.Response(pdu)

#
#   VLANPort
#

class VLANPort(Port):

    def __init__(self, addr, lan = None, promiscuous = False):
        Port.__init__(self)
        if _debugVLAN:
            print self, "VLANPort.__init__", addr, lan

        self.portStatus = 'unbound'
        self.portLocalAddress = addr
        self.portBroadcastAddress = LocalBroadcast()

        # bind to a lan if it was provided
        if lan:
            self.Bind(lan)

        # might receive all packets
        self.promiscuous = promiscuous

    def Bind(self, lan):
        """Bind to a LAN."""
        if _debugVLAN:
            print self, "VLANPort.Bind", lan

        lan.AddNode(self)
        self.portStatus = 'bound'

    def Indication(self,pdu):
        """Send a message."""
        if _debugVLAN:
            print self, "VLANPort.Indication", pdu

        # make sure we're connected
        if not self.lan:
            raise ConfigurationError, "node not connected"

        # build a VLAN message which will be scheduled
        newpdu = VLANMessage(self.lan)
        newpdu.pduSource = self.portLocalAddress
        newpdu.pduDestination = pdu.pduDestination
        newpdu.pduData = pdu.pduData
        newpdu.pduExpectingReply = pdu.pduExpectingReply
        newpdu.pduNetworkPriority = pdu.pduNetworkPriority

        # install it
        newpdu.InstallTask()

#
#   BVLLPDU
#

class BVLLPDU(PDU):
    bvlcResult                              = 0x00
    bvlcWriteBroadcastDistributionTable     = 0x01
    bvlcReadBroadcastDistributionTable      = 0x02
    bvlcReadBroadcastDistributionTableAck   = 0x03
    bvlcForwardedNPDU                       = 0x04
    bvlcRegisterForeignDevice               = 0x05
    bvlcReadForeignDeviceTable              = 0x06
    bvlcReadForeignDeviceTableAck           = 0x07
    bvlcDeleteForeignDeviceTableEntry       = 0x08
    bvlcDistributeBroadcastToNetwork        = 0x09
    bvlcOriginalUnicastNPDU                 = 0x0A
    bvlcOriginalBroadcastNPDU               = 0x0B

    def __init__(self,*args):
        PDU.__init__(self,*args)
        self.bvlcFunction = None
        self.bvlcAddress = None
        self.bvlcResultCode = None

    def Encode(self, pdu):
        """Encode the contents of the BVLLPDU into the PDU."""
        if _debug:
            print "BVLLPDU.Encode", pdu

        raise exceptions.NotImplementedError, "BVLLPDU.Encode is not implemented"

    def Decode(self,pdu):
        """Decode the contents of the PDU into the BVLLPDU."""
        if _debug:
            print "BVLLPDU.Decode", pdu

        raise exceptions.NotImplementedError, "BVLLPDU.Decode is not implemented"

#
#   IPMessage
#

class IPMessage(Task,PDU):
    """IPMessage objects are used to transfer content from the port threads
    to the task manager thread."""

    def __init__(self,server):
        Task.__init__(self, Task.oneShotTask)
        PDU.__init__(self)

        self.server = server

    def ProcessTask(self):
        self.server.Response(self)

#
#   IPBroadcastListener
#

class IPBroadcastListener(CSThread.Thread):

    def __init__(self, twin, localAddress, broadcastAddress):
        CSThread.Thread.__init__(self,"BACnet IPBroadcastListener '%s'" % (broadcastAddress,))

        if _debug:
            print self, "IPBroadcastListener.__init__", twin, localAddress, broadcastAddress

        self.portTwin = twin
        self.portLocalAddress = localAddress
        self.portBroadcastAddress = broadcastAddress

        self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.socket.bind( self.portBroadcastAddress )

        self.go = 0
        self.setDaemon(1)

    def run(self):
        """Listen for incoming broadcast packets and make requests out of them."""
        self.go = 1
        while self.go:
            data, addr = self.socket.recvfrom( 1536 )
            if (not data):
                break

            # if the source is us, drop it
            if addr == self.portLocalAddress:
                continue

            # create a message to process
            pdu = IPMessage(self.portTwin)
            pdu.pduData = data
            pdu.pduSource = Address(addr)
            pdu.pduDestination = LocalBroadcast()

            # install it
            pdu.InstallTask()

        self.socket.close()

    def halt(self):
        """Stop the thread."""
        self.go = 0

#
#   IPPort
#

class IPPort(Port,CSThread.Thread):

    def __init__(self,addr):
        Port.__init__(self)
        CSThread.Thread.__init__(self,"BACnet IPPort '%s'" % (addr,))

        if _debug:
            print self, "IPPort.__init__", addr

        self.portAddress = addr
        self.portStatus = 'ready'
        self.portLocalAddress = self.portAddress.addrTuple

        # figure out which broadcast address to use
        if self.portAddress.addrMask == -1L:
            self.portBroadcastAddress = ('255.255.255.255', self.portAddress.addrPort)
        else:
            self.portBroadcastAddress = self.portAddress.addrBroadcastTuple

        if _debug:
            print "    - local address", self.portLocalAddress
            print "    - broadcast address", self.portBroadcastAddress

        self.socket = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_BROADCAST, 1 )
        self.socket.bind( self.portLocalAddress )

        self.broadcastListener = IPBroadcastListener( self, self.portLocalAddress, self.portBroadcastAddress )

        self.go = 0
        self.setDaemon(1)

    def run(self):
        """Listen for incoming packets and make requests out of them."""
        self.go = 1
        while self.go:
            data, addr = self.socket.recvfrom( 1536 )
            if (not data):
                break

            # if the source is us, drop it
            if addr == self.portLocalAddress:
                continue

            # create a message to process
            pdu = IPMessage(self)
            pdu.pduData = data
            pdu.pduSource = Address(addr)
            pdu.pduDestination = Address(self.portLocalAddress)

            # install it
            pdu.InstallTask()

        self.socket.close()

    def Indication(self,pdu):
        if _debug:
            print self, "IPPort.Indication"

        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            if _debug:
                print "    - local broadcast"

            addr = self.portBroadcastAddress
        elif pdu.pduDestination.addrType == Address.localStationAddr:
            if _debug:
                print "    - local station"

            addr = IPAddrUnpack( pdu.pduDestination.addrAddr )
        else:
            if _debug:
                print "    - unknown address type", pdu.pduDestination.addrType
            return

        self.socket.sendto(pdu.pduData,addr)

    def halt(self):
        """Stop the thread."""
        self.go = 0

#
#   IPDirect
#

class IPDirect(Client,Server):

    def __init__(self):
        pass

    def Indication(self,pdu):
        if _debug:
            print self, "IPDirect.Indication"

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            if _debug:
                print "    - local broadcast"

            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcOriginalBroadcastNPDU )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
        elif pdu.pduDestination.addrType == Address.localStationAddr:
            if _debug:
                print "    - local station"

            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcOriginalUnicastNPDU )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
        else:
            if _debug:
                print "    - unknown address type", pdu.pduDestination.addrType
            return

        self.Request(newpdu)

    def Confirmation(self,pdu):
        if _debug:
            print self, "IPDirect.Confirmation"

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        hdr = pdu.Get()
        if hdr != 0x81:
            if _debug:
                print "    - not a BVLL header"
            return

        hdr = pdu.Get()
        if hdr == BVLLPDU.bvlcOriginalUnicastNPDU:
            if _debug:
                print "    - original unicast"

            datalen = pdu.GetShort()
        elif hdr == BVLLPDU.bvlcOriginalBroadcastNPDU:
            if _debug:
                print "    - original broadcast"

            newpdu.pduDestination = LocalBroadcast()
            datalen = pdu.GetShort()
        elif hdr == BVLLPDU.bvlcForwardedNPDU:
            if _debug:
                print "    - forwarded NPDU"

            datalen = pdu.GetShort()
            newpdu.pduSource = LocalStation(pdu.GetData(6))
            newpdu.pduDestination = LocalBroadcast()
        else:
            if _debug:
                print "    - unknown header", hdr
            return

        newpdu.pduData = pdu.pduData
        self.Response(newpdu)

#
#   IPForeign
#

class IPForeign(Client,Server,Task):
    """A class that handles registering as a foreign device and maintaining that
    registration.  regState is 0=unregistered, 1=pending, 2=error, 3=complete.
    """

    unregistered    = 0     # unregistered
    pending         = 1     # registration sent, nothing received yet
    error           = 2     # error received
    complete        = 3     # registration successful
    reregister      = 4     # already registered, re-registration pending

    def __init__(self, bbmdAddr=None, refresh=None):
        Task.__init__(self, Task.oneShotTask)

        if not isinstance(bbmdAddr,Address):
            raise TypeError, "bbmdAddr must be an Address"

        self.regState = IPForeign.unregistered
        self.regAddress = bbmdAddr
        self.regInterval = refresh
        self.regRetry = 10000       # 10 seconds

        if bbmd and refresh:
            self.Register(bbmd, refresh)

    def Indication(self,pdu):
        if _debug:
            print "IPForeign.Indication"

        if self.regState < IPForeign.complete:
            if _debug:
                print "    - unregistered"
            return

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            newpdu.pduDestination = self.regAddress
            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcDistributeBroadcastToNetwork )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
        elif pdu.pduDestination.addrType == Address.localStationAddr:
            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcOriginalUnicastNPDU )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
        else:
            return

        self.Request(newpdu)

    def Confirmation(self,pdu):
        if _debug:
            print "IPForeign.Confirmation"

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        hdr = pdu.Get()
        if hdr != 0x81:
            return
            
        hdr = pdu.Get()
        if hdr == BVLLPDU.bvlcResult:
            # we are scheduled to try again, cancel it
            self.SuspendTask()
            
            datalen = pdu.GetShort()
            if (datalen != 6):
                if _debug:
                    print "    - malformed result"
                return

            if self.regState != IPForeign.pending:
                if _debug:
                    print "    - registration not pending"
                return

            rsltcode = pdu.GetShort()
            if rsltcode == 0:
                if _debug:
                    print "    - registration successful"
                self.regState = IPForeign.complete
                self.InstallTask(delay=self.regInterval)
            else:
                if _debug:
                    print "    - registration failed: %d" % (rsltcode,)
                self.regState = IPForeign.error
            return
        elif hdr == BVLLPDU.bvlcOriginalUnicastNPDU:
            if _debug:
                print "    - original unicast NPDU"
            datalen = pdu.GetShort()
        elif hdr == BVLLPDU.bvlcForwardedNPDU:
            if _debug:
                print "    - forwarded NPDU"
            datalen = pdu.GetShort()
            newpdu.pduSource = LocalStation(pdu.GetData(6))
            newpdu.pduDestination = LocalBroadcast()
        else:
            if _debug:
                print "    - unrecognized BVLCI command %d" % (hdr,)
            return

        newpdu.pduData = pdu.pduData
        self.Response(newpdu)

    def Register(self, bbmd = None, refresh = None):
        if _debug:
            print "IPForeign.Register"

        if bbmd is not None:
            self.regAddress = bbmd
        if refresh is not None:
            self.regInterval = refresh
        if _debug:
            print "    - ttl %g" % (self.regInterval,)
            
        pdu = PDU()
        pdu.pduSource = None
        pdu.pduDestination = self.regAddress
        
        # form the registration request
        pdu.Put( 0x81 )
        pdu.Put( BVLLPDU.bvlcRegisterForeignDevice )
        pdu.PutShort( 6 )
        pdu.PutShort( self.regInterval )
        
        # set registration pending, install retry
        # set registration pending, install retry
        if self.regState == IPForeign.complete:
            self.regState = IPForeign.reregister
        else:
            self.regState = IPForeign.pending
        self.InstallTask(delay=self.regRetry)

        # send along the request
        self.Request(pdu)

    def ProcessTask(self):
        self.Register()

#
#   Foreign Device Table Entry
#

class FDTEntry:

    def __init__(self):
        self.fdAddress = None
        self.fdTTL = None
        self.fdRemain = None

#
#   BBMD
#

class BBMD(Client,Server,Task):

    def __init__(self, addr):
        Task.__init__( self, Task.recurringTask, 1000 )

        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        self.bbmdAddress = addr
        self.bbmdBDT = []
        self.bbmdFDT = []

        self.InstallTask()

    def Indication(self,pdu):
        if _debug:
            print self, "BBMD.Indication"

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        if pdu.pduDestination.addrType == Address.localStationAddr:
            if _debug:
                print "    - unicast message"

            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcOriginalUnicastNPDU )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
            self.Request(newpdu)

        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            if _debug:
                print "    - broadcast message"

            newpdu.Put( 0x81 )
            newpdu.Put( BVLLPDU.bvlcOriginalBroadcastNPDU )
            newpdu.PutShort( len(pdu.pduData) + 4 )
            newpdu.PutData( pdu.pduData )
            self.Request(newpdu)

            # create a forwarded NPDU message with self as the source
            fwdpdu = PDU()
            fwdpdu.pduSource = pdu.pduSource
            fwdpdu.Put( 0x81 )
            fwdpdu.Put( BVLLPDU.bvlcForwardedNPDU )
            fwdpdu.PutShort( len(pdu.pduData) + 10 )
            fwdpdu.PutData( self.bbmdAddress.addrAddr )
            fwdpdu.PutData( pdu.pduData )

            # send it to the peers
            for bdte in self.bbmdBDT:
                if bdte != self.bbmdAddress:
                    fwdpdu.pduDestination = Address( ((bdte.addrIP|~bdte.addrMask), bdte.addrPort) )
                    self.Request(fwdpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                fwdpdu.pduDestination = fdte.fdAddress
                self.Request(fwdpdu)

    def Confirmation(self,pdu):
        if _debug:
            print self, "BBMD.Confirmation"

        newpdu = PDU()
        newpdu.pduSource = pdu.pduSource
        newpdu.pduDestination = pdu.pduDestination

        hdr = pdu.Get()
        if hdr != 0x81:
            return

        hdr = pdu.Get()
        datalen = pdu.GetShort()

        if hdr == BVLLPDU.bvlcOriginalUnicastNPDU:
            if _debug:
                print "    - original unicast message"

            # pass up to the next layer
            newpdu.pduData = pdu.pduData
            self.Response(newpdu)

        elif hdr == BVLLPDU.bvlcOriginalBroadcastNPDU:
            if _debug:
                print "    - original broadcast message"

            # allow next layer up to get a copy
            newpdu.pduDestination = LocalBroadcast()
            newpdu.pduData = pdu.pduData
            self.Response(newpdu)

            # create a forwarded NPDU message
            fwdpdu = PDU()
            fwdpdu.Put( 0x81 )
            fwdpdu.Put( BVLLPDU.bvlcForwardedNPDU )
            fwdpdu.PutShort( len(pdu.pduData) + 10 )
            fwdpdu.PutData( pdu.pduSource.addrAddr )
            fwdpdu.PutData( pdu.pduData )

            # send it to the peers
            for bdte in self.bbmdBDT:
                if bdte != self.bbmdAddress:
                    fwdpdu.pduDestination = Address( ((bdte.addrIP|~bdte.addrMask), bdte.addrPort) )
                    self.Request(fwdpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                fwdpdu.pduDestination = fdte.fdAddress
                self.Request(fwdpdu)

        elif hdr == BVLLPDU.bvlcForwardedNPDU:
            if _debug:
                print "    - forwarded NPDU"

            # get the original source
            srcAddr = pdu.GetData(6)

            # create a forwarded NPDU message
            fwdpdu = PDU()
            fwdpdu.Put( 0x81 )
            fwdpdu.Put( BVLLPDU.bvlcForwardedNPDU )
            fwdpdu.PutShort( len(pdu.pduData) + 10 )
            fwdpdu.PutData( srcAddr )
            fwdpdu.PutData( pdu.pduData )

            ### broadcast it on the local network
            # (see if this should be broadcast on the local network, true iff my mask in the
            # BDT says direct messages forwarded messages to me)
            fwdpdu.pduDestination = LocalBroadcast()
            self.Request(fwdpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                fwdpdu.pduDestination = fdte.fdAddress
                self.Request(fwdpdu)

            # allow next layer up to get a copy
            newpdu.pduSource = LocalStation(srcAddr)
            newpdu.pduDestination = LocalBroadcast()
            newpdu.pduData = pdu.pduData
            self.Response(newpdu)

        elif hdr == BVLLPDU.bvlcDistributeBroadcastToNetwork:
            if _debug:
                print "    - distribute broadcast to network"

            # create a forwarded NPDU message
            fwdpdu = PDU()
            fwdpdu.Put( 0x81 )
            fwdpdu.Put( BVLLPDU.bvlcForwardedNPDU )
            fwdpdu.PutShort( len(pdu.pduData) + 10 )
            fwdpdu.PutData( pdu.pduSource.addrAddr )
            fwdpdu.PutData( pdu.pduData )

            # do a local broadcast
            fwdpdu.pduDestination = LocalBroadcast()
            self.Request(fwdpdu)

            # send it to the peers
            for bdte in self.bbmdBDT:
                if bdte != self.bbmdAddress:
                    fwdpdu.pduDestination = Address( ((bdte.addrIP|~bdte.addrMask), bdte.addrPort) )
                    self.Request(fwdpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                if fdte.fdAddress != pdu.pduSource:
                    fwdpdu.pduDestination = fdte.fdAddress
                    self.Request(fwdpdu)

            # allow next layer up to get a copy
            newpdu.pduSource = pdu.pduSource
            newpdu.pduDestination = LocalBroadcast()
            newpdu.pduData = pdu.pduData
            self.Response(newpdu)

        elif hdr == BVLLPDU.bvlcRegisterForeignDevice:
            if _debug:
                print "    - register foreign device"

            # extract the TTL
            ttl = pdu.GetShort()

            # attempt to register it
            stat = self.RegisterForeignDevice( pdu.pduSource, ttl);

            # create a response
            rsvp = PDU()
            rsvp.pduDestination = pdu.pduSource
            rsvp.Put( 0x81 )
            rsvp.Put( BVLLPDU.bvlcResult )
            rsvp.PutShort( 6 )
            rsvp.PutShort( 0 )

            # send it back
            self.Request(rsvp)

        elif hdr == BVLLPDU.bvlcReadForeignDeviceTable:
            if _debug:
                print "    - read foreign device table"

            # create a response
            rsvp = PDU()
            rsvp.pduDestination = pdu.pduSource
            rsvp.Put( 0x81 )
            rsvp.Put( BVLLPDU.bvlcResult )
            rsvp.PutShort( 6 )
            rsvp.PutShort( 0x0040 )     # NAK

            # send it back
            self.Request(rsvp)

        elif hdr == BVLLPDU.bvlcDeleteForeignDeviceTableEntry:
            if _debug:
                print "    - delete foreign device table entry"

            # create a response
            rsvp = PDU()
            rsvp.pduDestination = pdu.pduSource
            rsvp.Put( 0x81 )
            rsvp.Put( BVLLPDU.bvlcResult )
            rsvp.PutShort( 6 )
            rsvp.PutShort( 0x0050 )     # NAK

            # send it back
            self.Request(rsvp)

        elif hdr == BVLLPDU.bvlcReadBroadcastDistributionTable:
            if _debug:
                print "    - read broadcast distribution table"

            # create a response
            rsvp = PDU()
            rsvp.pduDestination = pdu.pduSource
            rsvp.Put( 0x81 )
            rsvp.Put( BVLLPDU.bvlcResult )
            rsvp.PutShort( 6 )
            rsvp.PutShort( 0x0020 )     # NAK

            # send it back
            self.Request(rsvp)

        elif hdr == BVLLPDU.bvlcWriteBroadcastDistributionTable:
            if _debug:
                print "    - write broadcast distribution table"

            # create a response
            rsvp = PDU()
            rsvp.pduDestination = pdu.pduSource
            rsvp.Put( 0x81 )
            rsvp.Put( BVLLPDU.bvlcResult )
            rsvp.PutShort( 6 )
            rsvp.PutShort( 0x0010 )     # NAK

            # send it back
            self.Request(rsvp)

        else:
            # might want to log this
            pass

    def RegisterForeignDevice(self, addr, ttl):
        """Add a foreign device to the FDT."""
        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        for fdte in self.bbmdFDT:
            if addr == fdte.fdAddress:
                break
        else:
            fdte = FDTEntry()
            fdte.fdAddress = addr
            self.bbmdFDT.append( fdte )

        fdte.fdTTL = ttl
        fdte.fdRemain = ttl + 5

        # return success
        return 0

    def DeleteForeignDevice(self, addr):
        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        # find it and delete it
        for i in range(len(self.bbmdFDT)-1, -1, -1):
            if addr == self.bbmdFDT[i].fdAddress:
                del self.bbmdFDT[i]

        # return success
        return 0

    def ProcessTask(self):
        # look for foreign device registrations that have expired
        for i in range(len(self.bbmdFDT)-1, -1, -1):
            fdte = self.bbmdFDT[i]
            fdte.fdRemain -= 1

            # delete it if it expired
            if fdte.fdRemain <= 0:
                if _debug:
                    print "(foreign device expired", fdte.fdAddress, ")"
                del self.bbmdFDT[i]

    def AddPeer(self, addr):
        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        # see if it's already there
        for bdte in self.bbmdBDT:
            if addr == bdte:
                break
        else:
            self.bbmdBDT.append(addr)

    def DeletePeer(self, addr):
        if isinstance(addr,LocalStation):
            pass
        elif isinstance(arg,types.StringType):
            addr = LocalStation( addr )
        else:
            raise TypeError, "addr must be a string or a LocalStation"

        # look for the peer address
        for i in range(len(self.bbmdBDT)-1, -1, -1):
            if addr == self.bbmdBDT[i]:
                del self.bbmdBDT[i]
                break
        else:
            pass

#
#  NPDU
#

class NPDU(PDU):
    whoIsRouterToNetwork            = 0x00
    iAmRouterToNetwork              = 0x01
    iCouldBeRouterToNetwork         = 0x02
    rejectMessageToNetwork          = 0x03
    routerBusyToNetwork             = 0x04
    routerAvailableToNetwork        = 0x05
    initializeRoutingTable          = 0x06
    initializeRoutingTableAck       = 0x07
    establishConnectionToNetwork    = 0x08
    disconnectConnectionToNetwork   = 0x09

    typeName = \
        [ 'WhoIsRouterToNetwork'
        , 'IAmRouterToNetwork'
        , 'ICouldBeRouterToNetwork'
        , 'RejectMessageToNetwork'
        , 'RouterBusyToNetwork'
        , 'RouterAvailableToNetwork'
        , 'InitializeRoutingTable'
        , 'InitializeRoutingTableAck'
        , 'EstablishConnectionToNetwork'
        , 'DisconnectConnectionToNetwork'
        ]

    def __init__(self,*args):
        PDU.__init__(self,*args)
        self.npduVersion = 1
        self.npduControl = None
        self.npduDADR = None
        self.npduSADR = None
        self.npduHopCount = None
        self.npduNetMessage = None
        self.npduVendorID = None

    def Encode(self, pdu):
        """Encode the contents of the NPDU into the PDU."""
        if _debug:
            print "NPDU.Encode"

        # copy the source and destination addresses
        pdu.pduSource = self.pduSource
        pdu.pduDestination = self.pduDestination

        # only version 1 messages supported
        pdu.Put(self.npduVersion)

        # build the flags
        if self.npduNetMessage is not None:
            if _debug:
                print "    - network layer message"
            netLayerMessage = 0x80
        else:
            if _debug:
                print "    - application layer message"
            netLayerMessage = 0x00

        if _debug:
            print "    - npduDADR", self.npduDADR

        # map the destination address
        dnetPresent = 0x00
        if self.npduDADR is not None:
            if _debug:
                print "    - dnet/dlen/dadr present"
            dnetPresent = 0x20

        # map the source address
        snetPresent = 0x00
        if self.npduSADR is not None:
            if _debug:
                print "    - dnet/dlen/dadr present"
            snetPresent = 0x08

        # encode the control octet
        control = netLayerMessage | dnetPresent | snetPresent
        if self.pduExpectingReply:
            control |= 0x04
        control |= (self.pduNetworkPriority & 0x03)
        if _debug:
            print "    - control 0x%02X" % (control,)
        self.npduControl = control
        pdu.Put(control)

        # make sure expecting reply and priority get passed down
        pdu.pduExpectingReply = self.pduExpectingReply
        pdu.pduNetworkPriority = self.pduNetworkPriority

        # encode the destination address
        if dnetPresent:
            if self.npduDADR.addrType == Address.remoteStationAddr:
                pdu.PutShort(self.npduDADR.addrNet)
                pdu.Put(self.npduDADR.addrLen)
                pdu.PutData(self.npduDADR.addrAddr)
            elif self.npduDADR.addrType == Address.remoteBroadcastAddr:
                pdu.PutShort(self.npduDADR.addrNet)
                pdu.Put(0)
            elif self.npduDADR.addrType == Address.globalBroadcastAddr:
                pdu.PutShort(0xFFFF)
                pdu.Put(0)

        # encode the source address
        if snetPresent:
            pdu.PutShort(self.npduSADR.addrNet)
            pdu.Put(self.npduSADR.addrLen)
            pdu.PutData(self.npduSADR.addrAddr)

        # put the hop count
        if dnetPresent:
            pdu.Put(self.npduHopCount)

        # put the network layer message type (if present)
        if netLayerMessage:
            pdu.Put(self.npduNetMessage)
            # put the vendor ID
            if (self.npduNetMessage >= 0x80) and (self.npduNetMessage <= 0xFF):
                pdu.PutShort(self.npduVendorID)

        # everything else is data
        pdu.PutData(self.pduData)

    def Decode(self, pdu):
        """Decode the contents of the PDU and put them into the NPDU."""
        if _debug:
            print "NPDU.Decode"

        # copy the source and destination so that upper layers still have
        # access to the orginal source and destination
        self.pduSource = pdu.pduSource
        self.pduDestination = pdu.pduDestination

        # check the length
        if len(pdu.pduData) < 2:
            raise DecodingError, "invalid length"

        # only version 1 messages supported
        self.npduVersion = pdu.Get()
        if (self.npduVersion != 0x01):
            raise DecodingError, "only version 1 messages supported"

        # decode the control octet
        self.npduControl = control = pdu.Get()
        netLayerMessage = control & 0x80
        dnetPresent = control & 0x20
        snetPresent = control & 0x08
        self.pduExpectingReply = (control & 0x04) != 0
        self.pduNetworkPriority = control & 0x03

        # extract the destination address
        if dnetPresent:
            dnet = pdu.GetShort()
            dlen = pdu.Get()
            dadr = pdu.GetData(dlen)

            if dnet == 0xFFFF:
                self.npduDADR = GlobalBroadcast()
            elif dlen == 0:
                self.npduDADR = RemoteBroadcast(dnet)
            else:
                self.npduDADR = RemoteStation(dnet, dadr)

        # extract the source address
        if snetPresent:
            snet = pdu.GetShort()
            slen = pdu.Get()
            sadr = pdu.GetData(slen)

            if snet == 0xFFFF:
                raise DecodingError, "SADR can't be a global broadcast"
            elif slen == 0:
                raise DecodingError, "SADR can't be a remote broadcast"

            self.npduSADR = RemoteStation(snet, sadr)

        # extract the hop count
        if dnetPresent:
            self.npduHopCount = pdu.Get()

        # extract the network layer message type (if present)
        if netLayerMessage:
            self.npduNetMessage = pdu.Get()
            if (self.npduNetMessage >= 0x80) and (self.npduNetMessage <= 0xFF):
                # extract the vendor ID
                self.npduVendorID = pdu.GetShort()

        # everything left is data
        self.pduData = pdu.pduData

#
#   DebugNPDUContents
#

def DebugNPDUContents(npdu):
    """Print the contents of a network message."""
    print "    source =", npdu.pduSource
    print "    destination =", npdu.pduDestination
    print "    expecting reply =", npdu.pduExpectingReply
    print "    network priority =", npdu.pduNetworkPriority

    if npdu.npduVersion is not None:
        print "    version =", npdu.npduVersion
    if npdu.npduControl is not None:
        print "    control =", npdu.npduControl
    if npdu.npduDADR is not None:
        print "    dnet/dlen/dadr =", npdu.npduDADR
    if npdu.npduSADR is not None:
        print "    snet/slen/sadr =", npdu.npduSADR
    if npdu.npduHopCount is not None:
        print "    hop count =", npdu.npduHopCount
    if npdu.npduNetMessage is not None:
        print "    message type =", npdu.npduNetMessage, NPDU.typeName[npdu.npduNetMessage]
    if npdu.npduVendorID is not None:
        print "    vendor id =", npdu.npduVendorID

    print "    data =", StringToHex(npdu.pduData,'.')

#
#   MaxAPDUSegmentsEncode/MaxAPDUSegmentsDecode
#

def MaxAPDUSegmentsEncode(arg):
    if (arg > 64): return 7
    return {None:0, 0:0, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6}.get(arg)

def MaxAPDUSegmentsDecode(arg):
    if (arg >= 7): return 128
    return {0:None, 1:2, 2:4, 3:8, 4:16, 5:32, 6:64}.get(arg)

#
#   MaxAPDUResponseEncode/MaxAPDUResponseDecode
#

def MaxAPDUResponseEncode(arg):
    return {50:0, 128:1, 206:2, 480:3, 1024:4, 1476:5}[arg]

def MaxAPDUResponseDecode(arg):
    return {0:50, 1:128, 2:206, 3:480, 4:1024, 5:1476}[arg]

#
#   APDU
#

class APDU(PDU):
    confirmedRequest    = 0x00
    unconfirmedRequest  = 0x01
    simpleAck           = 0x02
    complexAck          = 0x03
    segmentAck          = 0x04
    error               = 0x05
    reject              = 0x06
    abort               = 0x07

    typeName = \
        [ 'ConfirmedRequest'
        , 'UnconfirmedRequest'
        , 'SimpleAck'
        , 'ComplexAck'
        , 'SegmentAck'
        , 'Error'
        , 'Reject'
        , 'Abort'
        ]

    def __init__(self, *args):
        PDU.__init__(self, *args)

        self.apduType = None
        self.apduSeg = None                 # segmented
        self.apduMor = None                 # more follows
        self.apduSA = None                  # segmented response accepted
        self.apduSrv = None                 # sent by server
        self.apduNak = None                 # negative acknowledgement
        self.apduSeq = None                 # sequence number
        self.apduWin = None                 # actual/proposed window size
        self.apduMaxSegs = None             # maximum segments accepted (decoded)
        self.apduMaxResp = None             # max response accepted (decoded)
        self.apduService = None             #
        self.apduInvokeID = None            #
        self.apduAbortRejectReason = None   #

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = self.typeName[self.apduType]
        except:
            stype = str(self.apduType)
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

    def Encode(self,pdu):
        """Encode the contents of the APDU into the PDU."""
        if _debug:
            print "APDU.Encode", pdu

        if (self.apduType == APDU.confirmedRequest):
            if _debug:
                print "    - confirmed request"

            # PDU type
            buff = self.apduType << 4
            if self.apduSeg:
                buff += 0x08
            if self.apduMor:
                buff += 0x04
            if self.apduSA:
                buff += 0x02
            pdu.Put(buff)
            pdu.Put((MaxAPDUSegmentsEncode(self.apduMaxSegs) << 4) + MaxAPDUResponseEncode(self.apduMaxResp))
            pdu.Put(self.apduInvokeID)
            if self.apduSeg:
                pdu.Put(self.apduSeq)
                pdu.Put(self.apduWin)
            pdu.Put(self.apduService)
            pdu.PutData(self.pduData)

        elif (self.apduType == APDU.unconfirmedRequest):
            if _debug:
                print "    - unconfirmed request"

            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduService)
            pdu.PutData(self.pduData)

        elif (self.apduType == APDU.simpleAck):
            if _debug:
                print "    - simple ack"

            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduService)

        elif (self.apduType == APDU.complexAck):
            if _debug:
                print "    - complex ack"

            # PDU type
            buff = self.apduType << 4
            if self.apduSeg:
                buff += 0x08
            if self.apduMor:
                buff += 0x04
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            if self.apduSeg:
                pdu.Put(self.apduSeq)
                pdu.Put(self.apduWin)
            pdu.Put(self.apduService)
            pdu.PutData(self.pduData)

        elif (self.apduType == APDU.segmentAck):
            if _debug:
                print "    - segment ack"

            # PDU type
            buff = self.apduType << 4
            if self.apduNak:
                buff += 0x02
            if self.apduSrv:
                buff += 0x01
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduSeq)
            pdu.Put(self.apduWin)

        elif (self.apduType == APDU.error):
            if _debug:
                print "    - error"

            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduService)
            pdu.PutData(self.pduData)

        elif (self.apduType == APDU.reject):
            if _debug:
                print "    - reject"

            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduAbortRejectReason)

        elif (self.apduType == APDU.abort):
            if _debug:
                print "    - abort"

            # PDU type
            buff = self.apduType << 4
            if self.apduSrv:
                buff += 0x01
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduAbortRejectReason)

        else:
            raise ValueError, "invalid APDU type"

    def Decode(self,pdu):
        """Decode the contents of the PDU into the APDU."""
        if _debug:
            print "APDU.Decode", pdu

        # make a copy of the PDU
        pdu = PDUData(pdu)

        # decode the first octet
        buff = pdu.Get()

        # decode the APDU type
        self.apduType = (buff >> 4) & 0x0F

        if (self.apduType == APDU.confirmedRequest):
            if _debug:
                print "    - confirmed request"

            self.apduSeg = ((buff & 0x08) != 0)
            self.apduMor = ((buff & 0x04) != 0)
            self.apduSA  = ((buff & 0x02) != 0)
            buff = pdu.Get()
            self.apduMaxSegs = MaxAPDUSegmentsDecode( (buff >> 4) & 0x07 )
            self.apduMaxResp = MaxAPDUResponseDecode( buff & 0x0F )
            self.apduInvokeID = pdu.Get()
            if self.apduSeg:
                self.apduSeq = pdu.Get()
                self.apduWin = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == APDU.unconfirmedRequest):
            if _debug:
                print "    - unconfirmed request"

            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == APDU.simpleAck):
            if _debug:
                print "    - simple ack"

            self.apduInvokeID = pdu.Get()
            self.apduService = pdu.Get()

        elif (self.apduType == APDU.complexAck):
            if _debug:
                print "    - complex ack"

            self.apduSeg = ((buff & 0x08) != 0)
            self.apduMor = ((buff & 0x04) != 0)
            self.apduInvokeID = pdu.Get()
            if self.apduSeg:
                self.apduSeq = pdu.Get()
                self.apduWin = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == APDU.segmentAck):
            if _debug:
                print "    - segment ack"

            self.apduNak = ((buff & 0x02) != 0)
            self.apduSrv = ((buff & 0x01) != 0)
            self.apduInvokeID = pdu.Get()
            self.apduSeq = pdu.Get()
            self.apduWin = pdu.Get()

        elif (self.apduType == APDU.error):
            if _debug:
                print "    - error"

            self.apduInvokeID = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == APDU.reject):
            if _debug:
                print "    - reject"

            self.apduInvokeID = pdu.Get()
            self.apduAbortRejectReason = pdu.Get()

        elif (self.apduType == APDU.abort):
            if _debug:
                print "    - abort"

            self.apduSrv = ((buff & 0x01) != 0)
            self.apduInvokeID = pdu.Get()
            self.apduAbortRejectReason = pdu.Get()
            self.pduData = pdu.pduData

        else:
            raise ValueError, "invalid APDU type"

#
#   DebugAPDUContents
#

def DebugAPDUContents(apdu):
    """Print the contents of application encoded data."""
    print "    source =", apdu.pduSource
    print "    destination =", apdu.pduDestination
    print "    expecting reply =", apdu.pduExpectingReply
    print "    network priority =", apdu.pduNetworkPriority

    if apdu.apduType is not None:
        print "    type =", apdu.apduType, APDU.typeName[apdu.apduType]
    if apdu.apduSeg is not None:
        print "    segmented =", apdu.apduSeg
    if apdu.apduMor is not None:
        print "    more follows =", apdu.apduMor
    if apdu.apduSA is not None:
        print "    segmented response accepted =", apdu.apduSA
    if apdu.apduSrv is not None:
        print "    sent by server =", apdu.apduSrv
    if apdu.apduNak is not None:
        print "    negative ack =", apdu.apduNak
    if apdu.apduSeq is not None:
        print "    sequence number =", apdu.apduSeq
    if apdu.apduWin is not None:
        print "    window size =", apdu.apduWin
    if apdu.apduMaxSegs is not None:
        print "    max segments =", apdu.apduMaxSegs
    if apdu.apduMaxResp is not None:
        print "    max response size =", apdu.apduMaxResp
    if apdu.apduService is not None:
        if apdu.apduType == APDU.confirmedRequest:
            print "    service =", apdu.apduService, ConfirmedRequestAPDU.serviceName[apdu.apduService]
        elif apdu.apduType == APDU.unconfirmedRequest:
            print "    service =", apdu.apduService, UnconfirmedRequestAPDU.serviceName[apdu.apduService]
        else:
            print "    service =", apdu.apduService
    if apdu.apduInvokeID is not None:
        print "    invoke ID =", apdu.apduInvokeID
    if apdu.apduAbortRejectReason is not None:
        print "    reason =", apdu.apduAbortRejectReason

    print "    data =", StringToHex(apdu.pduData,'.')

#
#   ConfirmedRequestAPDU
#

class ConfirmedRequestAPDU(APDU):
    # Alarm and Event Services
    acknowledgeAlarm                = 0
    confirmedCOVNotification        = 1
    confirmedEventNotification      = 2
    getAlarmSummary                 = 3
    getEnrollmentSummary            = 4
    subscribeCOV                    = 5

    # File Access Services
    atomicReadFile                  = 6
    atomicWriteFile                 = 7

    # Object Access Services
    addListElement                  = 8
    removeListElement               = 9
    createObject                    = 10
    deleteObject                    = 11
    readProperty                    = 12
    readPropertyConditional         = 13
    readPropertyMultiple            = 14
    writeProperty                   = 15
    writePropertyMultiple           = 16

    # Remote Device Management Services
    deviceCommunicationControl      = 17
    confirmedPrivateTransfer        = 18
    confirmedTextMessage            = 19
    reinitializeDevice              = 20

    # Virtual Terminal Services
    vtOpen                          = 21
    vtClose                         = 22
    vtData                          = 23

    # Security Services
    authenticate                    = 24
    requestKey                      = 25

    serviceName = \
        [ "AcknowledgeAlarm"
        , "ConfirmedCOVNotification"
        , "ConfirmedEventNotification"
        , "GetAlarmSummary"
        , "GetEnrollmentSummary"
        , "SubscribeCOV"
        , "AtomicReadFile"
        , "AtomicWriteFile"
        , "AddListElement"
        , "RemoveListElement"
        , "CreateObject"
        , "DeleteObject"
        , "ReadProperty"
        , "ReadPropertyConditional"
        , "ReadPropertyMultiple"
        , "WriteProperty"
        , "WritePropertyMultiple"
        , "DeviceCommunicationControl"
        , "ConfirmedPrivateTransfer"
        , "ConfirmedTextMessage"
        , "ReinitializeDevice"
        , "VTOpen"
        , "VTClose"
        , "VTData"
        , "Authenticate"
        , "RequestKey"
        ]

    def __init__(self, choice, *args):
        APDU.__init__(self, *args)
        self.apduType = APDU.confirmedRequest
        self.apduService = choice

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = self.serviceName[self.apduService]
        except:
            stype = str(self.apduService)
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   UnconfirmedRequestAPDU
#

class UnconfirmedRequestAPDU(APDU):
    iAm                             = 0
    iHave                           = 1
    unconfirmedCOVNotification      = 2
    unconfirmedEventNotification    = 3
    unconfirmedPrivateTransfer      = 4
    unconfirmedTextMessage          = 5
    timeSynchronization             = 6
    whoHas                          = 7
    whoIs                           = 8

    serviceName = \
        [ "IAm"
        , "IHave"
        , "UnconfirmedCOVNotification"
        , "UnconfirmedEventNotification"
        , "UnconfirmedPrivateTransfer"
        , "UnconfirmedTextMessage"
        , "TimeSynchronization"
        , "WhoHas"
        , "WhoIs"
        ]

    def __init__(self, choice, *args):
        APDU.__init__(self, *args)
        self.apduType = APDU.unconfirmedRequest
        self.apduService = choice

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = self.serviceName[self.apduService]
        except:
            stype = str(self.apduService)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   SimpleAckAPDU
#

class SimpleAckAPDU(APDU):

    def __init__(self, choice, invokeID, *args):
        APDU.__init__(self,*args)
        self.apduType = APDU.simpleAck
        self.apduService = choice
        self.apduInvokeID = invokeID

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = ConfirmedRequestAPDU.serviceName[self.apduService]
        except:
            stype = str(self.apduService)
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   ComplexAckAPDU
#

class ComplexAckAPDU(APDU):

    def __init__(self, choice, invokeID, *args):
        APDU.__init__(self, *args)
        self.apduType = APDU.complexAck
        self.apduService = choice
        self.apduInvokeID = invokeID

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = ConfirmedRequestAPDU.serviceName[self.apduService]
        except:
            stype = str(self.apduService)
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   SegmentAckAPDU
#

class SegmentAckAPDU(APDU):

    def __init__(self, nak, srv, invokeID, sequenceNumber, windowSize, *args):
        APDU.__init__(self, *args)
        if nak is None: raise ValueError, "nak is None"
        if srv is None: raise ValueError, "srv is None"
        if invokeID is None: raise ValueError, "invokeID is None"
        if sequenceNumber is None: raise ValueError, "sequenceNumber is None"
        if windowSize is None: raise ValueError, "windowSize is None"

        self.apduType = APDU.segmentAck
        self.apduNak = nak
        self.apduSrv = srv
        self.apduInvokeID = invokeID
        self.apduSeq = sequenceNumber
        self.apduWin = windowSize

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__

        return '<' + sname + ' instance at 0x%08x' % xid + '>'

#
#   ErrorAPDU
#

class ErrorAPDU(APDU):

    def __init__(self, choice, invokeID, *args):
        APDU.__init__(self, *args)
        self.apduType = APDU.error
        self.apduService = choice
        self.apduInvokeID = invokeID

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            stype = ConfirmedRequestAPDU.serviceName[self.apduService]
        except:
            stype = str(self.apduService)
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   RejectAPDU
#

class RejectAPDU(APDU):
    other                           = 0
    bufferOverflow                  = 1
    inconsistentParameters          = 2
    invalidParameterDataType        = 3
    invalidTag                      = 4
    missingRequiredParameter        = 5
    parameterOutOfRange             = 6
    tooManyArguments                = 7
    undefinedEnumeration            = 8
    unrecognizedService             = 9

    reasonName = \
        [ "other"
        , "bufferOverflow"
        , "inconsistentParameters"
        , "invalidParameterDataType"
        , "invalidTag"
        , "missingRequiredParameter"
        , "parameterOutOfRange"
        , "tooManyArguments"
        , "undefinedEnumeration"
        , "unrecognizedService"
        ]

    def __init__(self, invokeID, reason, *args):
        APDU.__init__(self,*args)
        self.apduType = APDU.reject
        self.apduInvokeID = invokeID
        self.apduAbortRejectReason = reason

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            reason = RejectAPDU.reasonName[self.apduAbortRejectReason]
        except:
            reason = str(self.apduAbortRejectReason)

        return '<' + sname + '(%s,%s) instance at 0x%08x' % (self.apduInvokeID, reason, xid) + '>'

#
#   AbortAPDU
#

class AbortAPDU(APDU):
    other                           = 0
    bufferOverflow                  = 1
    invalidAPDUInThisState          = 2
    preemptedByHigherPriorityTask   = 3
    segmentationNotSupported        = 4

    # 64..255 are available for vendor codes
    serverTimeout                   = 64
    noResponse                      = 65

    def __init__(self, srv, invokeID, reason, *args):
        APDU.__init__(self,*args)
        self.apduType = APDU.abort
        self.apduSrv = srv
        self.apduInvokeID = invokeID
        self.apduAbortRejectReason = reason

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = '%s,%s' % (self.apduInvokeID, self.apduAbortRejectReason)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

#
#   RouterReference
#

class RouterReference:
    """These objects map a router; the adapter to talk to it,
    its address, and a list of networks that it routes to."""

    def __init__(self, adapter, addr, nets = []):
        self.refAdapter = adapter
        self.refAddress = addr      # local station relative to the adapter
        self.refNets = nets         # list of remote networks

#
#   RouterAdapter
#

class RouterAdapter(Client):
    """A RouterAdapter object handles the network layer of PDU's."""

    def __init__(self, net, router):
        self.adapterNet = net
        self.adapterRouter = router
        self.adapterRefs = []

    def Indication(self, npdu):
        """Encode messages and send downstream."""
        if _debug:
            print "RouterAdapter.Indication"
            DebugNPDUContents(npdu)

        pdu = PDU()
        npdu.Encode(pdu)
        self.Request(pdu)

    def Confirmation(self, pdu):
        """Pass upstream messages along to the router."""
        if _debug:
            print "RouterAdapter.Confirmation"

        npdu = NPDU()
        npdu.Decode(pdu)
        self.adapterRouter.ProcessNPDU(self, npdu)

#
#   Router
#

class Router(Server):
    """A Router object handles routing."""

    def __init__(self):
        Server.__init__(self)

        self.routerAdapters = []    # list of adapters
        self.routerLocalAdapter = None
        self.routerLocalAddress = None

    def Bind(self, endp, net = None):
        # create a new adapter
        adapter = RouterAdapter(net, self)

        # bind it
        Bind(adapter, endp)

        # add it to the list of adapters
        self.routerAdapters.append(adapter)

    def SetLocalAddress(self, net, addr):
        """When a router is bound to more than one network, one of them
        must be selected as "local", along with its local station address,
        so there is a consistent device-address-binding."""
        # find the adapter
        for adapter in self.routerAdapters:
            if net == adapter.adapterNet:
                self.routerLocalAdapter = adapter
                break
        else:
            raise ConfigurationError, "no adapter to network %d" % (net,)

        # set the address as it appears in routed messages
        self.routerLocalAddress = RemoteStation(net, addr)

    def BroadcastRoutingTable(self, adapter):
        npdu = NPDU()
        npdu.pduSource = None
        npdu.pduDestination = LocalBroadcast()

        # set the message
        npdu.npduNetMessage = NPDU.iAmRouterToNetwork;

        # append the network numbers of direct connected nets
        for ada in self.routerAdapters:
            if ada is not adapter:
                npdu.PutShort(ada.adapterNet)

                # append networks that it can route to
                for ref in ada.adapterRefs:
                    for net in ref.refNets:
                        npdu.PutShort(net)

        # send it to the adapter
        adapter.Indication(npdu)

    def BroadcastRoutingTables(self):
        """Broadcast all of the routing tables for all adapters."""
        if _debug:
            print "Router.BroadcastRoutingTables"

        # if there's only one adapter, we're not much of a router
        if len(self.routerAdapters) == 1:
            if _debug:
                print "    - we're not a router"
            return

        # each one does itself
        for adapter in self.routerAdapters:
            self.BroadcastRoutingTable(adapter)

    def ProcessNPDU(self, adapter, npdu):
        """Upstream packet from an adapter."""

        if _debug:
            print "Router.ProcessNPDU"
            print "    npdu.pduSource =", npdu.pduSource
            print "    npdu.pduDestination =", npdu.pduDestination
            print "    npdu.npduNetMessage =", npdu.npduNetMessage
            print "    npdu.npduVendorID =", npdu.npduVendorID
            print "    npdu.npduHopCount =", npdu.npduHopCount
            print "    npdu.npduSADR =", npdu.npduSADR
            print "    npdu.npduDADR =", npdu.npduDADR
            print "    npdu.pduData =", StringToHex(npdu.pduData,'.')

        # check to see if this is a network layer message
        if npdu.npduNetMessage is not None:
            # filter out vendor specific messages
            if npdu.npduVendorID != 0:
                self.ProcessNetMessage( adapter, npdu )
            return

        # if this thing has an SADR, the source is acting like a router, and
        # we should check to make sure we have a reference to this thing as
        # a router to the source network
        if npdu.npduSADR:
            for ref in adapter.adapterRefs:
                if npdu.pduSource == ref.refAddress:
                    if npdu.npduSADR.addrNet not in ref.refNets:
                        if _debugAdapterRefs:
                            print "    - adding to existing reference", npdu.pduSource,"net",npdu.npduSADR.addrNet
                        ref.refNets.append(npdu.npduSADR.addrNet)
                    else:
                        if _debugAdapterRefs:
                            print "    - reference", npdu.pduSource,"already contains net",npdu.npduSADR.addrNet
                    break
                elif npdu.npduSADR.addrNet in ref.refNets:
                    if _debugAdapterRefs:
                        print "    - removing reference", npdu.pduSource,"to net",npdu.npduSADR.addrNet
                    # moving to a different router on the same endpoint
                    ref.refNets.remove(npdu.npduSADR.addrNet)
                    ### remove empty reference
            else:
                # no match, make a new reference
                if _debugAdapterRefs:
                    print "    - adding reference", npdu.pduSource,"to net",npdu.npduSADR.addrNet
                adapter.adapterRefs.append(RouterReference(adapter, npdu.pduSource, [npdu.npduSADR.addrNet]))
            ### make sure reference doesn't exist on a different adapter

        # check for a copy going upstream
        if self.serverPeer:
            # check for the simple case
            if (len(self.routerAdapters) == 1) or (adapter is self.routerLocalAdapter):
                if (not npdu.npduDADR) or (npdu.npduDADR.addrType == Address.globalBroadcastAddr):
                    if _debug:
                        print "    - send to device (1)"
                    apdu = APDU()
                    apdu.pduSource = npdu.npduSADR or npdu.pduSource
                    apdu.pduDestination = npdu.npduDADR or npdu.pduDestination
                    apdu.Decode(npdu)

                    self.Response(apdu)
                else:
                    if _debug:
                        print "    - not for our device (1)"
                    pass # it's not for us, perhaps it was broadcast

            # make sure at least one adapter is considered local
            elif not self.routerLocalAdapter:
                raise ConfigurationError, "no local endpoint"

            # if there's no DADR, it can't be for us
            elif (not npdu.npduDADR):
                if _debug:
                    print "    - not for our device (2)"
                pass

            # if the DADR matches our local address, our device should get a copy
            elif (npdu.npduDADR == self.routerLocalAddress):
                if _debug:
                    print "    - send to device (2)"
                apdu = APDU()
                apdu.pduSource = npdu.npduSADR or RemoteStation(adapter.adapterNet, npdu.pduSource.addrAddr)
                apdu.pduDestination = LocalStation(self.routerLocalAddress.addrAddr)
                apdu.Decode(npdu)

                self.Response(apdu)

                # no more processing necessary
                return

            # see if it was broadcast and our device should get a copy
            elif (npdu.npduDADR.addrType == Address.remoteBroadcastAddr) and (npdu.npduDADR.addrNet == self.routerLocalAdapter.adapterNet):
                if _debug:
                    print "    - send to device (3)"
                apdu = APDU()
                apdu.pduSource = npdu.npduSADR or RemoteStation(adapter.adapterNet, npdu.pduSource.addrAddr)
                apdu.pduDestination = LocalBroadcast()
                apdu.Decode(npdu)

                self.Response(apdu)

            # if it was globally broadcast our device should get a copy
            elif (npdu.npduDADR.addrType == Address.globalBroadcastAddr):
                if _debug:
                    print "    - send to device (4)"
                apdu = APDU()
                apdu.pduSource = npdu.npduSADR or RemoteStation(adapter.adapterNet, npdu.pduSource.addrAddr)
                apdu.pduDestination = npdu.npduDADR
                apdu.Decode(npdu)

                self.Response(apdu)

        # if there's only one adapter, we're not much of a router
        if len(self.routerAdapters) == 1:
            if _debug:
                print "    - we're not a router"
            return

        # if there's no DADR it is not being routed
        if not npdu.npduDADR:
            if _debug:
                print "    - message not being routed"
            return

        # if the hop count reached zero, drop it
        if npdu.npduHopCount == 0:
            if _debug:
                print "    - hop count 0"
            return

        # it's hopping
        npdu.npduHopCount -= 1

        # make sure it looks routed, if it hasn't been routed already to get here
        if not npdu.npduSADR:
            npdu.npduSADR = RemoteStation(adapter.adapterNet, npdu.pduSource.addrAddr)
            if _debug:
                print "    - SADR is now",npdu.npduSADR

        if (npdu.npduDADR.addrType == Address.globalBroadcastAddr):
            if _debug:
                print "    - global broadcast"
            # this thing becomes a local broadcast
            npdu.pduDestination = LocalBroadcast()

            # send it to the other adapters
            for ada in self.routerAdapters:
                if ada is not adapter:
                    ada.Indication(npdu)

            # no more processing
            return

        # see if this message is a direct connect
        for ada in self.routerAdapters:
            if (ada is not adapter) and (npdu.npduDADR.addrNet == ada.adapterNet):
                if _debugAdapterRefs:
                    print "    - found a direct connect (1)"
                if (npdu.npduDADR.addrType == Address.remoteStationAddr):
                    npdu.pduDestination = LocalStation(npdu.npduDADR.addrAddr)
                elif (npdu.npduDADR.addrType == Address.remoteBroadcastAddr):
                    npdu.pduDestination = LocalBroadcast()
                else:
                    raise EncodingError, "invalid DADR address type"

                npdu.npduDADR = None
                ada.Indication(npdu)
                break

            # check to see if there's a router for it
            for ref in ada.adapterRefs:
                if npdu.npduDADR.addrNet in ref.refNets:
                    if _debugAdapterRefs:
                        print "    - found a path via",ref.refAddress,"(1)"
                    npdu.pduDestination = ref.refAddress
                    ada.Indication(npdu)
                    break
            else:
                continue
            break
        else:
            if _debug:
                print "    - rejecting message to network"

            # build a RejectMessageToNetwork
            rpdu = NPDU()
            rpdu.pduSource = None
            rpdu.pduDestination = npdu.pduSource

            # set the message
            rpdu.npduNetMessage = NPDU.rejectMessageToNetwork

            # set the error code
            rpdu.Put( 0x01 )

            # send the network number
            rpdu.PutShort(npdu.npduDADR.addrNet)

            # send it to the adapter
            adapter.Indication(rpdu)

    def ProcessNetMessage(self, adapter, npdu):
        """Network traffic is trying to tell us something."""
        if _debug:
            print "Router.ProcessNetMessage"

        if npdu.npduNetMessage == NPDU.whoIsRouterToNetwork:
            self.WhoIsRouterToNetwork(adapter,npdu)
        elif npdu.npduNetMessage == NPDU.iAmRouterToNetwork:
            self.IAmRouterToNetwork(adapter,npdu)
        else:
            pass

    def WhoIsRouterToNetwork(self, adapter, npdu):
        if _debug:
            print "Router.WhoIsRouterToNetwork"

        # make sure we're really a router
        if (len(self.routerAdapters) == 1):
            if _debug:
                print "    - we're not a real router"
            return

        # no parameter means return everything
        found = (npdu.pduData == '')

        # specific net
        if not found:
            net = npdu.GetShort()

            for ada in self.routerAdapters:
                if (ada is not adapter):
                    if (ada.adapterNet == net):
                        if _debugAdapterRefs:
                            print "    - found a direct connect (2)"
                        found = True
                        break

                    # check to see if there's a router for it
                    for ref in ada.adapterRefs:
                        if net in ref.refNets:
                            if _debugAdapterRefs:
                                print "     - found a path via",ref.refAddress,"(2)"
                            found = True
                            break
                    else:
                        continue
                    break
        if found:
            if _debug:
                print "    - we're who they're looking for"
            self.BroadcastRoutingTable(adapter)
        else:
            if _debugAdapterRefs:
                print "    - looking for a path on other adapters"
            # it might be out there someplace
            newpdu = NPDU()
            newpdu.pduSource = None
            newpdu.pduDestination = LocalBroadcast()
            newpdu.npduNetMessage = NPDU.whoIsRouterToNetwork
            newpdu.PutShort(net)

            for ada in self.routerAdapters:
                if (ada is not adapter):
                    ada.Indication(newpdu)

    def IAmRouterToNetwork(self, adapter, npdu):
        if _debug:
            print "Router.IAmRouterToNetwork"

        # check each network
        while npdu.pduData:
            net = npdu.GetShort()

            # make sure it is not our of our direct connects
            if net in [a.adapterNet for a in self.routerAdapters]:
                continue

            # check references on this adapter
            for ref in adapter.adapterRefs:
                if npdu.pduSource == ref.refAddress:
                    if net not in ref.refNets:
                        if _debugAdapterRefs:
                            print "    - adding to existing reference", npdu.pduSource,"net",net
                        ref.refNets.append(net)
                    else:
                        if _debugAdapterRefs:
                            print "    - reference", npdu.pduSource,"already contains net",net
                    break
                elif net in ref.refNets:
                    if _debugAdapterRefs:
                        print "    - removing reference", npdu.pduSource,"to net",net
                    # moving to a different router on the same endpoint
                    ref.refNets.remove(net)
                    ### remove empty reference
            else:
                # no match, make a new reference
                if _debugAdapterRefs:
                    print "    - adding reference", npdu.pduSource,"to net",net
                adapter.adapterRefs.append(RouterReference(adapter, npdu.pduSource, [net]))
            ### make sure reference doesn't exist on a different adapter

    def Indication(self,apdu):
        if _debug:
            print "Router.Indication"
            print "    apdu.pduSource =", apdu.pduSource
            print "    apdu.pduDestination =", apdu.pduDestination
            print "    apdu.pduData =", StringToHex(apdu.pduData,'.')

        if len(self.routerAdapters) == 0:
            raise ConfigurationError, "no bound endpoints"

        # building an NPDU
        npdu = NPDU()

        # excode the data
        apdu.Encode(npdu)

        # set the hop count in case it's going to be routed
        npdu.npduHopCount = 255

        # make sure the expecting reply and priority are passed down
        npdu.pduExpectingReply = apdu.pduExpectingReply
        npdu.pduNetworkPriority = apdu.pduNetworkPriority

        # local station or local broadcast
        if (apdu.pduDestination.addrType == Address.localStationAddr) or (apdu.pduDestination.addrType == Address.localBroadcastAddr):
            if _debug:
                print "    - local message"
            if self.routerLocalAdapter:
                adapter = self.routerLocalAdapter
            elif len(self.routerAdapters) == 1:
                adapter = self.routerAdapters[0]
            else:
                raise ConfigurationError, "no local endpoint"

            # the destination is exactly as requested
            npdu.pduDestination = apdu.pduDestination

            # send it along
            adapter.Indication(npdu)

        # remote station or remote broadcast
        elif (apdu.pduDestination.addrType == Address.remoteStationAddr) or (apdu.pduDestination.addrType == Address.remoteBroadcastAddr):
            if _debugAdapterRefs:
                print "    - remote message"
            # check for the simple case
            if len(self.routerAdapters) == 1:
                if _debugAdapterRefs:
                    print "     - only one way for it to go"
                adapter = self.routerAdapters[0]

                # fill in the remote station DADR
                npdu.npduDADR = apdu.pduDestination

                # check for a reference to a router on this adapter
                for ref in adapter.adapterRefs:
                    if apdu.pduDestination.addrNet in ref.refNets:
                        if _debugAdapterRefs:
                            print "    - found a path via",ref.refAddress,"(2)"
                        npdu.pduDestination = ref.refAddress
                        break
                else:
                    if _debugAdapterRefs:
                        print "    - no path to network %d found, doing a broadcast" % (apdu.pduDestination.addrNet,)
                    # broadcast it and hope it gets there
                    npdu.pduDestination = LocalBroadcast()

                # send it along
                adapter.Indication(npdu)

                # all done with this one
                return

            # make sure at least one adapter is considered local
            if not self.routerLocalAdapter:
                raise ConfigurationError, "no local endpoint"

            # see if this should have been local
            elif apdu.pduDestination.addrNet == self.routerLocalAdapter.adapterNet:
                raise EncodingError, "no routing to local network"

            # this is going to be routed someplace
            else:
                if _debugAdapterRefs:
                    print "    - find a path"
                # fill ourselves in as a remote station
                npdu.npduSADR = self.routerLocalAddress

                # fill in the remote station DADR
                npdu.npduDADR = apdu.pduDestination

                # check for a directly connected adapter
                for adapter in self.routerAdapters:
                    # check for a directly connected adapter
                    if apdu.pduDestination.addrNet == adapter.adapterNet:
                        if _debugAdapterRefs:
                            print "    - found a direct connect (2)"
                        # doesn't need to be routed furthur
                        npdu.pduDestination = LocalStation(apdu.pduDestination.addrAddr)
                        break

                    # check for a reference to a router on this adapter
                    for ref in adapter.adapterRefs:
                        if apdu.pduDestination.addrNet in ref.refNets:
                            if _debugAdapterRefs:
                                print "    - found a path via",ref.refAddress,"(3)"
                            npdu.pduDestination = ref.refAddress
                            break
                    else:
                        continue
                    break
                else:
                    if _debugAdapterRefs:
                        print "    - no path to network %d found" % (apdu.pduDestination.addrNet,)
                    return

                # if we found a path, send it
                adapter.Indication(npdu)

        # global broadcast
        elif apdu.pduDestination.addrType == Address.globalBroadcastAddr:
            if _debug:
                print "    - global broadcast message"
            # fill in the global broadcast for all cases
            npdu.npduDADR = apdu.pduDestination

            # this will also be broadcast
            npdu.pduDestination = LocalBroadcast()

            # check for the simple case
            if len(self.routerAdapters) == 1:
                self.routerAdapters[0].Indication(npdu)
            else:
                # make sure at least one adapter is considered local
                if not self.routerLocalAdapter:
                    raise ConfigurationError, "no local endpoint"

                # everywhere you want to be
                for adapter in self.routerAdapters:
                    # check to see if it should look routed
                    if adapter is self.routerLocalAdapter:
                        if _debugAdapterRefs:
                            print "    - this is not routed"
                        npdu.npduSADR = None
                    else:
                        if _debugAdapterRefs:
                            print "    - make it look routed"
                        npdu.npduSADR = self.routerLocalAddress

                    # send it
                    adapter.Indication(npdu)

        else:
            raise EncodingError, "invalid destination address type"

    def DebugRoutingTables(self):
        print self, "Routing Tables"

        for adapter in self.routerAdapters:
            print "    Adapter", adapter.adapterNet
            for ref in adapter.adapterRefs:
                print "        Reference", ref.refAddress, ref.refNets

#
#   DebugClient
#

class DebugClient(Client):

    def __init__(self,prefix=''):
        self.prefix = prefix

    def Confirmation(self,*args,**kwargs):
        if _debug:
            print "DebugClient.Confirmation", args
        if args and isinstance(args[0],PDU):
            print
            pdu = args[0]
            if self.prefix:
                print self.prefix,
            print pdu.pduSource,'->',pdu.pduDestination,':', StringToHex(pdu.pduData,'.')
            print
        if args and isinstance(args[0],APDU):
            DebugAPDUContents(args[0])
            print
        self.Response(*args,**kwargs)

#
#   DebugServer
#

class DebugServer(Server):

    def __init__(self,prefix=''):
        self.prefix = prefix

    def Indication(self,*args,**kwargs):
        if _debug:
            print "DebugServer.Indication", args
        if args and isinstance(args[0],PDU):
            print
            pdu = args[0]
            if self.prefix:
                print self.prefix,
            print pdu.pduDestination,'<-',pdu.pduSource,':', StringToHex(pdu.pduData,'.')
            print
        if args and isinstance(args[0],APDU):
            DebugAPDUContents(args[0])
            print
        self.Request(*args,**kwargs)

#
#   DebugFilter
#

class DebugFilter(DebugClient,DebugServer):

    def __init__(self,prefix=''):
        DebugClient.__init__(self, prefix)
        DebugServer.__init__(self, prefix)

#----------------------------------------------------------------------

# segmentation supported
SEGMENTED_BOTH = 0
SEGMENTED_TRANSMIT = 1
SEGMENTED_RECEIVE = 2
NO_SEGMENTATION = 3

segmentationLabels = ['SEGMENTED_BOTH', 'SEGMENTED_TRANSMIT',
    'SEGMENTED_RECEIVE', 'NO_SEGMENTATION']

#
#   DeviceInfo
#

class DeviceInfo:

    def __init__(self):
        self.devid = None                   # database object identifier
        self.instance = None                # device instance number
        self.address = None                 # LocalStation or RemoteStation

        self.segmentation = NO_SEGMENTATION  # normally no segmentation
        self.maxAPDULength = 1024            # how big to divide up apdu's
        self.maxSegmentCount = None          # limit on how many segments to recieve

        # make sure the number picked is a valid one
        try:
            MaxAPDUResponseEncode(self.maxAPDULength)
        except:
            raise ValueError, "default maxAPDULength cannot be encoded"

#
#   GetDeviceInfo
#

def GetDeviceInfo(addr):
    """This function is called to associate a transaction with a remote
    device."""
    if _debugSegmentation:
        print "GetDeviceInfo", addr

    import CSBACnet

    # create an info object
    info = DeviceInfo()
    info.address = addr

    ### local stations are on network 5 in the database
    if addr.addrType == Address.localStationAddr:
        addr = RemoteStation( 5, addr.addrAddr )
        if _debugSegmentation:
            print "    - remapped to", addr

    # try to map the address to the database object identifier
    devid = CSBACnet.DeviceAddrToID.get(addr,None)
    if not devid:
        if _debugSegmentation:
            print "    - no devid"
        return info

    # try to load the object
    from CSObject import LoadObject, UnloadObject
    dev = LoadObject(devid)

    # hopefully it will always exist
    if not dev:
        if _debugSegmentation:
            print "    - device", devid, "not defined, database corrupted?"
        return info

    # get the segmentation
    seg = getattr(dev, 'segmentation', NO_SEGMENTATION)
    if seg:
        if _debugSegmentation:
            print "    - segmentation specified", seg
        info.segmentation = seg

    # get the maxAPDULength
    maxLen = getattr(dev, 'maxAPDULength', 0)
    if maxLen:
        if _debugSegmentation:
            print "    - maxAPDULength specified", maxLen
        info.maxAPDULength = int(maxLen)

    # make sure the number picked is a valid one
    try:
        MaxAPDUResponseEncode(info.maxAPDULength)
    except:
        raise ValueError, "default maxAPDULength cannot be encoded"

    return info

#
#   DebugDeviceInfo
#

def DebugDeviceInfo(info):
    print "    devid =", info.devid
    print "    instance =", info.instance
    print "    address =", info.address
    print "    segmentation =", info.segmentation
    print "    maxAPDULength =", info.maxAPDULength
    print "    maxSegmentCount =", info.maxSegmentCount

#----------------------------------------------------------------------

#
#   SSM - Segmentation State Machine
#

# transaction states
IDLE = 0
SEGMENTED_REQUEST = 1
AWAIT_CONFIRMATION = 2
AWAIT_RESPONSE = 3
SEGMENTED_RESPONSE = 4
SEGMENTED_CONFIRMATION = 5
COMPLETED = 6
ABORTED = 7

class SSM(Task):

    transactionLabels = ['IDLE'
        , 'SEGMENTED_REQUEST', 'AWAIT_CONFIRMATION', 'AWAIT_RESPONSE'
        , 'SEGMENTED_RESPONSE', 'SEGMENTED_CONFIRMATION', 'COMPLETED', 'ABORTED'
        ]

    def __init__(self):
        """Common parts for client and server segmentation."""
        Task.__init__(self, Task.oneShotTask)

        self.localDevice = None             # local device
        self.remoteDevice = None            # remote device
        self.invokeID = None                # invoke ID

        self.state = IDLE                   # initial state
        self.segmentAPDU = None             # refers to request or response
        self.segmentSize = None             # how big the pieces are
        self.segmentCount = None
        self.maxSegmentCount = None         # maximum number of segments client will accept

        self.retryCount = None
        self.segmentRetryCount = None
        self.sentAllSegments = None
        self.lastSequenceNumber = None
        self.initialSequenceNumber = None
        self.actualWindowSize = None
        self.proposedWindowSize = None

    def StartTimer(self, msecs):
        if _debugSegmentation:
            print self, "SSM.StartTimer", msecs

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.taskType = Task.oneShotTask
        self.taskInterval = msecs
        self.InstallTask()

    def StopTimer(self):
        if _debugSegmentation:
            print self, "SSM.StopTimer"

        self.SuspendTask()

    def RestartTimer(self, msecs):
        if _debugSegmentation:
            print self, "SSM.RestartTimer", msecs

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.taskType = Task.oneShotTask
        self.taskInterval = msecs
        self.InstallTask()

    def SetState(self, newState, timer=0):
        """This function is called when the derived class wants to change
        state."""
        if _debugSegmentation:
            print self, "SSM.SetState", SSM.transactionLabels[newState]

        # make sure we have a correct transition
        if (self.state == COMPLETED) or (self.state == ABORTED):
            raise RuntimeError, "invalid state transition from %s to %s" % (SSM.transactionLabels[self.state], SSM.transactionLabels[newState])

        self.state = newState

        # stop any current timer
        self.StopTimer()

        # make the change
        self.state = newState

        # if another timer should be started, start it
        if timer:
            self.StartTimer(timer)

    def SetSegmentationContext(self, apdu):
        """This function is called to set the segmentation context."""
        if _debugSegmentation:
            print self, "SSM.SetSegmentationContext", apdu

        # set the context
        self.segmentAPDU = apdu

    def GetSegment(self, indx):
        """This function returns an APDU coorisponding to a particular
        segment of a confirmed request or complex ack.  The segmentAPDU
        is the context."""
        if _debugSegmentation:
            print self, "SSM.GetSegment", indx

        # check for no context
        if not self.segmentAPDU:
            raise exceptions.RuntimeError, "no segmentation context established"

        # check for invalid segment number
        if indx >= self.segmentCount:
            raise RuntimeError, "invalid segment number %d, APDU has %d segments" % (indx, self.segmentCount)

        if self.segmentAPDU.apduType == APDU.confirmedRequest:
            if _debugSegmentation:
                print "    - confirmed request context"

            segAPDU = ConfirmedRequestAPDU(self.segmentAPDU.apduService)

            segAPDU.apduMaxSegs = self.maxSegmentCount
            segAPDU.apduMaxResp = self.localDevice.maxAPDULength
            segAPDU.apduInvokeID = self.invokeID;

            # segmented response accepted?
            segAPDU.apduSA = ((self.localDevice.segmentation == SEGMENTED_BOTH) \
                    or (self.localDevice.segmentation == SEGMENTED_RECEIVE))
            if _debugSegmentation:
                print "    - segmented response accepted:", segAPDU.apduSA
                print "        - self.localDevice.segmentation", self.localDevice.segmentation

        elif self.segmentAPDU.apduType == APDU.complexAck:
            if _debugSegmentation:
                print "    - complex ack context"

            segAPDU = ComplexAckAPDU(self.segmentAPDU.apduService, self.segmentAPDU.apduInvokeID)
        else:
            raise exceptions.RuntimeError, "invalid APDU type for segmentation context"

        # make sure the destination is set
        segAPDU.pduDestination = self.remoteDevice.address

        # segmented message?
        if (self.segmentCount != 1):
            segAPDU.apduSeg = True
            segAPDU.apduMor = (indx < (self.segmentCount - 1)) # more follows
            segAPDU.apduSeq = indx % 256                       # sequence number
            segAPDU.apduWin = self.proposedWindowSize          # window size
        else:
            segAPDU.apduSeg = False
            segAPDU.apduMor = False

        # add the content
        offset = indx * self.segmentSize
        segAPDU.PutData( self.segmentAPDU.pduData[offset:offset+self.segmentSize] )

        # success
        return segAPDU

    def AppendSegment(self, apdu):
        """This function appends the apdu content to the end of the current
        APDU being built.  The segmentAPDU is the context."""
        if _debugSegmentation:
            print self, "SSM.AppendSegment"

        # check for no context
        if not self.segmentAPDU:
            raise exceptions.RuntimeError, "no segmentation context established"

        # append the data
        self.segmentAPDU.PutData(apdu.pduData)

    def InWindow(self, seqA, seqB):
        if _debugSegmentation:
            print self, "SSM.InWindow", seqA, seqB
            print "    - actualWindowSize", self.actualWindowSize

        rslt = ((seqA - seqB + 256) % 256) < self.actualWindowSize
        if _debugSegmentation:
            print "    - rslt", rslt

        return rslt

    def FillWindow(self, seqNum):
        """This function sends all of the packets necessary to fill
        out the segmentation window."""
        if _debugSegmentation:
            print self, "SSM.FillWindow", seqNum
            print "    - actualWindowSize", self.actualWindowSize

        for ix in range(self.actualWindowSize):
            apdu = self.GetSegment(seqNum + ix)

            # send the message
            self.localDevice.Request(apdu)

            # check for no more follows
            if not apdu.apduMor:
                self.sentAllSegments = True
                break

#
#   DebugSSM
#

def DebugSSM(sm):
    print "    state =", SSM.transactionLabels[sm.state]
    print "    segmentSize =", sm.segmentSize
    print "    segmentCount =", sm.segmentCount
    print "    maxSegmentCount =", sm.maxSegmentCount
    print "    retryCount =", sm.retryCount
    print "    segmentRetryCount =", sm.segmentRetryCount
    print "    sentAllSegments =", sm.sentAllSegments
    print "    lastSequenceNumber =", sm.lastSequenceNumber
    print "    initialSequenceNumber =", sm.initialSequenceNumber
    print "    actualWindowSize =", sm.actualWindowSize
    print "    proposedWindowSize =", sm.proposedWindowSize

#
#   ClientSSM - Client Segmentation State Machine
#

class ClientSSM(SSM):

    def __init__(self):
        SSM.__init__(self)

        # initialize the retry count
        self.retryCount = 0

    def SetState(self, newState, timer=0):
        """This function is called when the client wants to change state."""
        if _debugSegmentation:
            print self, "ClientSSM.SetState"

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.localDevice.clientTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by client transaction functions when it wants
        to send a message to the device."""
        if _debugSegmentation:
            print self, "ClientSSM.Request", apdu

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.localDevice.Request(apdu)

    def Indication(self, apdu):
        """This function is called after the device has bound a new transaction
        and wants to start the process rolling."""
        if _debugSegmentation:
            print self, "ClientSSM.Indication", apdu
            DebugSSM(self)

        # make sure we're getting confirmed requests
        if (apdu.apduType != APDU.confirmedRequest):
            raise RuntimeError, "invalid APDU"

        # save the request and set the segmentation context
        self.SetSegmentationContext(apdu)

        # save the maximum number of segments acceptable in the reply
        if apdu.apduMaxSegs is not None:
            # this request overrides the default
            self.maxSegmentCount = apdu.apduMaxSegs
        else:
            # use the default in the device definition
            self.maxSegmentCount = self.localDevice.maxSegmentCount

        # save the invoke ID
        self.invokeID = apdu.apduInvokeID
        if _debugSegmentation:
            print "    - invoke ID", self.invokeID

        # get information about the device
        self.remoteDevice = GetDeviceInfo(apdu.pduDestination)
        if _debugSegmentation:
            DebugDeviceInfo(self.remoteDevice)

        # the segment size is the minimum of what I want to transmit and
        # what the device can receive
        self.segmentSize = min(self.localDevice.maxAPDULength, self.remoteDevice.maxAPDULength)
        if _debugSegmentation:
            print "    - segment size =", self.segmentSize

        # compute the segment count ### minus the header?
        self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
        if more:
            self.segmentCount += 1
        if _debugSegmentation:
            print "    - segment count =", self.segmentCount

        # make sure we support segmented transmit if we need to
        if self.segmentCount > 1:
            if (self.localDevice.segmentation != SEGMENTED_TRANSMIT) and (self.localDevice.segmentation != SEGMENTED_BOTH):
                if _debugSegmentation:
                    print "    - local device can't send segmented messages"
                abort = self.Abort(AbortAPDU.segmentationNotSupported)
                self.Response(abort)
                return
            if (self.remoteDevice.segmentation != SEGMENTED_RECEIVE) and (self.remoteDevice.segmentation != SEGMENTED_BOTH):
                if _debugSegmentation:
                    print "    - remote device can't receive segmented messages"
                abort = self.Abort(AbortAPDU.segmentationNotSupported)
                self.Response(abort)
                return

        # send out the first segment (or the whole thing)
        if self.segmentCount == 1:
            # SendConfirmedUnsegmented
            self.sentAllSegments = True
            self.retryCount = 0
            self.SetState(AWAIT_CONFIRMATION, self.localDevice.retryTimeout)
        else:
            # SendConfirmedSegmented
            self.sentAllSegments = False
            self.retryCount = 0
            self.segmentRetryCount = 0
            self.initialSequenceNumber = 0
            self.proposedWindowSize = self.localDevice.windowSize
            self.actualWindowSize = 1
            self.SetState(SEGMENTED_REQUEST, self.localDevice.segmentTimeout)

        # deliver to the device
        self.Request(self.GetSegment(0))

    def Response(self, apdu):
        """This function is called by client transaction functions when they want
        to send a message to the application."""
        if _debugSegmentation:
            print self, "ClientSSM.Response", apdu

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it to the application
        self.localDevice.AppResponse(apdu)

    def Confirmation(self, apdu):
        """This function is called by the device for all upstream messages related
        to the transaction."""
        if _debugSegmentation:
            print self, "ClientSSM.Confirmation", apdu
            DebugSSM(self)

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequest(apdu)
        elif self.state == AWAIT_CONFIRMATION:
            self.AwaitConfirmation(apdu)
        elif self.state == SEGMENTED_CONFIRMATION:
            self.SegmentedConfirmation(apdu)
        else:
            raise RuntimeError, "invalid state"

    def ProcessTask(self):
        """This function is called when something has taken too long."""
        if _debugSegmentation:
            print self, "ClientSSM.ProcessTask"
            DebugSSM(self)

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequestTimeout()
        elif self.state == AWAIT_CONFIRMATION:
            self.AwaitConfirmationTimeout()
        elif self.state == SEGMENTED_CONFIRMATION:
            self.SegmentedConfirmationTimeout()
        elif self.state == COMPLETED:
            pass
        elif self.state == ABORTED:
            pass
        else:
            raise RuntimeError, "invalid state"

    def Abort(self, reason):
        """This function is called when the transaction should be aborted."""
        if _debugSegmentation:
            print "=" * 20, "ABORT", reason, "=" * 20
            print self, "ClientSSM.Abort", reason

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortAPDU(False, self.invokeID, reason)

    def SegmentedRequest(self, apdu):
        """This function is called when the client is sending a segmented request
        and receives an apdu."""
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedRequest", apdu

        # client is ready for the next segment
        if apdu.apduType == APDU.segmentAck:
            if _debugSegmentation:
                print "    - segment ack"
                print "        - apdu.apduSeq", apdu.apduSeq
                print "        - apdu.apduNak", apdu.apduNak

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                if _debugSegmentation:
                    print "    - not in window"
                self.RestartTimer(self.localDevice.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                if _debugSegmentation:
                    print "    - all done sending request"
                self.SetState(AWAIT_CONFIRMATION, self.localDevice.retryTimeout)

            # more segments to send
            else:
                if _debugSegmentation:
                    print "    - more segments to send"

                self.initialSequenceNumber = (apdu.apduSeq + 1) % 256
                self.actualWindowSize = apdu.apduWin
                self.segmentRetryCount = 0
                self.FillWindow(self.initialSequenceNumber)
                self.RestartTimer(self.localDevice.segmentTimeout)

        # simple ack
        elif (apdu.apduType == APDU.simpleAck):
            if _debugSegmentation:
                print "    - simple ack"

            if not self.sentAllSegments:
                abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
                self.Request(abort)     # send it to the device
                self.Response(abort)    # send it to the application
            else:
                self.SetState(COMPLETED)
                self.Response(apdu)

        elif (apdu.apduType == APDU.complexAck):
            if _debugSegmentation:
                print "    - complex ack"

            if not self.sentAllSegments:
                abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
                self.Request(abort)     # send it to the device
                self.Response(abort)    # send it to the application

            elif not apdu.apduSeg:
                self.SetState(COMPLETED)
                self.Response(apdu)

            else:
                # set the segmented response context
                self.SetSegmentationContext(apdu)

                self.actualWindowSize = min(apdu.apduWin, self.localDevice.windowSize)
                self.lastSequenceNumber = 0
                self.initialSequenceNumber = 0
                self.SetState(SEGMENTED_CONFIRMATION, self.localDevice.segmentTimeout)

        # some kind of problem
        elif (apdu.apduType == APDU.error) or (apdu.apduType == APDU.reject) or (apdu.apduType == APDU.abort):
            if _debugSegmentation:
                print "    - error/reject/abort"

            self.SetState(COMPLETED)
            self.response = apdu
            self.Response(apdu)

        else:
            raise RuntimeError, "invalid APDU"

    def SegmentedRequestTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedRequestTimeout"

        # try again
        if self.segmentRetryCount < self.localDevice.retryCount:
            if _debugSegmentation:
                print "    - retry segmented request"

            self.segmentRetryCount += 1
            self.StartTimer(self.localDevice.segmentTimeout)
            self.FillWindow(self.initialSequenceNumber)
        else:
            if _debugSegmentation:
                print "    - abort, no response from the device"

            abort = self.Abort(AbortAPDU.noResponse)
            self.Response(abort)

    def AwaitConfirmation(self, apdu):
        if _debugSegmentation:
            print self, "ClientSSM.AwaitConfirmation", apdu

        if (apdu.apduType == APDU.abort):
            if _debugSegmentation:
                print "    - server aborted"

            self.SetState(ABORTED)
            self.Response(apdu)

        elif (apdu.apduType == APDU.simpleAck) or (apdu.apduType == APDU.error) or (apdu.apduType == APDU.reject):
            if _debugSegmentation:
                print "    - simple ack, error, or reject"

            self.SetState(COMPLETED)
            self.Response(apdu)

        elif (apdu.apduType == APDU.complexAck):
            if _debugSegmentation:
                print "    - complex ack"

            # if the response is not segmented, we're done
            if not apdu.apduSeg:
                if _debugSegmentation:
                    print "    - unsegmented"

                self.SetState(COMPLETED)
                self.Response(apdu)

            elif (self.localDevice.segmentation != SEGMENTED_RECEIVE) and (self.localDevice.segmentation != SEGMENTED_BOTH):
                if _debugSegmentation:
                    print "    - local device can't receive segmented messages"
                abort = self.Abort(AbortAPDU.segmentationNotSupported)
                self.Response(abort)

            elif apdu.apduSeq == 0:
                if _debugSegmentation:
                    print "    - segmented response"

                # set the segmented response context
                self.SetSegmentationContext(apdu)

                self.actualWindowSize = min(apdu.apduWin, self.localDevice.windowSize)
                self.lastSequenceNumber = 0
                self.initialSequenceNumber = 0
                self.SetState(SEGMENTED_CONFIRMATION, self.localDevice.segmentTimeout)

                # send back a segment ack
                segack = SegmentAckAPDU( 0, 0, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                self.Request(segack)

            else:
                if _debugSegmentation:
                    print "    - invalid APDU in this state"

                abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
                self.Request(abort) # send it to the device
                self.Response(abort) # send it to the application

        elif (apdu.apduType == APDU.segmentAck):
            if _debugSegmentation:
                print "    - segment ack(!?)"

            self.RestartTimer(self.localDevice.segmentTimeout)

        else:
            raise RuntimeError, "invalid APDU"

    def AwaitConfirmationTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.AwaitConfirmationTimeout"

        self.retryCount += 1
        if self.retryCount < self.localDevice.retryCount:
            if _debugSegmentation:
                print "    - no response, try again (%d < %d)" % (self.retryCount, self.localDevice.retryCount)

            # save the retry count, Indication acts like the request is coming
            # from the application so the retryCount gets re-initialized.
            saveCount = self.retryCount
            self.Indication(self.segmentAPDU)
            self.retryCount = saveCount
        else:
            if _debugSegmentation:
                print "    - retry count exceeded"
            abort = self.Abort(AbortAPDU.noResponse)
            self.Response(abort)

    def SegmentedConfirmation(self, apdu):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedConfirmation", apdu

        # the only messages we should be getting are complex acks
        if (apdu.apduType != APDU.complexAck):
            if _debugSegmentation:
                print "    - complex ack required"

            abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        if not apdu.apduSeg:
            if _debugSegmentation:
                print "    - must be segmented"

            abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            if _debugSegmentation:
                print "    - segment", apdu.apduSeq, "received out of order, should be", (self.lastSequenceNumber + 1) % 256

            # segment received out of order
            self.RestartTimer(self.localDevice.segmentTimeout)
            segack = SegmentAckAPDU( 1, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)
            return

        # add the data
        self.AppendSegment(apdu)

        # update the sequence number
        self.lastSequenceNumber = (self.lastSequenceNumber + 1) % 256

        # last segment received
        if not apdu.apduMor:
            if _debugSegmentation:
                print "    - no more follows"

            # send a final ack
            segack = SegmentAckAPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

            self.SetState(COMPLETED)
            self.Response(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
            if _debugSegmentation:
                print "    - last segment in the group"

            self.initialSequenceNumber = self.lastSequenceNumber
            self.RestartTimer(self.localDevice.segmentTimeout)
            segack = SegmentAckAPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

        else:
            # wait for more segments
            if _debugSegmentation:
                print "    - wait for more segments"

            self.RestartTimer(self.localDevice.segmentTimeout)

    def SegmentedConfirmationTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedConfirmationTimeout"

        abort = self.Abort(AbortAPDU.noResponse)
        self.Response(abort)

#
#   ServerSSM - Server Segmentation State Machine
#

class ServerSSM(SSM):

    def __init__(self):
        SSM.__init__(self)

    def SetState(self, newState, timer=0):
        """This function is called when the client wants to change state."""
        if _debugSegmentation:
            print self, "ServerSSM.SetState"

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.localDevice.serverTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by transaction functions to send
        to the application."""
        if _debugSegmentation:
            print self, "ServerSSM.Request", apdu

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it via the device
        self.localDevice.AppRequest(apdu)

    def Indication(self, apdu):
        """This function is called for each downstream packet related to
        the transaction."""
        if _debugSegmentation:
            print self, "ServerSSM.Indication", apdu
            DebugSSM(self)

        if self.state == IDLE:
            self.Idle(apdu)
        elif self.state == SEGMENTED_REQUEST:
            self.SegmentedRequest(apdu)
        elif self.state == AWAIT_RESPONSE:
            self.AwaitResponse(apdu)
        elif self.state == SEGMENTED_RESPONSE:
            self.SegmentedResponse(apdu)
        else:
            raise RuntimeError, "invalid state"

    def Response(self, apdu):
        """This function is called by transaction functions when they want
        to send a message to the device."""
        if _debugSegmentation:
            print self, "ServerSSM.Response", apdu

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.localDevice.Request(apdu)

    def Confirmation(self, apdu):
        """This function is called when the application has provided a response
        and needs it to be sent to the client."""
        if _debugSegmentation:
            print self, "ServerSSM.Confirmation", apdu
            DebugSSM(self)

        if (apdu.apduType == APDU.abort):
            if _debugSegmentation:
                print "    - abort"

            self.SetState(ABORTED)

            # send the response to the device
            self.Response(apdu)
            return

        if self.state != AWAIT_RESPONSE:
            if _debugSegmentation:
                print "    - warning: not expecting a response"

        # simple response
        if (apdu.apduType == APDU.simpleAck) or (apdu.apduType == APDU.error) or (apdu.apduType == APDU.reject):
            if _debugSegmentation:
                print "    - simple ack, error, or reject"

            # transaction completed
            self.SetState(COMPLETED)

            # send the response to the device
            self.Response(apdu)
            return

        if (apdu.apduType == APDU.complexAck):
            if _debugSegmentation:
                print "    - complex ack"

            # save the response and set the segmentation context
            self.SetSegmentationContext(apdu)

            # the segment size is the minimum of what I want to transmit and
            # what the device can receive
            self.segmentSize = min(self.localDevice.maxAPDULength, self.remoteDevice.maxAPDULength)
            if _debugSegmentation:
                print "    - segment size =", self.segmentSize

            # compute the segment count ### minus the header?
            self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
            if more:
                self.segmentCount += 1
            if _debugSegmentation:
                print "    - segment count =", self.segmentCount

            # make sure we support segmented transmit if we need to
            if self.segmentCount > 1:
                if _debugSegmentation:
                    print "    - segmentation required,", self.segmentCount, "segments"

                if (self.localDevice.segmentation != SEGMENTED_TRANSMIT) and (self.localDevice.segmentation != SEGMENTED_BOTH):
                    abort = self.Abort(AbortAPDU.segmentationNotSupported)
                    self.Request(abort)
                    return
                if (self.remoteDevice.segmentation != SEGMENTED_RECEIVE) and (self.remoteDevice.segmentation != SEGMENTED_BOTH):
                    abort = self.Abort(AbortAPDU.segmentationNotSupported)
                    self.Request(abort)
                    return

            ### check to make sure the client can receive that many
            ### look at apduMaxSegs

            # initialize the state
            self.segmentRetryCount = 0
            self.initialSequenceNumber = 0
            self.proposedWindowSize = self.localDevice.windowSize
            self.actualWindowSize = 1

            # send out the first segment (or the whole thing)
            if self.segmentCount == 1:
                self.Response(apdu)
                self.SetState(COMPLETED)
            else:
                self.Response(self.GetSegment(0))
                self.SetState(SEGMENTED_RESPONSE, self.localDevice.segmentTimeout)

        else:
            raise RuntimeError, "invalid APDU"

    def ProcessTask(self):
        """This function is called when the client has failed to send all of the
        segments of a segmented request, the application has taken too long to
        complete the request, or the client failed to ack the segments of a
        segmented response."""
        if _debugSegmentation:
            print self, "ServerSSM.ProcessTask"
            DebugSSM(self)

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequestTimeout()
        elif self.state == AWAIT_RESPONSE:
            self.AwaitResponseTimeout()
        elif self.state == SEGMENTED_RESPONSE:
            self.SegmentedResponseTimeout()
        elif self.state == COMPLETED:
            pass
        elif self.state == ABORTED:
            pass
        else:
            raise RuntimeError, "invalid state"

    def Abort(self, reason):
        """This function is called when the application would like to abort the
        transaction.  There is no notification back to the application."""
        if _debugSegmentation:
            print "=" * 20, "ABORT", reason, "=" * 20
            print self, "ServerSSM.Abort", reason

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortAPDU(True, self.invokeID, reason)

    def Idle(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.Idle", apdu

        # make sure we're getting confirmed requests
        if (apdu.apduType != APDU.confirmedRequest):
            raise RuntimeError, "invalid APDU"

        # save the invoke ID
        self.invokeID = apdu.apduInvokeID
        if _debugSegmentation:
            print "    - invoke ID", self.invokeID

        # get information about the device
        self.remoteDevice = GetDeviceInfo( apdu.pduSource )
        if _debugSegmentation:
            DebugDeviceInfo(self.remoteDevice)

        # save the number of segments the client is willing to accept in the ack
        self.maxSegmentCount = apdu.apduMaxSegs

        # unsegmented request
        if not apdu.apduSeg:
            self.SetState(AWAIT_RESPONSE, self.localDevice.applicationTimeout)
            self.Request(apdu)
            return

        # make sure we support segmented requests
        if (self.localDevice.segmentation != SEGMENTED_RECEIVE) and (self.localDevice.segmentation != SEGMENTED_BOTH):
            abort = self.Abort(AbortAPDU.segmentationNotSupported)
            self.Response(abort)
            return

        # save the request and set the segmentation context
        self.SetSegmentationContext(apdu)

        # the window size is the minimum of what I'm willing to receive and
        # what the device has said it would like to send
        self.actualWindowSize = min(apdu.apduWin, self.localDevice.windowSize)

        # initialize the state
        self.lastSequenceNumber = 0
        self.initialSequenceNumber = 0
        self.SetState(SEGMENTED_REQUEST, self.localDevice.segmentTimeout)

        # send back a segment ack
        segack = SegmentAckAPDU( 0, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
        self.Response(segack)

    def SegmentedRequest(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedRequest", apdu

        # some kind of problem
        if (apdu.apduType == APDU.abort):
            if _debugSegmentation:
                print "    - abort"

            self.SetState(COMPLETED)
            self.Response(apdu)
            return

        # the only messages we should be getting are confirmed requests
        elif (apdu.apduType != APDU.confirmedRequest):
            if _debugSegmentation:
                print "    - confirmed request required"

            abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        elif not apdu.apduSeg:
            abort = self.Abort(AbortAPDU.invalidAPDUInThisState)
            self.Request(abort) # send it to the application
            self.Response(abort) # send it to the device
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            if _debugSegmentation:
                print "    - segment", apdu.apduSeq, "received out of order, should be", (self.lastSequenceNumber + 1) % 256

            # segment received out of order
            self.RestartTimer(self.localDevice.segmentTimeout)

            # send back a segment ack
            segack = SegmentAckAPDU( 1, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
            self.Response(segack)
            return

        # add the data
        self.AppendSegment(apdu)

        # update the sequence number
        self.lastSequenceNumber = (self.lastSequenceNumber + 1) % 256

        # last segment?
        if not apdu.apduMor:
            if _debugSegmentation:
                print "    - no more follows"

            # send back a final segment ack
            segack = SegmentAckAPDU( 0, 1, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Response(segack)

            # forward the whole thing to the application
            self.SetState(AWAIT_RESPONSE, self.localDevice.applicationTimeout)
            self.Request(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
                if _debugSegmentation:
                    print "    - last segment in the group"

                self.initialSequenceNumber = self.lastSequenceNumber
                self.RestartTimer(self.localDevice.segmentTimeout)

                # send back a segment ack
                segack = SegmentAckAPDU( 0, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                self.Response(segack)

        else:
            # wait for more segments
            if _debugSegmentation:
                print "    - wait for more segments"

            self.RestartTimer(self.localDevice.segmentTimeout)

    def SegmentedRequestTimeout(self):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedRequestTimeout"

        # give up
        self.SetState(ABORTED)

    def AwaitResponse(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.AwaitResponse", apdu

        if (apdu.apduType == APDU.confirmedRequest):
            if _debugSegmentation:
                print "    - client is trying this request again"

        elif (apdu.apduType == APDU.abort):
            if _debugSegmentation:
                print "    - client aborting this request"

            # forward abort to the application
            self.SetState(ABORTED)
            self.Request(apdu)

        else:
            raise RuntimeError, "invalid APDU"

    def AwaitResponseTimeout(self):
        """This function is called when the application has taken too long
        to respond to a clients request.  The client has probably long since
        given up."""
        if _debugSegmentation:
            print self, "ServerSSM.AwaitResponseTimeout"

        abort = self.Abort(AbortAPDU.serverTimeout)
        self.Request(apdu)

    def SegmentedResponse(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedResponse", apdu

        # client is ready for the next segment
        if (apdu.apduType == APDU.segmentAck):
            if _debugSegmentation:
                print "    - segment ack"
                print "        - apdu.apduSeq", apdu.apduSeq
                print "        - apdu.apduNak", apdu.apduNak

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                if _debugSegmentation:
                    print "    - not in window"
                self.RestartTimer(self.localDevice.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                if _debugSegmentation:
                    print "    - all done sending response"
                self.SetState(COMPLETED)

            else:
                if _debugSegmentation:
                    print "    - more segments to send"

                self.initialSequenceNumber = (apdu.apduSeq + 1) % 256
                self.actualWindowSize = apdu.apduWin
                self.segmentRetryCount = 0
                self.FillWindow(self.initialSequenceNumber)
                self.RestartTimer(self.localDevice.segmentTimeout)

        # some kind of problem
        elif (apdu.apduType == APDU.abort):
            self.SetState(COMPLETED)
            self.Response(apdu)

        else:
            raise RuntimeError, "invalid APDU"

    def SegmentedResponseTimeout(self):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedResponseTimeout"

        # try again
        if self.segmentRetryCount < self.localDevice.retryCount:
            self.segmentRetryCount += 1
            self.StartTimer(self.localDevice.segmentTimeout)
            self.FillWindow(self.initialSequenceNumber)
        else:
            # give up
            self.SetState(ABORTED)

#
#   Device
#

class Device(DeviceInfo,Client,AppClient,AppServer):

    def __init__(self):
        DeviceInfo.__init__(self)
        Client.__init__(self)
        AppClient.__init__(self)
        AppServer.__init__(self)
        
        self.application = None

        # client settings
        self.clientTransactions = []
        self.retryCount = 3                     # how many times to repeat the request
        self.retryTimeout = 3 * 1000            # how long between retrying the request
        self.nextInvokeID = 1

        # server settings
        self.serverTransactions = []
        self.applicationTimeout = 60 * 1000     # how long the application has to respond

        # segmentation SSM settings
        self.segmentTimeout = 2 * 1000          # how long to wait for a segAck
        self.windowSize = 5                     # how many to send before waiting for a segAck

    def GetInvokeID(self):
        """Called by clients to get an unused invoke ID."""
        initialID = self.nextInvokeID
        while 1:
            invokeID = self.nextInvokeID
            self.nextInvokeID = (self.nextInvokeID + 1) % 256

            # see if we've checked for them all
            if initialID == self.nextInvokeID:
                raise RuntimeError, "no available invoke ID"

            for tr in self.clientTransactions:
                if invokeID == tr.invokeID:
                    break
            else:
                break

        return invokeID

    def Confirmation(self,apdu):
        """Packets coming up the stack are APDU's."""
        if _debug:
            print "Device.Confirmation"
            DebugAPDUContents(apdu)

        if (apdu.apduType == APDU.confirmedRequest):
            if _debug:
                print "    - confirmed request"

            # find duplicates of this request
            for tr in self.serverTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                    break
            else:
                # build a server transaction
                tr = ServerSSM()

                # bind to this device and track it
                tr.localDevice = self
                self.serverTransactions.append(tr)

            # let it run with the apdu
            tr.Indication(apdu)

        elif (apdu.apduType == APDU.unconfirmedRequest):
            if _debug:
                print "    - unconfirmed request"

            # deliver directly to the application
            self.AppRequest(apdu)

        elif (apdu.apduType == APDU.simpleAck) or (apdu.apduType == APDU.complexAck) or (apdu.apduType == APDU.error) or (apdu.apduType == APDU.reject):
            if _debug:
                print "    - ack/error/reject"

            # find the client transaction this is acking
            for tr in self.clientTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.apduInvokeID == tr.invokeID):
                    if not(apdu.pduSource == tr.remoteDevice.address):
                        if _debug:
                            print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                    break
            else:
                if _debug:
                    print "    - no matching client transaction"
                return

            # send the packet on to the transaction
            tr.Confirmation(apdu)

        elif (apdu.apduType == APDU.abort):
            if _debug:
                print "    - abort"

            # find the transaction being aborted
            if apdu.apduSrv:
                for tr in self.clientTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            if _debug:
                                print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    if _debug:
                        print "    - no matching client transaction"
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                for tr in self.serverTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    if _debug:
                        print "    - no matching server transaction"
                    return

                # send the packet on to the transaction
                tr.Indication(apdu)

        elif (apdu.apduType == APDU.segmentAck):
            if _debug:
                print "    - segment ack"

            # find the transaction being aborted
            if apdu.apduSrv:
                for tr in self.clientTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            if _debug:
                                print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    if _debug:
                        print "    - no matching client transaction"
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                for tr in self.serverTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    if _debug:
                        print "    - no matching server transaction"
                    return

                # send the packet on to the transaction
                tr.Indication(apdu)

        else:
            raise RuntimeError, "invalid APDU"

    def AppIndication(self, apdu):
        """This function is called when the application is requesting
        a new transaction as a client."""
        if _debug:
            print self, "Device.AppIndication", apdu
            print apdu.pduSource, '->', apdu.pduDestination, ':', StringToHex(apdu.pduData,'.')
            DebugAPDUContents(apdu)

        if (apdu.apduType == APDU.unconfirmedRequest):
            if _debug:
                print "    - unconfirmed request"

            # deliver to the device
            self.Request(apdu)

        elif (apdu.apduType == APDU.confirmedRequest):
            if _debug:
                print "    - confirmed request"

            # make sure it has an invoke ID
            if apdu.apduInvokeID is None:
                apdu.apduInvokeID = self.GetInvokeID()
            else:
                # verify the invoke ID isn't already being used
                for tr in self.clientTransactions:
                    if apdu.apduInvokeID == tr.invokeID:
                        raise RuntimeError, "invoke ID in use"

            # warning for bogus requests
            if (apdu.pduDestination.addrType != Address.localStationAddr) and (apdu.pduDestination.addrType != Address.remoteStationAddr):
                if _debug:
                    print "    - warning, %s is not a local or remote station" % (apdu.pduDestination,)

            # create a client transaction
            tr = ClientSSM()

            # bind it to this device and track it
            tr.localDevice = self
            self.clientTransactions.append(tr)

            # let it run
            tr.Indication(apdu)

        else:
            raise RuntimeError, "invalid APDU"

    def AppConfirmation(self, apdu):
        """This function is called when the application is responding
        to a request, the apdu may be a simple ack, complex ack, error, reject or abort."""
        if _debug:
            print self, "Device.AppConfirmation", apdu
            print apdu.pduSource, '->', apdu.pduDestination, ':', StringToHex(apdu.pduData,'.')
            DebugAPDUContents(apdu)

        if (apdu.apduType == APDU.simpleAck) or (apdu.apduType == APDU.complexAck) or (apdu.apduType == APDU.error) or (apdu.apduType == APDU.reject):
            # find the appropriate server transaction
            for tr in self.serverTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.pduDestination == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                    break
            else:
                if _debug:
                    print "    - no matching server transaction"
                return

            # pass control to the transaction
            tr.Confirmation(apdu)

        else:
            raise RuntimeError, "invalid APDU"

#
#   Bind
#

def Bind(*args):
    """Bind a list of clients and servers together, top down."""
    # go through the pairs
    for i in xrange(len(args)-1):
        client = args[i]
        server = args[i+1]

        # make sure we're binding clients and servers
        if isinstance(client,Client) and isinstance(server,Server):
            client.clientPeer = server
            server.serverPeer = client

        # we could be binding application clients and servers
        elif isinstance(client,AppClient) and isinstance(server,AppServer):
            client.appClientPeer = server
            server.appServerPeer = client

        # error
        else:
            raise TypeError, "Bind() requires a client and server"
