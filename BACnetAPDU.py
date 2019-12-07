"""
Some useful classes.
"""

from BACnet import *

#
#   Enumerations
#

class BinaryPV(Enumerated):
    enumerations = \
        { 'inactive':0
        , 'active':1
        }

class ErrorClass(Enumerated):
    enumerations = \
        { 'device':0
        , 'object':1
        , 'property':2
        , 'resources':3
        , 'security':4
        , 'services':5
        , 'vt':6
        }

class ErrorCode(Enumerated):
    enumerations = \
        { 'other':0
        , 'authentication-failed':1
        , 'character-set-not-supported':41
        , 'configuration-in-progress':2
        , 'datatype-not-supported':47
        , 'device-busy':3
        , 'duplicate-name':48
        , 'duplicate-object-id':49
        , 'dynamic-creation-not-supported':4
        , 'file-access-denied':5
        , 'incompatible-security-levels':6
        , 'inconsistent-parameters':7
        , 'inconsistent-selection-criteria':8
        , 'invalid-array-index':42
        , 'invalid-configuration-data':46
        , 'invalid-data-type':9
        , 'invalid-file-access-method':10
        , 'invalid-file-start-position':11
        , 'invalid-operator-name':12
        , 'invalid-parameter-datatype':13
        , 'invalid-time-stamp':14
        , 'key-generation-error':15
        , 'missing-required-parameter':16
        , 'no-objects-of-specified-type':17
        , 'no-space-for-object':18
        , 'no-space-to-add-list-element':19
        , 'no-space-to-write-property':20
        , 'no-vt-sessions-available':21
        , 'object-deletion-not-premitted':23
        , 'object-identifier-already-exists':24
        , 'operational-problem':25
        , 'optional-functionality-not-supported':45
        , 'password-failure':26
        , 'property-is-not-a-list':22
        , 'property-is-not-an-array':50
        , 'read-access-denied':27
        , 'security-not-supported':28
        , 'service-request-denied':29
        , 'timeout':30
        , 'unknown-object':31
        , 'unknown-property':32
        , 'unknown-vt-class':34
        , 'unknown-vt-session':35
        , 'unsupported-object-type':36
        , 'value-out-of-range':37
        , 'vt-session-already-closed':38
        , 'vt-session-termination-failure':39
        , 'write-access-denied':40
        , 'cov-subscription-failed':43
        , 'not-cov-property':44
        }

class EventState(Enumerated):
    enumerations = \
        { 'normal':0
        , 'fault':1
        , 'offnormal':2
        , 'high-limit':3
        , 'low-limit':4
        , 'life-safety-alarm':5
        }

class EventType(Enumerated):
    enumerations = \
        { 'change-of-bitstring':0
        , 'change-of-state':1
        , 'change-of-value':2
        , 'command-failure':3
        , 'floating-limit':4
        , 'out-of-range':5
        , 'complex-event-type':6
        , 'deprecated(7)':7
        , 'change-of-life-safety':8
        , 'extended':9
        , 'buffer-ready':10
        , 'unsigned-range':11
        }

class NotifyType(Enumerated):
    enumerations = \
        { 'alarm':0
        , 'event':1
        , 'ack-notification':2
        }

class ObjectTypesSupported(BitString):
    bitNames = \
        { 'analog-input':0
        , 'analog-output':1
        , 'analog-value':2
        , 'binary-input':3
        , 'binary-output':4
        , 'binary-value':5
        , 'calendar':6
        , 'command':7
        , 'device':8
        , 'event-enrollment':9
        , 'file':10
        , 'group':11
        , 'loop':12
        , 'multi-state-input':13
        , 'multi-state-output':14
        , 'notification-class':15
        , 'program':16
        , 'schedule':17
        , 'averaging':18
        , 'multi-state-value':19
        , 'trend-log':20
        , 'life-safety-point':21
        , 'life-safety-zone':22
        , 'accumulator':23
        , 'pulse-converter':24
        }
    bitLen = 25

class PropertyIdentifier(Enumerated):
    enumerations = \
        { 'accepted-modes':175
        , 'acked-transitions':0
        , 'ack-required':1
        , 'action':2
        , 'action-text':3
        , 'active-text':4
        , 'active-vt-sessions':5
        , 'active-cov-subscriptions':152
        , 'adjust-value':176
        , 'alarm-value':6
        , 'alarm-values':7
        , 'all':8
        , 'all-writes-successful':9
        , 'apdu-segment-timeout':10
        , 'apdu-timeout':11
        , 'application-software-version':12
        , 'archive':13
        , 'attempted-samples':124
        , 'auto-slave-discovery':169
        , 'average-value':125
        , 'backup-failure-timeout':153
        , 'bias':14
        , 'buffer-size':126
        , 'change-of-state-count':15
        , 'change-of-state-time':16
        , 'client-cov-increment':127
        , 'configuration-files':154
        , 'controlled-variable-reference':19
        , 'controlled-variable-units':20
        , 'controlled-variable-value':21
        , 'count':177
        , 'count-before-change':178
        , 'count-change-time':179
        , 'cov-increment':22
        , 'cov-period':180
        , 'cov-resubscription-interval':128
        , 'database-revision':155
        , 'date-list':23
        , 'daylight-savings-status':24
        , 'deadband':25
        , 'derivative-constant':26
        , 'derivative-constant-units':27
        , 'description':28
        , 'description-of-halt':29
        , 'device-address-binding':30
        , 'device-type':31
        , 'direct-reading':156
        , 'effective-period':32
        , 'elapsed-active-time':33
        , 'error-limit':34
        , 'event-enable':35
        , 'event-time-stamps':130
        , 'event-type':37
        , 'event-parameters':83
        , 'exception-schedule':38
        , 'fault-values':39
        , 'feedback-value':40
        , 'file-access-method':41
        , 'file-size':42
        , 'file-type':43
        , 'firmware-revision':44
        , 'high-limit':45
        , 'inactive-text':46
        , 'in-process':47
        , 'input-reference':181
        , 'instance-of':48
        , 'integral-constant':49
        , 'integral-constant-units':50
        , 'last-notify-record':173
        , 'last-restore-time':157
        , 'life-safety-alarm-values':166
        , 'limit-enable':52
        , 'limit-monitoring-interval':182
        , 'list-of-group-members':53
        , 'list-of-object-property-references':54
        , 'list-of-session-keys':55
        , 'local-date':56
        , 'local-time':57
        , 'location':58
        , 'log-buffer':131
        , 'log-device-object-property':132
        , 'log-enable':133
        , 'log-interval':134
        , 'logging-object':183
        , 'logging-record':184
        , 'low-limit':59
        , 'maintenance-required':158
        , 'manipulated-variable-reference':60
        , 'manual-slave-address-binding':170
        , 'maximum-output':61
        , 'maximum-value':135
        , 'maximum-value-timestamp':149
        , 'max-apdu-length-accepted':62
        , 'max-info-frames':63
        , 'max-master':64
        , 'max-pres-value':65
        , 'max-segments-accepted':167
        , 'member-of':159
        , 'minimum-off-time':66
        , 'minimum-on-time':67
        , 'minimum-output':68
        , 'minimum-value':136
        , 'minimum-value-timestamp':150
        , 'min-pres-value':69
        , 'mode':160
        , 'model-name':70
        , 'notification-class':17
        , 'notify-type':72
        , 'number-of-apdu-retries':73 # number-of-APDU-retries
        , 'number-of-states':74
        , 'object-identifier':75
        , 'object-list':76
        , 'object-name':77
        , 'object-property-reference':78
        , 'object-type':79
        , 'operation-expected':161
        , 'optional':80
        , 'out-of-service':81
        , 'output-units':82
        , 'polarity':84
        , 'prescale':185
        , 'present-value':85
        , 'priority':86
        , 'pulse-rate':186
        , 'priority-array':87
        , 'priority-for-writing':88
        , 'process-identifier':89
        , 'profile-name':168
        , 'program-change':90
        , 'program-location':91
        , 'program-state':92
        , 'proportional-constant':93
        , 'proportional-constant-units':94
        , 'protocol-object-types-supported':96
        , 'protocol-revision':139
        , 'protocol-services-supported':97
        , 'protocol-version':98
        , 'read-only':99
        , 'reason-for-halt':100
        , 'recipient-list':102
        , 'records-since-notification':140
        , 'record-count':141
        , 'reliability':103
        , 'relinquish-default':104
        , 'required':105
        , 'resolution':106
        , 'scale':187
        , 'scale-factor':188
        , 'schedule-default':174
        , 'segmentation-supported':107
        , 'setpoint':108
        , 'setpoint-reference':109
        , 'slave-address-binding':171
        , 'setting':162
        , 'silenced':163
        , 'start-time':142
        , 'state-text':110
        , 'status-flags':111
        , 'stop-time':143
        , 'stop-when-full':144
        , 'system-status':112
        , 'time-delay':113
        , 'time-of-active-time-reset':114
        , 'time-of-state-count-reset':115
        , 'time-synchronization-recipients':116
        , 'total-record-count':145
        , 'tracking-value':164
        , 'units':117
        , 'update-interval':118
        , 'update-time':189
        , 'utc-offset':119
        , 'valid-samples':146
        , 'value-before-change':190
        , 'value-set':191
        , 'value-change-time':192
        , 'variance-value':151
        , 'vendor-identifier':120
        , 'vendor-name':121
        , 'vt-classes-supported':122
        , 'weekly-schedule':123
        , 'window-interval':147
        , 'window-samples':148
        , 'zone-members':165
        }

class Segmentation(Enumerated):
    enumerations = \
        { 'segmented-both':0
        , 'segmented-transmit':1
        , 'segmented-receive':2
        , 'no-segmentation':3
        }

class ServicesSupported(BitString):
    bitNames = \
        { 'acknowledgeAlarm':0
        , 'confirmedCOVNotification':1
        , 'confirmedEventNotification':2
        , 'getAlarmSummary':3
        , 'getEnrollmentSummary':4
        , 'subscribeCOV':5
        , 'atomicReadFile':6
        , 'atomicWriteFile':7
        , 'addListElement':8
        , 'removeListElement':9
        , 'createObject':10
        , 'deleteObject':11
        , 'readProperty':12
        , 'readPropertyConditional':13
        , 'readPropertyMultiple':14
        , 'writeProperty':15
        , 'writePropertyMultiple':16
        , 'deviceCommunicationControl':17
        , 'confirmedPrivateTransfer':18
        , 'confirmedTextMessage':19
        , 'reinitializeDevice':20
        , 'vtOpen':21
        , 'vtClose':22
        , 'vtData':23
        , 'authenticate':24
        , 'requestKey':25
        , 'i-Am':26
        , 'i-Have':27
        , 'unconfirmedCOVNotification':28
        , 'unconfirmedEventNotification':29
        , 'unconfirmedPrivateTransfer':30
        , 'unconfirmedTextMessage':31
        , 'timeSynchronization':32
        , 'who-Has':33
        , 'who-Is':34
        , 'readRange':35
        , 'utcTimeSynchronization':36
        , 'lifeSafetyOperation':37
        , 'subscribeCOVProperty':38
        , 'getEventInformation':39
        }
    bitLen = 40

class StatusFlags(BitString):
    bitNames = \
        { 'in-alarm':0
        , 'fault':1
        , 'overridden':2
        , 'out-of-service':3
        }
    bitLen = 4

class FileAccessMethod(Enumerated):
    enumerations = \
        { 'record-access':0
        , 'stream-access':1
        }

class LifeSafetyMode(Enumerated):
    enumerations = \
        { 'off':0
        , 'on':1
        , 'test':2
        , 'manned':3
        , 'unmanned':4
        , 'armed':5
        , 'disarmed':6
        , 'prearmed':7
        , 'slow':8
        , 'fast':9
        , 'disconnected':10
        , 'enabled':11
        , 'disabled':12
        , 'automatic-release-disabled':13
        , 'default':14
        }

#
#
#

class DaysOfWeek(BitString):
    bitNames = \
        { 'monday':0
        , 'tuesday':1
        , 'wednesday':2
        , 'thursday':3
        , 'friday':4
        , 'saturday':5
        , 'sunday':6
        }
    bitLen = 7

class EventTransitionBits(BitString):
    bitNames = \
        { 'to-offnormal':0
        , 'to-fault':1
        , 'to-normal':2
        }
    bitLen = 3

class LimitEnable(BitString):
    bitNames = \
        { 'lowLimitEnable':0
        , 'highLimitEnable':1
        }
    bitLen = 2

class ObjectTypesSupported(BitString):
    bitNames = \
        { 'analog-input':0
        , 'analog-output':1
        , 'analog-value':2
        , 'binary-input':3
        , 'binary-output':4
        , 'binary-value':5
        , 'calendar':6
        , 'command':7
        , 'device':8
        , 'event-enrollment':9
        , 'file':10
        , 'group':11
        , 'loop':12
        , 'multi-state-input':13
        , 'multi-state-output':14
        , 'notification-class':15
        , 'program':16
        , 'schedule':17
        , 'averaging':18
        , 'multi-state-value':19
        , 'trend-log':20
        , 'life-safety-point':21
        , 'life-safety-zone':22
        , 'accumulator':23
        , 'pulse-converter':24
        }
    bitLen = 25

class ServicesSupported(BitString):
    bitNames = \
        { 'acknowledgeAlarm':0
        , 'confirmedCOVNotification':1
        , 'confirmedEventNotification':2
        , 'getAlarmSummary':3
        , 'getEnrollmentSummary':4
        , 'subscribeCOV':5
        , 'atomicReadFile':6
        , 'atmoicWriteFile':7
        , 'addListElement':8
        , 'removeListElement':9
        , 'createObject':10
        , 'deleteObject':11
        , 'readProperty':12
        , 'readPropertyConditional':13
        , 'readPropertyMultiple':14
        , 'writeProperty':15
        , 'writePropertyMultiple':16
        , 'deviceCommunicationControl':17
        , 'confirmedPrivateTransfer':18
        , 'confirmedTextMessage':19
        , 'reinitializeDevice':20
        , 'vtOpen':21
        , 'vtClose':22
        , 'vtData':23
        , 'authenticate':24
        , 'requestKey':25
        , 'i-Am':26
        , 'i-Have':27
        , 'unconfirmedCOVNotification':28
        , 'unconfirmedEventNotification':29
        , 'unconfirmedPrivateTransfer':30
        , 'unconfirmedTextMessage':31
        , 'timeSynchronization':32
        , 'who-Has':33
        , 'who-Is':34
        , 'readRange':35
        , 'utcTimeSynchronization':36
        , 'lifeSafetyOperation':37
        , 'subscribeCOVProperty':38
        , 'getEventInformation':39
        }
    bitLen = 40

#
#
#

class BACnetAddress(Sequence):
    sequenceElements = \
        [ Element('networkNumber', Unsigned)
        , Element('macAddress', OctetString)
        ]

class AddressBinding(Sequence):
    sequenceElements = \
        [ Element('deviceObjectIdentifier', ObjectIdentifier)
        , Element('deviceAddress', BACnetAddress)
        ]

#
#
#

class Error(Sequence):
    sequenceElements = \
        [ Element('errorClass', ErrorClass)
        , Element('errorCode', ErrorCode)
        ]

class ReadPropertyRequest(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

class ReadPropertyACK(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('propertyValue', Any, 3)
        ]

class WhoIsRequest(Sequence):
    sequenceElements = \
        [ Element('deviceInstanceRangeLowLimit', Unsigned, 0, True)
        , Element('deviceInstanceRangeHighLimit', Unsigned, 1, True)
        ]

class WhoHasLimits(Sequence):
    sequenceElements = \
        [ Element('deviceInstanceRangeLowLimit', Unsigned, 0)
        , Element('deviceInstanceRangeHighLimit', Unsigned, 1)
        ]

class WhoHasObject(Choice):
    choiceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 2)
        , Element('objectName', CharacterString, 3)
        ]

class WhoHasRequest(Sequence):
    sequenceElements = \
        [ Element('limits', WhoHasLimits, None, True)
        , Element('object', WhoHasObject)
        ]

class IAmRequest(Sequence):
    sequenceElements = \
        [ Element('iAmDeviceIdentifier', ObjectIdentifier)
        , Element('maxAPDULengthAccepted', Unsigned)
        , Element('segmentationSupported', Segmentation)
        , Element('vendorID', Unsigned)
        ]

class IHaveRequest(Sequence):
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier)
        , Element('objectIdentifier', ObjectIdentifier)
        , Element('objectName', CharacterString)
        ]

class DateTime(Sequence):
    sequenceElements = \
        [ Element('date', Date)
        , Element('time', Time)
        ]

class TimeStamp(Choice):
    choiceElements = \
        [ Element('time', Time, 0)
        , Element('sequenceNumber', Unsigned, 1)
        , Element('dateTime', DateTime, 2)
        ]

class NotificationChangeOfBitstring(Sequence):
    sequenceElements = \
        [ Element('referencedBitstring', BitString, 0)
        , Element('statusFlags', StatusFlags, 1)
        ]

class PropertyStates(Any): pass

class NotificationChangeOfState(Any): pass
class NotificationChangeOfValue(Any): pass
class NotificationCommandFailure(Any): pass
class NotificationFloatingLimit(Any): pass
class NotificationOutOfRange(Any): pass
class NotificationComplexEventType(Any): pass
class NotificationChangeOfLifeSafety(Any): pass
class NotificationExtended(Any): pass
class NotificationBufferReady(Any): pass
class NotificationUnsignedRange(Any): pass

class NotificationParameters(Choice):
    choiceElements = \
        [ Element('changeOfBitstring', NotificationChangeOfBitstring, 0)
        , Element('changeOfState', NotificationChangeOfState, 1)
        , Element('changeOfValue', NotificationChangeOfValue, 2)
        , Element('commandFailure', NotificationCommandFailure, 3)
        , Element('floatingLimit', NotificationFloatingLimit, 4)
        , Element('outOfRange', NotificationOutOfRange, 5)
        , Element('complexEventType', NotificationComplexEventType, 6)
        , Element('changeOfLifeSafety', NotificationChangeOfLifeSafety, 8)
        , Element('extended', NotificationExtended, 9)
        , Element('bufferReady', NotificationBufferReady, 10)
        , Element('unsignedRange', NotificationUnsignedRange, 11)
        ]

class ConfirmedEventNotificationRequest(Sequence):
    sequenceElements = \
        [ Element('processIdentifier', Unsigned, 0)
        , Element('initiatingDeviceIdentifier', ObjectIdentifier, 1)
        , Element('eventObjectIdentifier', ObjectIdentifier, 2)
        , Element('timeStamp', TimeStamp, 3)
        , Element('notificationClass', Unsigned, 4)
        , Element('priority', Unsigned, 5)
        , Element('eventType', EventType, 6)
        , Element('messageText', CharacterString, 7, True)
        , Element('notifyType', NotifyType, 8)
        , Element('ackRequired', Boolean, 9, True)
        , Element('fromState', EventState, 10, True)
        , Element('toState', EventState, 11)
        , Element('eventValues', NotificationParameters, 12, True)
        ]

class UnconfirmedEventNotificationRequest(Sequence):
    sequenceElements = ConfirmedEventNotificationRequest.sequenceElements

class PropertyValue(Sequence):
    sequenceElements = \
        [ Element('propertyIdentifier', PropertyIdentifier, 0)
        , Element('propertyArrayIndex', Unsigned, 1, True)
        , Element('value', Any, 2)
        , Element('priority', Unsigned, 3, True)
        ]

class UnconfirmedCOVNotificationRequest(Sequence):
    sequenceElements = \
        [ Element('subscriberProcessIdentifier', Unsigned, 0)
        , Element('initiatingDeviceIdentifier', ObjectIdentifier, 1)
        , Element('monitoredObjectIdentifier', ObjectIdentifier, 2)
        , Element('timeRemaining', Unsigned, 3)
        , Element('listOfValues', SequenceOf(PropertyValue), 4)
