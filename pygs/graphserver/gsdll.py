import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_float, c_size_t, c_char_p, c_double, c_void_p, py_object
from ctypes import c_int8, c_int16, c_int32, c_int64, sizeof
from ctypes import Structure, pointer, cast, POINTER, addressof
from ctypes.util import find_library

import os
import sys

# The libgraphserver.so object:
lgs = None

# Try loading from the source tree. If that doesn't work, fall back to the installed location.
_dlldirs = [os.path.dirname(os.path.abspath(__file__)),
            os.path.dirname(os.path.abspath(__file__)) + '/../../core',
            '/usr/lib',
            '/usr/local/lib']

for _dlldir in _dlldirs:
    _dllpath = os.path.join(_dlldir, 'libgraphserver.so')
    if os.path.exists(_dllpath):
        lgs = PyDLL( _dllpath )
        break

if not lgs:
    raise ImportError("unable to find libgraphserver shared library in the usual locations: %s" % "\n".join(_dlldirs))

libc = cdll.LoadLibrary(find_library('c'))

class _EmptyClass(object):
    pass

def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = _EmptyClass()
    ret.__class__ = cls
    return ret

def cleanup():
    """ Perform any necessary cleanup when the library is unloaded."""
    pass

atexit.register(cleanup)

class CShadow(object):
    """ Base class for all objects that shadow a C structure."""
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
        
    def check_destroyed(self):
        if self.soul is None:
            raise Exception("You are trying to use an instance that has been destroyed")

def _declare(fun, restype, argtypes):
    fun.argtypes = argtypes
    fun.restype = restype
    fun.safe = True

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
    Combination = c_void_p
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
        PL_COMBINATION = 15

LGSTypes.edgepayload_t = {1:c_int8, 2:c_int16, 4:c_int32, 8:c_int64}[c_size_t.in_dll(lgs, "EDGEPAYLOAD_ENUM_SIZE").value]
declarations = [\
    (lgs.chpNew, LGSTypes.CHPath, [c_int, c_long]),
    (lgs.chpLength, c_int, [LGSTypes.CHPath]),
    (lgs.chpCombine, LGSTypes.CHPath, [LGSTypes.CHPath, LGSTypes.CHPath]),
    (lgs.chpDestroy, None, [LGSTypes.CHPath]),
    (lgs.dist, LGSTypes.CHPath, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.WalkOptions, c_int, c_int]),
    (lgs.get_shortcuts, POINTER(LGSTypes.CHPath), [LGSTypes.Graph, LGSTypes.Vertex, LGSTypes.WalkOptions, c_int, POINTER(c_int)]),
    (lgs.init_priority_queue, LGSTypes.Heap, [LGSTypes.Graph, LGSTypes.WalkOptions, c_int]),
    (lgs.pqPush, None, [LGSTypes.Heap, LGSTypes.Vertex, c_long]),
    (lgs.pqPop, LGSTypes.Vertex, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.get_contraction_hierarchies, LGSTypes.CH, [LGSTypes.Graph, LGSTypes.WalkOptions, c_int]),
    (lgs.chNew, LGSTypes.CH, []),
    (lgs.chUpGraph, LGSTypes.Graph, [LGSTypes.CH]),
    (lgs.chDownGraph, LGSTypes.Graph, [LGSTypes.CH]),
    (lgs.epNew, LGSTypes.EdgePayload, [LGSTypes.edgepayload_t, c_void_p]),
    (lgs.epDestroy, None, [LGSTypes.EdgePayload]),
    (lgs.epGetType, LGSTypes.edgepayload_t, [LGSTypes.EdgePayload]),
    (lgs.epGetExternalId, c_long, [LGSTypes.EdgePayload]),
    (lgs.epSetExternalId, None, [LGSTypes.EdgePayload, c_long]),
    (lgs.epWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.epWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.gNew, LGSTypes.Graph, []),
    (lgs.gDestroyBasic, None, [LGSTypes.Graph, c_int]),
    (lgs.gDestroy, None, [LGSTypes.Graph]),
    (lgs.gAddVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (lgs.gRemoveVertex, None, [LGSTypes.Graph, c_char_p, c_int]),
    (lgs.gGetVertex, LGSTypes.Vertex, [LGSTypes.Graph, c_char_p]),
    (lgs.gAddVertices, None, [LGSTypes.Graph, POINTER(c_char_p), c_int]),
    (lgs.gAddEdge, LGSTypes.Edge, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (lgs.gVertices, POINTER(LGSTypes.Vertex), [LGSTypes.Graph, POINTER(c_long)]),
    (lgs.gShortestPathTree, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gShortestPathTreeRetro, LGSTypes.ShortestPathTree, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gShortestPath, LGSTypes.State, [LGSTypes.Graph, c_char_p, c_char_p, LGSTypes.State, c_int, POINTER(c_long), LGSTypes.WalkOptions, c_long, c_int, c_long]),
    (lgs.gSize, c_long, [LGSTypes.Graph]),
    (lgs.gSetVertexEnabled, None, [LGSTypes.Graph, c_char_p, c_int]),
    (lgs.sptNew, LGSTypes.ShortestPathTree, []),
    (lgs.sptDestroy, None, [LGSTypes.ShortestPathTree]),
    (lgs.sptAddVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, LGSTypes.Vertex, c_int]),
    (lgs.sptRemoveVertex, None, [LGSTypes.ShortestPathTree, c_char_p]),
    (lgs.sptGetVertex, LGSTypes.SPTVertex, [LGSTypes.ShortestPathTree, c_char_p]),
    (lgs.sptAddEdge, LGSTypes.Edge, [LGSTypes.ShortestPathTree, c_char_p, c_char_p, LGSTypes.EdgePayload]),
    (lgs.sptVertices, POINTER(LGSTypes.SPTVertex), [LGSTypes.ShortestPathTree, POINTER(c_long)]),
    (lgs.sptSize, c_long, [LGSTypes.ShortestPathTree]),
    (lgs.sptPathRetro, LGSTypes.Path, [LGSTypes.Graph, c_char_p]),
    (lgs.vNew, LGSTypes.Vertex, [c_char_p]),
    (lgs.vDestroy, None, [LGSTypes.Vertex, c_int]),
    (lgs.vLink, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.vSetParent, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.vGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (lgs.vGetIncomingEdgeList, LGSTypes.ListNode, [LGSTypes.Vertex]),
    (lgs.vRemoveOutEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.vRemoveInEdgeRef, None, [LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.vGetLabel, c_char_p, [LGSTypes.Vertex]),
    (lgs.vDegreeOut, c_int, [LGSTypes.Vertex]),
    (lgs.vDegreeIn, c_int, [LGSTypes.Vertex]),
    (lgs.sptvNew, LGSTypes.SPTVertex, [LGSTypes.Vertex, c_int]),
    (lgs.sptvDestroy, None, [LGSTypes.SPTVertex]),
    (lgs.sptvLink, LGSTypes.Edge, [LGSTypes.SPTVertex, LGSTypes.SPTVertex, LGSTypes.EdgePayload]),
    (lgs.sptvSetParent, LGSTypes.Edge, [LGSTypes.SPTVertex, LGSTypes.SPTVertex, LGSTypes.EdgePayload]),
    (lgs.sptvGetOutgoingEdgeList, LGSTypes.ListNode, [LGSTypes.SPTVertex]),
    (lgs.sptvGetIncomingEdgeList, LGSTypes.ListNode, [LGSTypes.SPTVertex]),
    (lgs.sptvRemoveOutEdgeRef, None, [LGSTypes.SPTVertex, LGSTypes.Edge]),
    (lgs.sptvRemoveInEdgeRef, None, [LGSTypes.SPTVertex, LGSTypes.Edge]),
    (lgs.sptvGetLabel, c_char_p, [LGSTypes.SPTVertex]),
    (lgs.sptvDegreeOut, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvDegreeIn, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvState, LGSTypes.State, [LGSTypes.SPTVertex]),
    (lgs.sptvHop, c_int, [LGSTypes.SPTVertex]),
    (lgs.sptvGetParent, LGSTypes.Edge, [LGSTypes.SPTVertex]),
    (lgs.sptvMirror, LGSTypes.Vertex, [LGSTypes.SPTVertex]),
    (lgs.eNew, LGSTypes.Edge, [LGSTypes.Vertex, LGSTypes.Vertex, LGSTypes.EdgePayload]),
    (lgs.eDestroy, None, [LGSTypes.Edge, c_int]),
    (lgs.eWalk, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.eWalkBack, LGSTypes.State, [LGSTypes.Edge, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.eGetFrom, LGSTypes.Vertex, [LGSTypes.Edge]),
    (lgs.eGetTo, LGSTypes.Vertex, [LGSTypes.Edge]),
    (lgs.eGetPayload, LGSTypes.EdgePayload, [LGSTypes.Edge]),
    (lgs.eGetEnabled, c_int, [LGSTypes.Edge]),
    (lgs.eSetEnabled, None, [LGSTypes.Edge, c_int]),
    (lgs.heapNew, LGSTypes.Heap, [c_int]),
    (lgs.heapDestroy, None, [LGSTypes.Heap]),
    (lgs.heapInsert, None, [LGSTypes.Heap, c_void_p, c_long]),
    (lgs.heapEmpty, c_int, [LGSTypes.Heap]),
    (lgs.heapMin, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.heapPop, c_void_p, [LGSTypes.Heap, POINTER(c_long)]),
    (lgs.liNew, LGSTypes.ListNode, [LGSTypes.Edge]),
    (lgs.liInsertAfter, None, [LGSTypes.ListNode, LGSTypes.ListNode]),
    (lgs.liRemoveAfter, None, [LGSTypes.ListNode]),
    (lgs.liRemoveRef, None, [LGSTypes.ListNode, LGSTypes.Edge]),
    (lgs.liGetData, LGSTypes.Edge, [LGSTypes.ListNode]),
    (lgs.liGetNext, LGSTypes.ListNode, [LGSTypes.ListNode]),
    (lgs.pathNew, LGSTypes.Path, [LGSTypes.Vertex, c_int, c_int]),
    (lgs.pathDestroy, None, [LGSTypes.Path]),
    (lgs.pathGetVertex, LGSTypes.Vertex, [LGSTypes.Path, c_int]),
    (lgs.pathGetEdge, LGSTypes.Edge, [LGSTypes.Path, c_int]),
    (lgs.pathAddSegment, None, [LGSTypes.Path, LGSTypes.Vertex, LGSTypes.Edge]),
    (lgs.scNew, LGSTypes.ServiceCalendar, []),
    (lgs.scAddServiceId, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (lgs.scGetServiceIdString, c_char_p, [LGSTypes.ServiceCalendar, c_int]),
    (lgs.scGetServiceIdInt, c_int, [LGSTypes.ServiceCalendar, c_char_p]),
    (lgs.scAddPeriod, None, [LGSTypes.ServiceCalendar, LGSTypes.ServicePeriod]),
    (lgs.scPeriodOfOrAfter, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (lgs.scPeriodOfOrBefore, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar, c_long]),
    (lgs.scHead, LGSTypes.ServicePeriod, [LGSTypes.ServiceCalendar]),
    (lgs.scDestroy, None, [LGSTypes.ServiceCalendar]),
    (lgs.spNew, LGSTypes.ServicePeriod, [c_long, c_long, c_int, POINTER(LGSTypes.ServiceId)]),
    (lgs.spDestroyPeriod, None, [LGSTypes.ServicePeriod]),
    (lgs.spPeriodHasServiceId, c_int, [LGSTypes.ServicePeriod, LGSTypes.ServiceId]),
    (lgs.spRewind, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spFastForward, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spPrint, None, [LGSTypes.ServicePeriod]),
    (lgs.spPrintPeriod, None, [LGSTypes.ServicePeriod]),
    (lgs.spNormalizeTime, c_long, [LGSTypes.ServicePeriod, c_int, c_long]),
    (lgs.spBeginTime, c_long, [LGSTypes.ServicePeriod]),
    (lgs.spEndTime, c_long, [LGSTypes.ServicePeriod]),
    (lgs.spServiceIds, POINTER(LGSTypes.ServiceId), [LGSTypes.ServicePeriod, POINTER(c_int)]),
    (lgs.spNextPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spPreviousPeriod, LGSTypes.ServicePeriod, [LGSTypes.ServicePeriod]),
    (lgs.spDatumMidnight, c_long, [LGSTypes.ServicePeriod, c_int]),
    (lgs.stateNew, LGSTypes.State, [c_int, c_long]),
    (lgs.stateDestroy, None, [LGSTypes.State]),
    (lgs.stateDup, LGSTypes.State, [LGSTypes.State]),
    (lgs.stateGetTime, c_long, [LGSTypes.State]),
    (lgs.stateGetWeight, c_long, [LGSTypes.State]),
    (lgs.stateGetDistWalked, c_double, [LGSTypes.State]),
    (lgs.stateGetNumTransfers, c_int, [LGSTypes.State]),
    (lgs.stateGetPrevEdge, LGSTypes.EdgePayload, [LGSTypes.State]),
    (lgs.stateGetTripId, c_char_p, [LGSTypes.State]),
    (lgs.stateGetStopSequence, c_int, [LGSTypes.State]),
    (lgs.stateGetNumAgencies, c_int, [LGSTypes.State]),
    (lgs.stateServicePeriod, LGSTypes.ServicePeriod, [LGSTypes.State, c_int]),
    (lgs.stateSetServicePeriod, None, [LGSTypes.State, c_int, LGSTypes.ServicePeriod]),
    (lgs.stateSetTime, None, [LGSTypes.State, c_long]),
    (lgs.stateSetWeight, None, [LGSTypes.State, c_long]),
    (lgs.stateSetDistWalked, None, [LGSTypes.State, c_double]),
    (lgs.stateSetNumTransfers, None, [LGSTypes.State, c_int]),
    (lgs.stateDangerousSetTripId, None, [LGSTypes.State, c_char_p]),
    (lgs.stateSetPrevEdge, None, [LGSTypes.State, LGSTypes.EdgePayload]),
    (lgs.tzNew, LGSTypes.Timezone, []),
    (lgs.tzAddPeriod, None, [LGSTypes.Timezone, LGSTypes.TimezonePeriod]),
    (lgs.tzPeriodOf, LGSTypes.TimezonePeriod, [LGSTypes.Timezone, c_long]),
    (lgs.tzUtcOffset, c_int, [LGSTypes.Timezone, c_long]),
    (lgs.tzTimeSinceMidnight, c_int, [LGSTypes.Timezone, c_long]),
    (lgs.tzHead, LGSTypes.TimezonePeriod, [LGSTypes.Timezone]),
    (lgs.tzDestroy, None, [LGSTypes.Timezone]),
    (lgs.tzpNew, LGSTypes.TimezonePeriod, [c_long, c_long, c_int]),
    (lgs.tzpDestroy, None, [LGSTypes.TimezonePeriod]),
    (lgs.tzpUtcOffset, c_int, [LGSTypes.TimezonePeriod]),
    (lgs.tzpTimeSinceMidnight, c_int, [LGSTypes.TimezonePeriod, c_long]),
    (lgs.tzpBeginTime, c_long, [LGSTypes.TimezonePeriod]),
    (lgs.tzpEndTime, c_long, [LGSTypes.TimezonePeriod]),
    (lgs.tzpNextPeriod, LGSTypes.TimezonePeriod, [LGSTypes.TimezonePeriod]),
    (lgs.vecNew, LGSTypes.Vector, [c_int, c_int]),
    (lgs.vecDestroy, None, [LGSTypes.Vector]),
    (lgs.vecAdd, None, [LGSTypes.Vector, c_void_p]),
    (lgs.vecGet, c_void_p, [LGSTypes.Vector, c_int]),
    (lgs.vecExpand, None, [LGSTypes.Vector, c_int]),
    (lgs.woNew, LGSTypes.WalkOptions, []),
    (lgs.woDestroy, None, [LGSTypes.WalkOptions]),
    (lgs.woGetTransferPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTransferPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingSpeed, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingSpeed, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetWalkingReluctance, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetUphillSlowness, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetUphillSlowness, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetDownhillFastness, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetDownhillFastness, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetHillReluctance, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetHillReluctance, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetMaxWalk, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetMaxWalk, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.woGetWalkingOverage, c_float, [LGSTypes.WalkOptions]),
    (lgs.woSetWalkingOverage, None, [LGSTypes.WalkOptions, c_float]),
    (lgs.woGetTurnPenalty, c_int, [LGSTypes.WalkOptions]),
    (lgs.woSetTurnPenalty, None, [LGSTypes.WalkOptions, c_int]),
    (lgs.comboNew, LGSTypes.Combination, [c_int]),
    (lgs.comboAdd, None, [LGSTypes.Combination, LGSTypes.EdgePayload]),
    (lgs.comboDestroy, None, [LGSTypes.Combination]),
    (lgs.comboWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.comboWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.comboGet, LGSTypes.EdgePayload, [LGSTypes.Combination, c_int]),
    (lgs.comboN, c_int, [LGSTypes.Combination]),
    (lgs.crNew, LGSTypes.Crossing, []),
    (lgs.crDestroy, None, [LGSTypes.Crossing]),
    (lgs.crAddCrossingTime, None, [LGSTypes.Crossing, c_char_p, c_int]),
    (lgs.crGetCrossingTime, c_int, [LGSTypes.Crossing, c_char_p]),
    (lgs.crGetCrossingTimeTripIdByIndex, c_char_p, [LGSTypes.Crossing, c_int]),
    (lgs.crGetCrossingTimeByIndex, c_int, [LGSTypes.Crossing, c_int]),
    (lgs.crGetSize, c_int, [LGSTypes.Crossing]),
    (lgs.crWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.crWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
#   For reasons presently opaque to me, argtypes for this function are set to None to make this work.
#   Old comment says: args are not specified to allow for None - therefore, setting to none
#    (lgs.defineCustomPayloadType, LGSTypes.PayloadMethods, [CFUNCTYPE(c_void_p, c_void_p), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions), CFUNCTYPE(LGSTypes.State, c_void_p, LGSTypes.State, LGSTypes.WalkOptions)]),
    (lgs.defineCustomPayloadType, LGSTypes.PayloadMethods, None),
    (lgs.undefineCustomPayloadType, None, [LGSTypes.PayloadMethods]),
    (lgs.cpNew, LGSTypes.CustomPayload, [py_object, LGSTypes.PayloadMethods]),
    (lgs.cpDestroy, None, [LGSTypes.CustomPayload]),
    (lgs.cpSoul, py_object, [LGSTypes.CustomPayload]),
    (lgs.cpMethods, LGSTypes.PayloadMethods, [LGSTypes.CustomPayload]),
    (lgs.cpWalk, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.cpWalkBack, LGSTypes.State, [LGSTypes.CustomPayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressNew, LGSTypes.Egress, [c_char_p, c_double]),
    (lgs.egressDestroy, None, [LGSTypes.Egress]),
    (lgs.egressWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.egressGetName, c_char_p, [LGSTypes.Egress]),
    (lgs.egressGetLength, c_double, [LGSTypes.Egress]),
    (lgs.elapse_time_and_service_period_forward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (lgs.elapse_time_and_service_period_backward, None, [LGSTypes.State, LGSTypes.State, c_long]),
    (lgs.elapseTimeNew, LGSTypes.ElapseTime, [c_long]),
    (lgs.elapseTimeDestroy, None, [LGSTypes.ElapseTime]),
    (lgs.elapseTimeWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.elapseTimeWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.elapseTimeGetSeconds, c_long, [LGSTypes.ElapseTime]),
    (lgs.headwayNew, LGSTypes.Headway, [c_int, c_int, c_int, c_int, c_char_p, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, LGSTypes.ServiceId]),
    (lgs.headwayDestroy, None, [LGSTypes.Headway]),
    (lgs.headwayWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.headwayWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.headwayBeginTime, c_int, [LGSTypes.Headway]),
    (lgs.headwayEndTime, c_int, [LGSTypes.Headway]),
    (lgs.headwayWaitPeriod, c_int, [LGSTypes.Headway]),
    (lgs.headwayTransit, c_int, [LGSTypes.Headway]),
    (lgs.headwayTripId, c_char_p, [LGSTypes.Headway]),
    (lgs.headwayCalendar, LGSTypes.ServiceCalendar, [LGSTypes.Headway]),
    (lgs.headwayTimezone, LGSTypes.Timezone, [LGSTypes.Headway]),
    (lgs.headwayAgency, c_int, [LGSTypes.Headway]),
    (lgs.headwayServiceId, LGSTypes.ServiceId, [LGSTypes.Headway]),
    (lgs.haNew, LGSTypes.HeadwayAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (lgs.haDestroy, None, [LGSTypes.HeadwayAlight]),
    (lgs.haGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayAlight]),
    (lgs.haGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayAlight]),
    (lgs.haGetAgency, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayAlight]),
    (lgs.haGetTripId, c_char_p, [LGSTypes.HeadwayAlight]),
    (lgs.haGetStartTime, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetEndTime, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haGetHeadwaySecs, c_int, [LGSTypes.HeadwayAlight]),
    (lgs.haWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.haWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.hbNew, LGSTypes.HeadwayBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int, c_char_p, c_int, c_int, c_int]),
    (lgs.hbDestroy, None, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetTimezone, LGSTypes.Timezone, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetAgency, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetServiceId, LGSTypes.ServiceId, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetTripId, c_char_p, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetStartTime, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetEndTime, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbGetHeadwaySecs, c_int, [LGSTypes.HeadwayBoard]),
    (lgs.hbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.hbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkNew, LGSTypes.Link, []),
    (lgs.linkDestroy, None, [LGSTypes.Link]),
    (lgs.linkWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.linkGetName, c_char_p, [LGSTypes.Link]),
    (lgs.streetNew, LGSTypes.Street, [c_char_p, c_double, c_int]),
    (lgs.streetNewElev, LGSTypes.Street, [c_char_p, c_double, c_float, c_float, c_int]),
    (lgs.streetDestroy, None, [LGSTypes.Street]),
    (lgs.streetWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.streetWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.streetGetName, c_char_p, [LGSTypes.Street]),
    (lgs.streetGetLength, c_double, [LGSTypes.Street]),
    (lgs.streetGetRise, c_float, [LGSTypes.Street]),
    (lgs.streetGetFall, c_float, [LGSTypes.Street]),
    (lgs.streetSetRise, None, [LGSTypes.Street, c_float]),
    (lgs.streetSetFall, None, [LGSTypes.Street, c_float]),
    (lgs.streetGetWay, c_long, [LGSTypes.Street]),
    (lgs.streetSetWay, None, [LGSTypes.Street, c_long]),
    (lgs.streetGetSlog, c_float, [LGSTypes.Street]),
    (lgs.streetSetSlog, None, [LGSTypes.Street, c_float]),
    (lgs.streetGetReverseOfSource, c_int, [LGSTypes.Street]),
    (lgs.alNew, LGSTypes.TripAlight, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (lgs.alDestroy, None, [LGSTypes.TripAlight]),
    (lgs.alGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripAlight]),
    (lgs.alGetTimezone, LGSTypes.Timezone, [LGSTypes.TripAlight]),
    (lgs.alGetAgency, c_int, [LGSTypes.TripAlight]),
    (lgs.alGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripAlight]),
    (lgs.alGetNumAlightings, c_int, [LGSTypes.TripAlight]),
    (lgs.alAddAlighting, None, [LGSTypes.TripAlight, c_char_p, c_int, c_int]),
    (lgs.alGetAlightingTripId, c_char_p, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetAlightingArrival, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetAlightingStopSequence, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alSearchAlightingsList, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetLastAlightingIndex, c_int, [LGSTypes.TripAlight, c_int]),
    (lgs.alGetOverage, c_int, [LGSTypes.TripAlight]),
    (lgs.alGetAlightingIndexByTripId, c_int, [LGSTypes.TripAlight, c_char_p]),
    (lgs.alWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.alWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbNew, LGSTypes.TripBoard, [LGSTypes.ServiceId, LGSTypes.ServiceCalendar, LGSTypes.Timezone, c_int]),
    (lgs.tbDestroy, None, [LGSTypes.TripBoard]),
    (lgs.tbGetCalendar, LGSTypes.ServiceCalendar, [LGSTypes.TripBoard]),
    (lgs.tbGetTimezone, LGSTypes.Timezone, [LGSTypes.TripBoard]),
    (lgs.tbGetAgency, c_int, [LGSTypes.TripBoard]),
    (lgs.tbGetServiceId, LGSTypes.ServiceId, [LGSTypes.TripBoard]),
    (lgs.tbGetNumBoardings, c_int, [LGSTypes.TripBoard]),
    (lgs.tbAddBoarding, None, [LGSTypes.TripBoard, c_char_p, c_int, c_int]),
    (lgs.tbGetBoardingTripId, c_char_p, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetBoardingDepart, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetBoardingStopSequence, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbSearchBoardingsList, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetNextBoardingIndex, c_int, [LGSTypes.TripBoard, c_int]),
    (lgs.tbGetOverage, c_int, [LGSTypes.TripBoard]),
    (lgs.tbWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.tbGetBoardingIndexByTripId, c_int, [LGSTypes.TripBoard, c_char_p]),
    (lgs.waitNew, LGSTypes.Wait, [c_long, LGSTypes.Timezone]),
    (lgs.waitDestroy, None, [LGSTypes.Wait]),
    (lgs.waitWalk, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.waitWalkBack, LGSTypes.State, [LGSTypes.EdgePayload, LGSTypes.State, LGSTypes.WalkOptions]),
    (lgs.waitGetEnd, c_long, [LGSTypes.Wait]),
    (lgs.waitGetTimezone, LGSTypes.Timezone, [LGSTypes.Wait])
]

for d in declarations:
    _declare(*d)

def caccessor(cfunc, restype, ptrclass=None):
    """Wraps a C data accessor in a python function.
       If a ptrclass is provided, the result will be converted to by the class' from_pointer method."""
    # Leaving this the the bulk declare process
    #cfunc.restype = restype
    #cfunc.argtypes = [c_void_p]
    if ptrclass:
        def prop(self):
            self.check_destroyed()
            ret = cfunc( c_void_p( self.soul ) )
            return ptrclass.from_pointer(ret)
    else:
        def prop(self):
            self.check_destroyed()
            return cfunc( c_void_p( self.soul ) )
    return prop

def cmutator(cfunc, argtype, ptrclass=None):
    """Wraps a C data mutator in a python function.  
       If a ptrclass is provided, the soul of the argument will be used."""
    # Leaving this to the bulk declare function
    #cfunc.argtypes = [c_void_p, argtype]
    #cfunc.restype = None
    if ptrclass:
        def propset(self, arg):
            cfunc( self.soul, arg.soul )
    else:
        def propset(self, arg):
            cfunc( self.soul, arg )
    return propset

def cproperty(cfunc, restype, ptrclass=None, setter=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    if not setter:
        return property(caccessor(cfunc, restype, ptrclass))
    return property(caccessor(cfunc, restype, ptrclass),
                    cmutator(setter, restype, ptrclass))

def ccast(func, cls):
    """Wraps a function to casts the result of a function (assumed c_void_p)
       into an object using the class's from_pointer method."""
    func.restype = c_void_p
    def _cast(self, *args):
        return cls.from_pointer(func(*args))
    return _cast

#CUSTOM TYPE API
class PayloadMethodTypes:
    """ Enumerates the ctypes of the function pointers."""
    destroy = CFUNCTYPE(c_void_p, py_object)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)

# 
import sys
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
    lgs = SafeWrapper(lgs,'lgs')
