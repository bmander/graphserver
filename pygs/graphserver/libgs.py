from ctypes import cdll, PyDLL
from ctypes import c_int, c_long, c_float, c_size_t, c_char_p, c_double, c_void_p, py_object, c_ulong
from ctypes import c_int8, c_int16, c_int32, c_int64, sizeof
from ctypes import POINTER

import os
import sys

# if this thing is not installed, use so in source tree lib directory
#if not CURRENTLY_INSTALLED
libgs = PyDLL( os.path.join( os.path.dirname(os.path.abspath(__file__)) + "/../../core", "libgraphserver.so" ) )

# if we are installed, use so in standard directory
#TODO look up location of standard library directory in some standard way

if not libgs:
    raise ImportError("unable to find libgraphserver shared library")

class LGSTypes:
    ServiceId = c_int
    EdgePayload = c_void_p
    State = c_void_p
    WalkOptions = c_void_p
    Vertex = c_void_p
    Edge = c_void_p
    ListNode = c_void_p
    Graph = c_void_p
    Path = c_void_p
    Vector = c_void_p
    SPTVertex = c_void_p
    ShortestPathTree = c_void_p
    ServicePeriod = c_void_p
    ServiceCalendar = c_void_p
    Timezone = c_void_p
    TimezonePeriod = c_void_p
    Link = c_void_p
    Street = c_void_p
    Egress = c_void_p
    Wait = c_void_p
    ElapseTime = c_void_p
    Headway = c_void_p
    TripBoard = c_void_p
    HeadwayBoard = c_void_p
    HeadwayAlight = c_void_p
    Crossing = c_void_p
    Alight = c_void_p
    PayloadMethods = c_void_p
    CustomPayload = c_void_p
    TripAlight = c_void_p
    CHPath = c_void_p
    CH = c_void_p
    Heap = c_void_p
    HeapNode = c_void_p
    edgepayload_t = c_int
    class ENUM_edgepayload_t:
        PL_STREET = 0
        PL_TRIPHOPSCHED_DEPRIC = 1
        PL_TRIPHOP_DEPRIC = 2
        PL_LINK = 3
        PL_EXTERNVALUE = 4
        PL_NONE = 5
        PL_WAIT = 6
        PL_HEADWAY = 7
        PL_TRIPBOARD = 8
        PL_CROSSING = 9
        PL_ALIGHT = 10
        PL_HEADWAYBOARD = 11
        PL_EGRESS = 12
        PL_HEADWAYALIGHT = 13
        PL_ELAPSE_TIME = 14

LGSTypes.edgepayload_t = {1:c_int8, 2:c_int16, 4:c_int32, 8:c_int64}[c_size_t.in_dll(libgs, "EDGEPAYLOAD_ENUM_SIZE").value]
declarations = [\
    (libgs.epNew, LGSTypes.EdgePayload, [LGSTypes.edgepayload_t, c_void_p]),
    (libgs.epDestroy, None, [LGSTypes.EdgePayload]),
    (libgs.epGetType, LGSTypes.edgepayload_t, [LGSTypes.EdgePayload]),
    (libgs.epGetExternalId, c_long, [LGSTypes.EdgePayload]),
    (libgs.epSetExternalId, None, [LGSTypes.EdgePayload, c_long]),
    (libgs.epWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.epWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.gNew, LGSTypes.Graph, []),
    (libgs.gDestroyBasic, None, [LGSTypes.Graph, c_int]),
    (libgs.gDestroy, None, [LGSTypes.Graph]),
    (libgs.gAddVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (libgs.gRemoveVertex, None, [LGSTypes.Graph, c_char_p, c_int]),
    (libgs.gGetVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (libgs.gAddVertices, None, [LGSTypes.Graph, POINTER(c_char_p), c_int]),
    (libgs.gAddEdge, LGSTypes.Edge, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (libgs.gGetVertexByIndex, LGSTypes.Vertex, [LGSTypes.Graph, c_long]),
    (libgs.gShortestPathTree, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (libgs.gShortestPathTreeRetro, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (libgs.gShortestPath, LGSTypes.State, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, c_int, POINTER(c_long), LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (libgs.gSize, c_long, [LGSTypes.Graph]),
    (libgs.gSetVertexEnabled, None, [LGSTypes.Graph, c_char_p, c_int]),
    (libgs.sptNew, LGSTypes.ShortestPathTree, []),
    (libgs.sptDestroy, None, [LGSTypes.ShortestPathTree]),
    (libgs.sptAddVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, LGSTypes.Vertex, c_int]),
    (libgs.sptRemoveVertex, None, [LGSTypes.ShortestPathTree, c_char_p]),
    (libgs.sptGetVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, c_char_p]),
    (libgs.sptSetParent, LGSTypes.Edge, [LGSTypes.ShortestPathTree, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (libgs.sptGetVertexByIndex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, c_long]),
    (libgs.sptSize, c_long, [LGSTypes.ShortestPathTree]),
    (libgs.sptPathRetro, LGSTypes.Path, [LGSTypes.Graph, c_char_p]),
    (libgs.vNew, LGSTypes.Vertex, [c_char_p]),
    (libgs.vDestroy, None, [LGSTypes.Vertex, c_int]),
    (libgs.vGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (libgs.vGetIncomingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (libgs.vRemoveOutEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (libgs.vRemoveInEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (libgs.vGetLabel, c_char_p, [LGSTypes.Vertex]),
    (libgs.vDegreeOut, c_int, [LGSTypes.Vertex]),
    (libgs.vDegreeIn, c_int, [LGSTypes.Vertex]),
    (libgs.sptvNew, LGSTypes.SPTVertex, [LGSTypes.Vertex, c_int]),
    (libgs.sptvDestroy, None, [LGSTypes.SPTVertex]),
    (libgs.sptvSetParent, LGSTypes.Edge, [LGSTypes.SPTVertex, LGSTypes.SPTVertex, LGSTypes.EdgePayload]),
    (libgs.sptvGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.SPTVertex]),
    (libgs.sptvRemoveOutEdgeRef, None, [LGSTypes.SPTVertex, LGSTypes.Edge]),
    (libgs.sptvDegreeOut, c_int, [LGSTypes.SPTVertex]),
    (libgs.sptvState, LGSTypes.State, [LGSTypes.SPTVertex]),
    (libgs.sptvHop, c_int, [LGSTypes.SPTVertex]),
    (libgs.sptvGetParent, c_ulong, [LGSTypes.SPTVertex]),
    (libgs.sptvMirror, LGSTypes.Vertex, [LGSTypes.SPTVertex]),
    (libgs.eNew, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (libgs.eDestroy, None, [LGSTypes.Edge, c_int]),
    (libgs.eWalk, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.eWalkBack, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.eGetFrom, c_long, [LGSTypes.Edge]),
    (libgs.eGetTo, c_long, [LGSTypes.Edge]),
    (libgs.eGetPayload, LGSTypes.EdgePayload, [LGSTypes.Edge]),
    (libgs.eGetEnabled, c_int, [LGSTypes.Edge]),
    (libgs.eSetEnabled, None, [LGSTypes.Edge, c_int]),
    (libgs.heapNew, LGSTypes.Heap, [c_int]),
    (libgs.heapDestroy, None, [LGSTypes.Heap]),
    (libgs.heapInsert, None, [LGSTypes.Heap, c_void_p, c_long]),
    (libgs.heapEmpty, c_int, [LGSTypes.Heap]),
    (libgs.heapMin, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (libgs.heapPop, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (libgs.liNew, LGSTypes.ListNode, [LGSTypes.Edge]),
    (libgs.liInsertAfter, None, [LGSTypes.ListNode, LGSTypes.ListNode]),
    (libgs.liRemoveAfter, None, [LGSTypes.ListNode]),
    (libgs.liRemoveRef, None, [LGSTypes.ListNode, LGSTypes.Edge]),
    (libgs.liGetData, c_ulong, [LGSTypes.ListNode]),
    (libgs.liGetNext, LGSTypes.ListNode, [LGSTypes.ListNode]),
    (libgs.pathNew, LGSTypes.Path, [LGSTypes.SPTVertex, c_int, c_int]),
    (libgs.pathDestroy, None, [LGSTypes.Path]),
    (libgs.pathGetVertex, LGSTypes.SPTVertex, [LGSTypes.Path, c_int]),
    (libgs.pathGetEdge, LGSTypes.Edge, [LGSTypes.Path, c_int]),
    (libgs.pathAddSegment, None, [LGSTypes.Path, LGSTypes.SPTVertex, LGSTypes.Edge]),
    (libgs.scNew, LGSTypes.ServiceCalendar, []),
    (libgs.scAddServiceId, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (libgs.scGetServiceIdString, c_char_p, [LGSTypes.ServiceCalendar, c_int]),
    (libgs.scGetServiceIdInt, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (libgs.scAddPeriod, None, [LGSTypes.ServiceCalendar, LGSTypes.ServicePeriod]),
    (libgs.scPeriodOfOrAfter, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (libgs.scPeriodOfOrBefore, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (libgs.scHead, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar]),
    (libgs.scDestroy, None, [LGSTypes.ServiceCalendar]),
    (libgs.spNew, LGSTypes.ServicePeriod, [c_long, c_long, c_int, POINTER(LGSTypes.ServiceId)]),
    (libgs.spDestroyPeriod, None, [LGSTypes.ServicePeriod]),
    (libgs.spPeriodHasServiceId, c_int, [LGSTypes.ServicePeriod, LGSTypes.ServiceId]),
    (libgs.spRewind, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (libgs.spFastForward, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (libgs.spPrint, None, [LGSTypes.ServicePeriod]),
    (libgs.spPrintPeriod, None, [LGSTypes.ServicePeriod]),
    (libgs.spNormalizeTime, c_long, [LGSTypes.ServicePeriod, c_int, c_long]),
    (libgs.spBeginTime, c_long, [LGSTypes.ServicePeriod]),
    (libgs.spEndTime, c_long, [LGSTypes.ServicePeriod]),
    (libgs.spServiceIds, POINTER(LGSTypes.ServiceId), [LGSTypes.ServicePeriod, POINTER(c_int)]),
    (libgs.spNextPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (libgs.spPreviousPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (libgs.spDatumMidnight, c_long, [LGSTypes.ServicePeriod, c_int]),
    (libgs.stateNew, LGSTypes.State, [c_int, c_long]),
    (libgs.stateDestroy, None, [LGSTypes.State]),
    (libgs.stateDup, LGSTypes.State, [LGSTypes.State]),
    (libgs.stateGetTime, c_long, [LGSTypes.State]),
    (libgs.stateGetWeight, c_long, [LGSTypes.State]),
    (libgs.stateGetDistWalked, c_double, [LGSTypes.State]),
    (libgs.stateGetNumTransfers, c_int, [LGSTypes.State]),
    (libgs.stateGetPrevEdge, LGSTypes.EdgePayload, [LGSTypes.State]),
    (libgs.stateGetTripId, c_char_p, [LGSTypes.State]),
    (libgs.stateGetStopSequence, c_int, [LGSTypes.State]),
    (libgs.stateGetNumAgencies, c_int, [LGSTypes.State]),
    (libgs.stateServicePeriod, LGSTypes.ServicePeriod, [LGSTypes.State, c_int]),
    (libgs.stateSetServicePeriod, None, [LGSTypes.State, c_int, LGSTypes.ServicePeriod]),
    (libgs.stateSetTime, None, [LGSTypes.State, c_long]),
    (libgs.stateSetWeight, None, [LGSTypes.State, c_long]),
    (libgs.stateSetDistWalked, None, [LGSTypes.State, c_double]),
    (libgs.stateSetNumTransfers, None, [LGSTypes.State, c_int]),
    (libgs.stateDangerousSetTripId, None, [LGSTypes.State, c_char_p]),
    (libgs.stateSetPrevEdge, None, [LGSTypes.State, LGSTypes.EdgePayload]),
    (libgs.tzNew, LGSTypes.Timezone, []),
    (libgs.tzAddPeriod, None, [LGSTypes.Timezone, LGSTypes.TimezonePeriod]),
    (libgs.tzPeriodOf, LGSTypes.TimezonePeriod, [LGSTypes.Timezone, c_long]),
    (libgs.tzUtcOffset, c_int, [LGSTypes.Timezone, c_long]),
    (libgs.tzTimeSinceMidnight, c_int, [LGSTypes.Timezone, c_long]),
    (libgs.tzHead, LGSTypes.TimezonePeriod, [LGSTypes.Timezone]),
    (libgs.tzDestroy, None, [LGSTypes.Timezone]),
    (libgs.tzpNew, LGSTypes.TimezonePeriod, [c_long, c_long, c_int]),
    (libgs.tzpDestroy, None, [LGSTypes.TimezonePeriod]),
    (libgs.tzpUtcOffset, c_int, [LGSTypes.TimezonePeriod]),
    (libgs.tzpTimeSinceMidnight, c_int, [LGSTypes.TimezonePeriod, c_long]),
    (libgs.tzpBeginTime, c_long, [LGSTypes.TimezonePeriod]),
    (libgs.tzpEndTime, c_long, [LGSTypes.TimezonePeriod]),
    (libgs.tzpNextPeriod, LGSTypes.TimezonePeriod, [LGSTypes.TimezonePeriod]),
    (libgs.vecNew, LGSTypes.Vector, [c_int, c_int]),
    (libgs.vecDestroy, None, [LGSTypes.Vector]),
    (libgs.vecAdd, None, [LGSTypes.Vector, c_void_p]),
    (libgs.vecGet, c_void_p, [LGSTypes.Vector, c_int]),
    (libgs.vecExpand, None, [LGSTypes.Vector, c_int]),
    (libgs.woNew, LGSTypes.WalkOptions, []),
    (libgs.woDestroy, None, [LGSTypes.WalkOptions]),
    (libgs.woGetTransferPenalty, c_int, [LGSTypes.WalkOptions]),
    (libgs.woSetTransferPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (libgs.woGetWalkingSpeed, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetWalkingSpeed, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetWalkingReluctance, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetWalkingReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (libgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (libgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (libgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (libgs.woGetUphillSlowness, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetUphillSlowness, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetDownhillFastness, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetDownhillFastness, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetHillReluctance, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetHillReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (libgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (libgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (libgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (libgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (libgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (libgs.crNew, LGSTypes.Crossing, []),
    (libgs.crDestroy, None, [LGSTypes.Crossing]),
    (libgs.crAddCrossingTime, None, [LGSTypes.Crossing, c_char_p, c_int]),
    (libgs.crGetCrossingTime, c_int, [LGSTypes.Crossing, c_char_p]),
    (libgs.crGetCrossingTimeTripIdByIndex, c_char_p, [LGSTypes.Crossing, c_int]),
    (libgs.crGetCrossingTimeByIndex, c_int, [LGSTypes.Crossing, c_int]),
    (libgs.crGetSize, c_int, [LGSTypes.Crossing]),
    (libgs.crWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.crWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
#   For reasons presently opaque to me, argtypes for this function are set to None to make this work.
#   Old comment says: args are not specified to allow for None - therefore, setting to none
#    (libgs.defineCustomPayloadType, LGSTypes.PayloadMethods, [CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions)]),
    (libgs.defineCustomPayloadType, LGSTypes.PayloadMethods, None),
    (libgs.undefineCustomPayloadType, None, [LGSTypes.PayloadMethods]),
    (libgs.cpNew, LGSTypes.CustomPayload, [py_object, LGSTypes.PayloadMethods]),
    (libgs.cpDestroy, None, [LGSTypes.CustomPayload]),
    (libgs.cpSoul, py_object, [LGSTypes.CustomPayload]),
    (libgs.cpMethods, LGSTypes.PayloadMethods, [LGSTypes.CustomPayload]),
    (libgs.cpWalk, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.cpWalkBack, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.egressNew, LGSTypes.Egress, [c_char_p, c_double]),
    (libgs.egressDestroy, None, [LGSTypes.Egress]),
    (libgs.egressWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.egressWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.egressGetName, c_char_p, [LGSTypes.Egress]),
    (libgs.egressGetLength, c_double, [LGSTypes.Egress]),
    (libgs.elapse_time_and_service_period_forward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (libgs.elapse_time_and_service_period_backward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (libgs.elapseTimeNew, LGSTypes.ElapseTime, [c_long]),
    (libgs.elapseTimeDestroy, None, [LGSTypes.ElapseTime]),
    (libgs.elapseTimeWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.elapseTimeWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.elapseTimeGetSeconds, c_long, [LGSTypes.ElapseTime]),
    (libgs.headwayNew, LGSTypes.Headway, [c_int, c_int, c_int, c_int, c_char_p, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, LGSTypes.ServiceId]),
    (libgs.headwayDestroy, None, [LGSTypes.Headway]),
    (libgs.headwayWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.headwayWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.headwayBeginTime, c_int, [LGSTypes.Headway]),
    (libgs.headwayEndTime, c_int, [LGSTypes.Headway]),
    (libgs.headwayWaitPeriod, c_int, [LGSTypes.Headway]),
    (libgs.headwayTransit, c_int, [LGSTypes.Headway]),
    (libgs.headwayTripId, c_char_p, [LGSTypes.Headway]),
    (libgs.headwayCalendar, LGSTypes.ServiceCalendar, [LGSTypes.Headway]),
    (libgs.headwayTimezone, LGSTypes.Timezone, [LGSTypes.Headway]),
    (libgs.headwayAgency, c_int, [LGSTypes.Headway]),
    (libgs.headwayServiceId, LGSTypes.ServiceId, [LGSTypes.Headway]),
    (libgs.haNew, LGSTypes.HeadwayAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (libgs.haDestroy, None, [LGSTypes.HeadwayAlight]),
    (libgs.haGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayAlight]),
    (libgs.haGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayAlight]),
    (libgs.haGetAgency, c_int, [LGSTypes.HeadwayAlight]),
    (libgs.haGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayAlight]),
    (libgs.haGetTripId, c_char_p, [LGSTypes.HeadwayAlight]),
    (libgs.haGetStartTime, c_int, [LGSTypes.HeadwayAlight]),
    (libgs.haGetEndTime, c_int, [LGSTypes.HeadwayAlight]),
    (libgs.haGetHeadwaySecs, c_int, [LGSTypes.HeadwayAlight]),
    (libgs.haWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.haWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.hbNew, LGSTypes.HeadwayBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (libgs.hbDestroy, None, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetAgency, c_int, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetTripId, c_char_p, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetStartTime, c_int, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetEndTime, c_int, [LGSTypes.HeadwayBoard]),
    (libgs.hbGetHeadwaySecs, c_int, [LGSTypes.HeadwayBoard]),
    (libgs.hbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.hbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.linkNew, LGSTypes.Link, []),
    (libgs.linkDestroy, None, [LGSTypes.Link]),
    (libgs.linkWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.linkWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.streetNew, LGSTypes.Street, [c_char_p, c_double, c_int]),
    (libgs.streetNewElev, LGSTypes.Street, [c_char_p, c_double, c_float, c_float, c_int]),
    (libgs.streetDestroy, None, [LGSTypes.Street]),
    (libgs.streetWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.streetWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.streetGetName, c_char_p, [LGSTypes.Street]),
    (libgs.streetGetLength, c_double, [LGSTypes.Street]),
    (libgs.streetGetRise, c_float, [LGSTypes.Street]),
    (libgs.streetGetFall, c_float, [LGSTypes.Street]),
    (libgs.streetSetRise, None, [LGSTypes.Street, c_float]),
    (libgs.streetSetFall, None, [LGSTypes.Street, c_float]),
    (libgs.streetGetWay, c_long, [LGSTypes.Street]),
    (libgs.streetSetWay, None, [LGSTypes.Street, c_long]),
    (libgs.streetGetSlog, c_float, [LGSTypes.Street]),
    (libgs.streetSetSlog, None, [LGSTypes.Street, c_float]),
    (libgs.streetGetReverseOfSource, c_int, [LGSTypes.Street]),
    (libgs.alNew, LGSTypes.TripAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (libgs.alDestroy, None, [LGSTypes.TripAlight]),
    (libgs.alGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripAlight]),
    (libgs.alGetTimezone, LGSTypes.Timezone, [LGSTypes.TripAlight]),
    (libgs.alGetAgency, c_int, [LGSTypes.TripAlight]),
    (libgs.alGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripAlight]),
    (libgs.alGetNumAlightings, c_int, [LGSTypes.TripAlight]),
    (libgs.alAddAlighting, None, [LGSTypes.TripAlight, c_char_p, c_int, c_int]),
    (libgs.alGetAlightingTripId, c_char_p, [LGSTypes.TripAlight, c_int]),
    (libgs.alGetAlightingArrival, c_int, [LGSTypes.TripAlight, c_int]),
    (libgs.alGetAlightingStopSequence, c_int, [LGSTypes.TripAlight, c_int]),
    (libgs.alSearchAlightingsList, c_int, [LGSTypes.TripAlight, c_int]),
    (libgs.alGetLastAlightingIndex, c_int, [LGSTypes.TripAlight, c_int]),
    (libgs.alGetOverage, c_int, [LGSTypes.TripAlight]),
    (libgs.alGetAlightingIndexByTripId, c_int, [LGSTypes.TripAlight, c_char_p]),
    (libgs.alWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.alWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.tbNew, LGSTypes.TripBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (libgs.tbDestroy, None, [LGSTypes.TripBoard]),
    (libgs.tbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripBoard]),
    (libgs.tbGetTimezone, LGSTypes.Timezone, [LGSTypes.TripBoard]),
    (libgs.tbGetAgency, c_int, [LGSTypes.TripBoard]),
    (libgs.tbGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripBoard]),
    (libgs.tbGetNumBoardings, c_int, [LGSTypes.TripBoard]),
    (libgs.tbAddBoarding, None, [LGSTypes.TripBoard, c_char_p, c_int, c_int]),
    (libgs.tbGetBoardingTripId, c_char_p, [LGSTypes.TripBoard, c_int]),
    (libgs.tbGetBoardingDepart, c_int, [LGSTypes.TripBoard, c_int]),
    (libgs.tbGetBoardingStopSequence, c_int, [LGSTypes.TripBoard, c_int]),
    (libgs.tbSearchBoardingsList, c_int, [LGSTypes.TripBoard, c_int]),
    (libgs.tbGetNextBoardingIndex, c_int, [LGSTypes.TripBoard, c_int]),
    (libgs.tbGetOverage, c_int, [LGSTypes.TripBoard]),
    (libgs.tbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.tbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.tbGetBoardingIndexByTripId, c_int, [LGSTypes.TripBoard, c_char_p]),
    (libgs.waitNew, LGSTypes.Wait, [c_long, LGSTypes.Timezone]),
    (libgs.waitDestroy, None, [LGSTypes.Wait]),
    (libgs.waitWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.waitWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (libgs.waitGetEnd, c_long, [LGSTypes.Wait]),
    (libgs.waitGetTimezone, LGSTypes.Timezone, [LGSTypes.Wait])
]

for fun, restype, argtypes in declarations:
    fun.argtypes = argtypes
    fun.restype = restype
    fun.safe = True

class SafeWrapper(object):
    def __init__(self, lib, name):
        self.lib = lib
        self.name = name

    def __getattr__(self, attr):
        v = getattr(self.lib, attr)
        if not getattr(v, 'safe', False):
            raise Exception("Using unsafe method %s - you must declare the ctypes restype and argtypes in gsdll.py to ensure 64-bit compatibility." % attr)
        return SafeWrapper(v, name=self.name + "." + attr)

    def __call__(self, *args):
        """Very useful for debugging bogus calls to the DLL which result in segfaluts."""
        sys.stderr.write( ">%s %s(%s)\n" % (self.lib.restype and self.lib.restype.__name__ or None, self.name, ",".join(map(repr, args))))
        sys.stderr.flush()

        return self.lib(*args)

if 'GS_VERBOSE_CTYPES' in os.environ:
    libgs = SafeWrapper(libgs,'lgs')
