try:
    from graphserver.gsdll import lgs, libc, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
except ImportError:
    #so I can run this script from the same folder
    from gsdll import lgs, libc, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p, py_object, c_float
from ctypes import Structure, pointer, cast, POINTER, addressof
from _ctypes import Py_INCREF, Py_DECREF
from time import asctime, gmtime
from time import time as now
import pytz
import calendar
from util import TimeHelpers

def indent( a, n ):
    return "\n".join( [" "*n+x for x in a.split("\n")] )
        
#TODO this is probably defined somewhere else, too
def unparse_secs(secs):
    return "%02d:%02d:%02d"%(secs/3600, (secs%3600)/60, secs%60)

"""

These classes map C structs to Python Ctypes Structures.

"""


class Walkable:
    """ Implements the walkable interface. """
    def walk(self, state, walk_options):
        return State.from_pointer(self._cwalk(self.soul, state.soul, walk_options.soul))
        
    def walk_back(self, state, walk_options):
        return State.from_pointer(self._cwalk_back(self.soul, state.soul, walk_options.soul))

"""

CType Definitions

"""

ServiceIdType = c_int

"""

Class Definitions

"""

#=============================================================================#
# Core Graph Classes                                                          #
#=============================================================================#

class Graph(CShadow):
    
    size = cproperty(lgs.gSize, c_long)
    
    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies #a central point that keeps track of how large the list of calendards need ot be in the state variables.
        
    def destroy(self, free_vertex_payloads=1, free_edge_payloads=1):
        #void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self.check_destroyed()
        
        self._cdel(self.soul, free_vertex_payloads, free_edge_payloads)
        self.soul = None
            
    def add_vertex(self, label):
        #Vertex* gAddVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cadd_vertex(self.soul, label)
        
    def remove_vertex(self, label, free_vertex_payload, free_edge_payload):
        #void gRemoveVertex( Graph* this, char *label, int free_vertex_payload, int free_edge_payloads );
        
        return self._cremove_vertex(self.soul, label, free_vertex_payload, free_edge_payload)
        
    def get_vertex(self, label):
        #Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)
        
    def add_edge( self, fromv, tov, payload ):
        #Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()
        
        e = self._cadd_edge( self.soul, fromv, tov, payload.soul )
        
        if e != None: return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)
        
    def set_vertex_enabled( self, vertex_label, enabled ):
        #void gSetVertexEnabled( Graph *this, char *label, int enabled );
        self.check_destroyed()
        
        lgs.gSetVertexEnabled( self.soul, vertex_label, enabled )
        
    @property
    def vertices(self):
        self.check_destroyed()
        
        count = c_int()
        p_va = lgs.gVertices(self.soul, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p)) # a bit of necessary voodoo
        for i in range(count.value):
            v = Vertex.from_pointer(arr[i])
            verts.append(v)
        return verts
    
    def add_vertices(self, vs):
        a = (c_char_p * len(vs))()
        for i, v in enumerate(vs):
            a[i] = str(v)
        lgs.gAddVertices(self.soul, a, len(vs))
    
    @property
    def edges(self):
        self.check_destroyed()
        
        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o: continue
            for e in o:
                edges.append(e)
        return edges    
    
    def shortest_path_tree(self, fromv, tov, initstate, walk_options=None, maxtime=2000000000):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not tov:
            tov = "*bogus^*^vertex*"
        
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime) )
            walk_options.destroy()
            return ret
        else:
            return self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime) )
        
    def shortest_path_tree_retro(self, fromv, tov, finalstate, walk_options=None, mintime=0):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not fromv:
            fromv = "*bogus^*^vertex*"
            
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime) )
            walk_options.destroy()
            return ret
        else:
            return self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime) )

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"

class ShortestPathTree(Graph):
    def path(self, destination):
        path_vertices, path_edges = self.path_retro(destination)
        
        if path_vertices is None:
            return (None,None)
        
        path_vertices.reverse()
        path_edges.reverse()
        
        return (path_vertices, path_edges)
        
    def path_retro(self,origin):
        self.check_destroyed()
        
        t = now()
        vcnt = c_long(0)
        ptr = lgs.sptPathRetro(self.soul, origin, 
                               byref(vcnt))
        
        vcnt = vcnt.value
        if vcnt <= 0:
            return (None, None) 

        pv = []
        pe = []
        vev_arr = cast(ptr, POINTER(c_void_p)) # a bit of necessary voodoo
        pv.append(Vertex.from_pointer(vev_arr[0]))
        for i in range(1,vcnt):
            pv.append(Vertex.from_pointer(vev_arr[2*i]))
            pe.append(Edge.from_pointer(vev_arr[2*i-1]))
        # free the vev_arr
        libc.free(ptr)
        
        return (pv, pe)
        
    def set_thicknesses(self, root_label):
        lgs.gSetThicknesses( c_void_p(self.soul), c_char_p(root_label) )

    def destroy(self):
        #destroy the vertex State instances, but not the edge EdgePayload instances, as they're owned by the parent graph
        super(ShortestPathTree, self).destroy(1, 0)

class EdgePayload(CShadow, Walkable):
    def __init__(self):
        if self.__class__ == EdgePayload:
            raise "EdgePayload is an abstract type."
    
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
        
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()
        return "<abstractedgepayload type='%s'/>" % self.type
    
    type = cproperty(lgs.epGetType, c_int)
    
    @classmethod
    def from_pointer(cls, ptr):
        """ Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        
        payloadtype = EdgePayload._subtypes[EdgePayload._cget_type(ptr)]
        if payloadtype is GenericPyPayload:
            p = lgs.cpSoul(ptr)
            # this is required to prevent garbage collection of the object
            Py_INCREF(p)
            return p
        ret = instantiate(payloadtype)
        ret.soul = ptr
        return ret

class State(CShadow):
    
    def __init__(self, n_agencies, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(n_agencies, long(time))
        
    def service_period(self, agency):
        soul = lgs.stateServicePeriod( self.soul, agency )
        return ServicePeriod.from_pointer( soul )
        
    def set_service_period(self, agency, sp):
        if agency>self.num_agencies-1:
            raise Exception("Agency index %d out of bounds"%agency)
        
        lgs.stateSetServicePeriod( self.soul, c_int(agency), sp.soul)
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
    
    def __copy__(self):
        self.check_destroyed()
        
        return self._ccopy(self.soul)
    
    def clone(self):
        self.check_destroyed()
        
        return self.__copy__()
    
    def __str__(self):
        self.check_destroyed()
        
        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()  
        
        ret = "<state time='%d' weight='%s' dist_walked='%s' " \
              "num_transfers='%s' trip_id='%s'>" % \
               (self.time,
               self.weight,
               self.dist_walked,
              self.num_transfers,
               self.trip_id)
        for i in range(self.num_agencies):
            if self.service_period(i) is not None:
                ret += self.service_period(i).to_xml()
        return ret + "</state>"
        
    time           = cproperty(lgs.stateGetTime, c_long, setter=lgs.stateSetTime)
    weight         = cproperty(lgs.stateGetWeight, c_long, setter=lgs.stateSetWeight)
    dist_walked    = cproperty(lgs.stateGetDistWalked, c_double, setter=lgs.stateSetDistWalked)
    num_transfers  = cproperty(lgs.stateGetNumTransfers, c_int, setter=lgs.stateSetNumTransfers)
    prev_edge      = cproperty(lgs.stateGetPrevEdge, c_void_p, EdgePayload, setter=lgs.stateSetPrevEdge )
    num_agencies     = cproperty(lgs.stateGetNumAgencies, c_int)
    trip_id          = cproperty(lgs.stateGetTripId, c_char_p)
    
class WalkOptions(CShadow):
    
    def __init__(self):
        self.soul = self._cnew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
        
    @classmethod
    def from_pointer(cls, ptr):
        """ Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
 
    transfer_penalty = cproperty(lgs.woGetTransferPenalty, c_int, setter=lgs.woSetTransferPenalty)
    turn_penalty = cproperty(lgs.woGetTurnPenalty, c_int, setter=lgs.woSetTurnPenalty)
    walking_speed = cproperty(lgs.woGetWalkingSpeed, c_float, setter=lgs.woSetWalkingSpeed)
    walking_reluctance = cproperty(lgs.woGetWalkingReluctance, c_float, setter=lgs.woSetWalkingReluctance)
    uphill_slowness = cproperty(lgs.woGetUphillSlowness, c_float, setter=lgs.woSetUphillSlowness)
    downhill_fastness = cproperty(lgs.woGetDownhillFastness, c_float, setter=lgs.woSetDownhillFastness)
    hill_reluctance = cproperty(lgs.woGetHillReluctance, c_float, setter=lgs.woSetHillReluctance)
    max_walk = cproperty(lgs.woGetMaxWalk, c_int, setter=lgs.woSetMaxWalk)
    walking_overage = cproperty(lgs.woGetWalkingOverage, c_float, setter=lgs.woSetWalkingOverage)

class Vertex(CShadow):
    
    label = cproperty(lgs.vGetLabel, c_char_p)
    degree_in = cproperty(lgs.vDegreeIn, c_int)
    degree_out = cproperty(lgs.vDegreeOut, c_int)
    
    def __init__(self,label):
        self.soul = self._cnew(label)
        
    def destroy(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?
        
        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None
    
    def to_xml(self):
        self.check_destroyed()
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (self.degree_out, self.degree_in, self.label)
    
    def __str__(self):
        self.check_destroyed()
        return self.to_xml()

    @property
    def outgoing(self):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges)
        
    @property
    def incoming(self):
        self.check_destroyed()
        return self._edges(self._cincoming_edges)
    
    @property
    def payload(self):
        self.check_destroyed()
        return self._cpayload(self.soul)

    def _edges(self, method, index = -1):
        self.check_destroyed()
        e = []
        node = method(self.soul)
        if not node: 
            if index == -1:
                return e
            else: 
                return None
        i = 0
        while node:
            if index != -1 and i == index:
                return node.data
            e.append(node.data)
            node = node.next
            i = i+1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self,i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, i)
        
    def get_incoming_edge(self,i):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, i)
        
    def __hash__(self):
        return int(self.soul)

class Edge(CShadow, Walkable):
    def __init__(self, from_v, to_v, payload):
        #Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
        self.soul = self._cnew(from_v.soul, to_v.soul, payload.soul)
    
    def __str__(self):
        return self.to_xml()
        
    def to_xml(self):
        return "<Edge>%s</Edge>" % (self.payload)
        
    @property
    def from_v(self):
        return self._cfrom_v(self.soul)
        
    @property
    def to_v(self):
        return self._cto_v(self.soul)
        
    @property
    def payload(self):
        return self._cpayload(self.soul)
        
    def walk(self, state, walk_options):
        return self._cwalk(self.soul, state.soul, walk_options.soul)
        
    thickness = cproperty(lgs.eGetThickness, c_long, setter=lgs.eSetThickness)
    enabled = cproperty(lgs.eGetEnabled, c_int, setter=lgs.eSetEnabled)


class ListNode(CShadow):
    @property
    def data(self):
        return self._cdata(self.soul)
    
    @property
    def next(self):
        return self._cnext(self.soul)

            



def failsafe(return_arg_num_on_failure):
    """ Decorator to prevent segfaults during failed callbacks."""
    def deco(func):
        def safe(*args):
            try:
                return func(*args)
            except:
                import traceback, sys            
                sys.stderr.write("ERROR: Exception during callback ")
                try:
                    sys.stderr.write("%s\n" % (map(str, args)))
                except:
                    pass
                traceback.print_exc()
                return args[return_arg_num_on_failure]
        return safe
    return deco

class GenericPyPayload(EdgePayload):
    """ This class is the base type for custom payloads created in Python.  
        Subclasses can override the *_impl methods, which will be invoked through
        C callbacks. """
        
    def __init__(self):
        """ Children MUST call this method to properly 
            register themselves in C world. """
        self.soul = self._cnew(py_object(self),self._cmethods)
        self.name = self.__class__.__name__
        # required to keep this object around in the C world
        Py_INCREF(self)

    def to_xml(self):
        return "<pypayload type='%s' class='%s'/>" % (self.type, self.__class__.__name__)

    """ These methods are the public interface, BUT should not be overridden by subclasses 
        - subclasses should override the *_impl methods instead.""" 
    @failsafe(1)
    def walk(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_impl(s, walkoptions)
    
    @failsafe(1)
    def walk_back(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_back_impl(s, walkoptions)
     
    """ These methods should be overridden by subclasses as deemed fit. """
    def walk_impl(self, state, walkoptions):
        return state

    def walk_back_impl(self, state, walkoptions):
        return state

    """ These methods provide the interface from the C world to py method implementation. """
    def _cwalk(self, stateptr, walkoptionsptr):
        return self.walk(State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)).soul

    def _cwalk_back(self, stateptr, walkoptionsptr):
        return self.walk_back(State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)).soul

    def _cfree(self):
        #print "Freeing %s..." % self
        # After this is freed in the C world, this can be freed
        Py_DECREF(self)
        self.soul = None
        
        
        
    _cmethodptrs = [PayloadMethodTypes.destroy(_cfree),
                    PayloadMethodTypes.walk(_cwalk),
                    PayloadMethodTypes.walk_back(_cwalk_back)]

    _cmethods = lgs.defineCustomPayloadType(*_cmethodptrs)

 
class NoOpPyPayload(GenericPyPayload):
    def __init__(self, num):
        self.num = num
        super(NoOpPyPayload,self).__init__()
    
    """ Dummy class."""
    def walk_impl(self, state, walkopts):
        print "%s walking..." % self
        
    def walk_back_impl(self, state, walkopts):
        print "%s walking back..." % self
        
        
    def to_xml(self):
        return "<NoOpPyPayload type='%s' num='%s'/>" % (self.type, self.num)
    
#=============================================================================#
# Edge Type Support Classes                                                   #
#=============================================================================#

class ServicePeriod(CShadow):   

    begin_time = cproperty(lgs.spBeginTime, c_long)
    end_time = cproperty(lgs.spEndTime, c_long)

    def __init__(self, begin_time, end_time, service_ids):
        n, sids = ServicePeriod._py2c_service_ids(service_ids)
        self.soul = self._cnew(begin_time, end_time, n, sids)
    
    @property
    def service_ids(self):
        count = c_int()
        ptr = lgs.spServiceIds(self.soul, byref(count))
        ptr = cast(ptr, POINTER(ServiceIdType))
        ids = []
        for i in range(count.value):
            ids.append(ptr[i])
        return ids
    
    @property
    def previous(self):
        return self._cprev(self.soul)

    @property
    def next(self):
        return self._cnext(self.soul)

    def rewind(self):
        return self._crewind(self.soul)
        
    def fast_forward(self):
        return self._cfast_forward(self.soul)
    
    def __str__(self):
        return self.to_xml()
    
    def to_xml(self, cal=None):
        if cal is not None:
            sids = [cal.get_service_id_string(x) for x in self.service_ids]
        else:
            sids = [str(x) for x in self.service_ids]

        return "<ServicePeriod begin_time='%d' end_time='%d' service_ids='%s'/>" %( self.begin_time, self.end_time, ",".join(sids))
    
    def datum_midnight(self, timezone_offset):
        return lgs.spDatumMidnight( self.soul, timezone_offset )
    
    def normalize_time(self, timezone_offset, time):
        return lgs.spNormalizeTime(self.soul, timezone_offset, time)
        
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.service_ids)
        
    def __setstate__(self, state):
        self.__init__(*state)
        
    def __repr__(self):
        return "(%s %s->%s)"%(self.service_ids, self.begin_time, self.end_time)
        
    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)

class ServiceCalendar(CShadow):
    """Calendar provides a set of convient methods for dealing with the wrapper class ServicePeriod, which
       wraps a single node in the doubly linked list that represents a calendar in Graphserver."""
    head = cproperty( lgs.scHead, c_void_p, ServicePeriod )
       
    def __init__(self):
        self.soul = lgs.scNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    
    def get_service_id_int( self, service_id ):
        if type(service_id)!=type("string"):
            raise TypeError("service_id is supposed to be a string")
        
        return lgs.scGetServiceIdInt( self.soul, service_id );
        
    def get_service_id_string( self, service_id ):
        if type(service_id)!=type(1):
            raise TypeError("service_id is supposed to be an int, in this case")
        
        return lgs.scGetServiceIdString( self.soul, service_id )
        
    def add_period(self, begin_time, end_time, service_ids):
        sp = ServicePeriod( begin_time, end_time, [self.get_service_id_int(x) for x in service_ids] )
        
        lgs.scAddPeriod(self.soul, sp.soul)

    def period_of_or_after(self,time):
        soul = lgs.scPeriodOfOrAfter(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    def period_of_or_before(self,time):
        soul = lgs.scPeriodOfOrBefore(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    @property
    def periods(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next
            
    def to_xml(self):
        ret = ["<ServiceCalendar>"]
        for period in self.periods:
            ret.append( period.to_xml(self) )
        ret.append( "</ServiceCalendar>" )
        return "".join(ret)
        
    def __getstate__(self):
        ret = []
        max_sid = -1
        curs = self.head
        while curs:
            start, end, sids = curs.__getstate__()
            for sid in sids:
                max_sid = max(max_sid, sid)
            sids = [self.get_service_id_string(sid) for sid in sids]

            ret.append( (start,end,sids) )
            curs = curs.next
        sids_list = [self.get_service_id_string(sid) for sid in range(max_sid+1)]
        return (sids_list, ret)
        
    def __setstate__(self, state):
        self.__init__()
        sids_list, periods = state
        for sid in sids_list:
            self.get_service_id_int(sid)
            
        for p in periods:
            self.add_period( *p )
            
    def __repr__(self):
        return "<ServiceCalendar periods=%s>"%repr(list(self.periods))
        
    def expound(self, timezone_name):
        periodstrs = []
        
        for period in self.periods:
            begin_time = TimeHelpers.unix_to_localtime( period.begin_time, timezone_name )
            end_time = TimeHelpers.unix_to_localtime( period.end_time, timezone_name )
            service_ids = dict([(id,self.get_service_id_string(id)) for id in period.service_ids])
            periodstrs.append( "sids:%s active from %d (%s) to %d (%s)"%(service_ids, period.begin_time, begin_time, period.end_time, end_time) )
        
        return "\n".join( periodstrs )
    
class TimezonePeriod(CShadow):
    begin_time = cproperty(lgs.tzpBeginTime, c_long)
    end_time = cproperty(lgs.tzpEndTime, c_long)
    utc_offset = cproperty(lgs.tzpUtcOffset, c_long)
    
    def __init__(self, begin_time, end_time, utc_offset):
        self.soul = lgs.tzpNew(begin_time, end_time, utc_offset)
    
    @property
    def next_period(self):
        return TimezonePeriod.from_pointer( lgs.tzpNextPeriod( self.soul ) )
        
    def time_since_midnight(self, time):
        return lgs.tzpTimeSinceMidnight( self.soul, c_long(time) )
        
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.utc_offset)
    
    def __setstate__(self, state):
        self.__init__(*state)
                
        
class Timezone(CShadow):
    head = cproperty( lgs.tzHead, c_void_p, TimezonePeriod )
    
    def __init__(self):
        self.soul = lgs.tzNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    def add_period(self, timezone_period):
        lgs.tzAddPeriod( self.soul, timezone_period.soul)
        
    def period_of(self, time):
        tzpsoul = lgs.tzPeriodOf( self.soul, time )
        return TimezonePeriod.from_pointer( tzpsoul )
        
    def utc_offset(self, time):
        ret = lgs.tzUtcOffset( self.soul, time )
        
        if ret==-360000:
            raise IndexError( "%d lands within no timezone period"%time )
            
        return ret
        
    def time_since_midnight(self, time):
        ret = lgs.tzTimeSinceMidnight( self.soul, c_long(time) )
        
        if ret==-1:
            raise IndexError( "%d lands within no timezone period"%time )
            
        return ret
        
    @classmethod
    def generate(cls, timezone_string):
        ret = Timezone()
        
        timezone = pytz.timezone(timezone_string)
        tz_periods = zip(timezone._utc_transition_times[:-1],timezone._utc_transition_times[1:])
            
        #exclude last transition_info entry, as it corresponds with the last utc_transition_time, and not the last period as defined by the last two entries
        for tz_period, (utcoffset,dstoffset,periodname) in zip( tz_periods, timezone._transition_info[:-1] ):
            period_begin, period_end = [calendar.timegm( (x.year, x.month, x.day, x.hour, x.minute, x.second) ) for x in tz_period]
            period_end -= 1 #period_end is the last second the period is active, not the first second it isn't
            utcoffset = utcoffset.days*24*3600 + utcoffset.seconds
            
            ret.add_period( TimezonePeriod( period_begin, period_end, utcoffset ) )
        
        return ret
        
    def __getstate__(self):
        ret = []
        curs = self.head
        while curs:
            ret.append( curs.__getstate__() )
            curs = curs.next_period
        return ret
        
    def __setstate__(self, state):
        self.__init__()
        for tzpargs in state:
            self.add_period( TimezonePeriod(*tzpargs) )
            
    def expound(self):
        return "Timezone"
    
#=============================================================================#
# Edge Types                                                                  #
#=============================================================================#
    
class Link(EdgePayload):
    name = cproperty(lgs.linkGetName, c_char_p)
    
    def __init__(self):
        self.soul = self._cnew()

    def to_xml(self):
        self.check_destroyed()
        
        return "<Link name='%s'/>" % (self.name)
        
    def __getstate__(self):
        return tuple([])
        
    def __setstate__(self, state):
        self.__init__()
        
    @classmethod
    def reconstitute(self, state, resolver):
        return Link()
    
class Street(EdgePayload):
    length = cproperty(lgs.streetGetLength, c_double)
    name   = cproperty(lgs.streetGetName, c_char_p)
    rise = cproperty(lgs.streetGetRise, c_float)
    fall = cproperty(lgs.streetGetFall, c_float)
    slog = cproperty(lgs.streetGetSlog, c_float, setter=lgs.streetSetSlog)
    way = cproperty(lgs.streetGetWay, c_long, setter=lgs.streetSetWay)
    
    def __init__(self,name,length,rise=0,fall=0):
        self.soul = self._cnew(name, length, rise, fall)
            
    def to_xml(self):
        self.check_destroyed()
        
        return "<Street name='%s' length='%f' rise='%f' fall='%f' way='%ld'/>" % (self.name, self.length, self.rise, self.fall, self.way)
        
    def __getstate__(self):
        return (self.name, self.length, self.rise, self.fall, self.slog, self.way)
        
    def __setstate__(self, state):
        name, length, rise, fall, slog, way = state
        self.__init__(name, length, rise, fall)
        self.slog = slog
        self.way = way
        
    def __repr__(self):
        return "<Street name='%s' length=%f rise=%f fall=%f way=%ld>"%(self.name, self.length, self.rise, self.fall, self.way)
        
    @classmethod
    def reconstitute(self, state, resolver):
        name, length, rise, fall, slog, way = state
        ret = Street( name, length, rise, fall )
        ret.slog = slog
        ret.way = way
        return ret

class Egress(EdgePayload):
    length = cproperty(lgs.egressGetLength, c_double)
    name   = cproperty(lgs.egressGetName, c_char_p)
    
    def __init__(self,name,length):
        self.soul = self._cnew(name, length)
            
    def to_xml(self):
        self.check_destroyed()
        
        return "<Egress name='%s' length='%f' />" % (self.name, self.length)
        
    def __getstate__(self):
        return (self.name, self.length)
        
    def __setstate__(self, state):
        self.__init__(*state)
        
    def __repr__(self):
        return "<Egress name='%s' length=%f>"%(self.name, self.length)
        
    @classmethod
    def reconstitute(self, state, resolver):
        return Egress( *state )


class Wait(EdgePayload):
    end = cproperty(lgs.waitGetEnd, c_long)
    timezone = cproperty(lgs.waitGetTimezone, c_void_p, Timezone)
    
    def __init__(self, end, timezone):
        self.soul = self._cnew( end, timezone.soul )
        
    def to_xml(self):
        self.check_destroyed()
        
        return "<Wait end='%ld' />"%(self.end)
        
    def __getstate__(self):
        return (self.end, self.timezone.soul)

class ElapseTime(EdgePayload):
    seconds = cproperty(lgs.elapseTimeGetSeconds, c_long)
    
    def __init__(self, seconds):
        self.soul = self._cnew( seconds )
        
    def to_xml(self):
        self.check_destroyed()
        
        return "<ElapseTime seconds='%ld' />"%(self.seconds)
        
    def __getstate__(self):
        return self.seconds
    
    @classmethod
    def reconstitute(cls, state, resolver):
        return cls(state)



class Headway(EdgePayload):
    
    begin_time = cproperty( lgs.headwayBeginTime, c_int )
    end_time = cproperty( lgs.headwayEndTime, c_int )
    wait_period = cproperty( lgs.headwayWaitPeriod, c_int )
    transit = cproperty( lgs.headwayTransit, c_int )
    trip_id = cproperty( lgs.headwayTripId, c_char_p )
    calendar = cproperty( lgs.headwayCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.headwayTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.headwayAgency, c_int )
    int_service_id = cproperty( lgs.headwayServiceId, c_int )
    
    def __init__(self, begin_time, end_time, wait_period, transit, trip_id, calendar, timezone, agency, service_id):
        if type(service_id)!=type('string'):
            raise TypeError("service_id is supposed to be a string")
            
        int_sid = calendar.get_service_id_int( service_id )
        
        self.soul = lgs.headwayNew(begin_time, end_time, wait_period, transit, trip_id.encode("ascii"),  calendar.soul, timezone.soul, c_int(agency), ServiceIdType(int_sid))
        
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
        
    def to_xml(self):
        return "<Headway begin_time='%d' end_time='%d' wait_period='%d' transit='%d' trip_id='%s' agency='%d' int_service_id='%d' />"% \
                       (self.begin_time,
                        self.end_time,
                        self.wait_period,
                        self.transit,
                        self.trip_id,
                        self.agency,
                        self.int_service_id)
    
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.wait_period, self.transit, self.trip_id, self.calendar.soul, self.timezone.soul, self.agency, self.calendar.get_service_id_string(self.int_service_id))
        
class TripBoard(EdgePayload):
    calendar = cproperty( lgs.tbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.tbGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.tbGetAgency, c_int )
    int_service_id = cproperty( lgs.tbGetServiceId, c_int )
    num_boardings = cproperty( lgs.tbGetNumBoardings, c_int )
    overage = cproperty( lgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
    
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
    
    def add_boarding(self, trip_id, depart):
        self._cadd_boarding( self.soul, trip_id, depart )
        
    def get_boarding(self, i):
        trip_id = lgs.tbGetBoardingTripId(self.soul, c_int(i))
        depart = lgs.tbGetBoardingDepart(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, depart)
    
    def search_boardings_list(self, time):
        return lgs.tbSearchBoardingsList( self.soul, c_int(time) )
        
    def get_next_boarding_index(self, time):
        return lgs.tbGetNextBoardingIndex( self.soul, c_int(time) )
        
    def get_next_boarding(self, time):
        i = self.get_next_boarding_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_boarding( i )
            
    def to_xml(self):
        return "<TripBoard />"
        
    def __repr__(self):
        return "<TripBoard int_sid=%d sid=%s agency=%d calendar=%s timezone=%s boardings=%s>"%(self.int_service_id, self.calendar.get_service_id_string(self.int_service_id), self.agency, self.calendar.soul,self.timezone.soul,[self.get_boarding(i) for i in range(self.num_boardings)])
        
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        boardings = []
        for i in range(self.num_boardings):
            boardings.append( self.get_boarding( i ) )
        state['boardings'] = boardings
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        
        ret = TripBoard(int_sid, calendar, timezone, agency)
        
        for trip_id, depart in state['boardings']:
            ret.add_boarding( trip_id, depart )
            
        return ret
        
    def expound(self):
        boardingstrs = []
        
        for i in range(self.num_boardings):
            trip_id, departure_secs = self.get_boarding(i)
            boardingstrs.append( "on trip id='%s' at %s"%(trip_id, unparse_secs(departure_secs)) )
        
        ret = """TripBoard
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   boardings:
%s"""%( self.agency,
        self.int_service_id,
        indent( self.calendar.expound("America/Chicago"), 6 ),
        indent( self.timezone.expound(), 6 ),
        indent( "\n".join(boardingstrs), 6 ) )

        return ret
        
        
class HeadwayBoard(EdgePayload):
    calendar = cproperty( lgs.hbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.hbGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.hbGetAgency, c_int )
    int_service_id = cproperty( lgs.hbGetServiceId, c_int )
    trip_id = cproperty( lgs.hbGetTripId, c_char_p )
    start_time = cproperty( lgs.hbGetStartTime, c_int )
    end_time = cproperty( lgs.hbGetEndTime, c_int )
    headway_secs = cproperty( lgs.hbGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayBoard calendar=%d timezone=%d agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(self.calendar.soul,
                                                                                                                                          self.timezone.soul,
                                                                                                                                          self.agency,
                                                                                                                                          self.int_service_id,
                                                                                                                                          self.trip_id,
                                                                                                                                          self.start_time,
                                                                                                                                          self.end_time,
                                                                                                                                          self.headway_secs)

    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
                                                                                                                                      
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        state['trip_id'] = self.trip_id
        state['start_time'] = self.start_time
        state['end_time'] = self.end_time
        state['headway_secs'] = self.headway_secs
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        trip_id = state['trip_id']
        start_time = state['start_time']
        end_time = state['end_time']
        headway_secs = state['headway_secs']
        
        ret = HeadwayBoard(int_sid, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs)
            
        return ret
        
class HeadwayAlight(EdgePayload):
    calendar = cproperty( lgs.haGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.haGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.haGetAgency, c_int )
    int_service_id = cproperty( lgs.haGetServiceId, c_int )
    trip_id = cproperty( lgs.haGetTripId, c_char_p )
    start_time = cproperty( lgs.haGetStartTime, c_int )
    end_time = cproperty( lgs.haGetEndTime, c_int )
    headway_secs = cproperty( lgs.haGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayAlight calendar=%d timezone=%d agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(self.calendar.soul,
                                                                                                                                          self.timezone.soul,
                                                                                                                                          self.agency,
                                                                                                                                          self.int_service_id,
                                                                                                                                          self.trip_id,
                                                                                                                                          self.start_time,
                                                                                                                                          self.end_time,
                                                                                                                                          self.headway_secs)
                                                                                                                                          
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        state['trip_id'] = self.trip_id
        state['start_time'] = self.start_time
        state['end_time'] = self.end_time
        state['headway_secs'] = self.headway_secs
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        trip_id = state['trip_id']
        start_time = state['start_time']
        end_time = state['end_time']
        headway_secs = state['headway_secs']
        
        ret = HeadwayAlight(int_sid, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs)
            
        return ret
    
class Crossing(EdgePayload):
    crossing_time = cproperty( lgs.crGetCrossingTime, c_int )
    
    def __init__(self, crossing_time):
        self.soul = self._cnew(c_int(crossing_time))
        
    def to_xml(self):
        return "<Crossing crossing_time=\"%d\"/>"%self.crossing_time
        
    def __getstate__(self):
        return self.crossing_time
        
    @classmethod
    def reconstitute(cls, state, resolver):
        return Crossing(state)
        
class Alight(EdgePayload):
    calendar = cproperty( lgs.alGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( lgs.alGetTimezone, c_void_p, Timezone )
    agency = cproperty( lgs.alGetAgency, c_int )
    int_service_id = cproperty( lgs.alGetServiceId, c_int )
    num_alightings = cproperty( lgs.alGetNumAlightings, c_int )
    overage = cproperty( lgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
        
    def add_alighting(self, trip_id, arrival):
        lgs.alAddAlighting( self.soul, trip_id, arrival )
        
    def get_alighting(self, i):
        trip_id = lgs.alGetAlightingTripId(self.soul, c_int(i))
        arrival = lgs.alGetAlightingArrival(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, arrival)
        
    def search_alightings_list(self, time):
        return lgs.alSearchAlightingsList( self.soul, c_int(time) )
        
    def get_last_alighting_index(self, time):
        return lgs.alGetLastAlightingIndex( self.soul, c_int(time) )
        
    def get_last_alighting(self, time):
        i = self.get_last_alighting_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_alighting( i )
        
    def to_xml(self):
        return "<Alight/>"
        
    def __repr__(self):
        return "<Alight int_sid=%d agency=%d calendar=%s timezone=%s alightings=%s>"%(self.int_service_id, self.agency, self.calendar.soul,self.timezone.soul,[self.get_alighting(i) for i in range(self.num_alightings)])
        
    def __getstate__(self):
        state = {}
        state['calendar'] = self.calendar.soul
        state['timezone'] = self.timezone.soul
        state['agency'] = self.agency
        state['int_sid'] = self.int_service_id
        alightings = []
        for i in range(self.num_alightings):
            alightings.append( self.get_alighting( i ) )
        state['alightings'] = alightings
        return state
        
    def __resources__(self):
        return ((str(self.calendar.soul), self.calendar),
                (str(self.timezone.soul), self.timezone))
    
    @classmethod
    def reconstitute(cls, state, resolver):
        calendar = resolver.resolve( state['calendar'] )
        timezone = resolver.resolve( state['timezone'] )
        int_sid = state['int_sid']
        agency = state['agency']
        
        ret = Alight(int_sid, calendar, timezone, agency)
        
        for trip_id, arrival in state['alightings']:
            ret.add_alighting( trip_id, arrival )
            
        return ret
        
    def expound(self):
        alightingstrs = []
        
        for i in range(self.num_alightings):
            trip_id, arrival_secs = self.get_alighting(i)
            alightingstrs.append( "on trip id='%s' at %s"%(trip_id, unparse_secs(arrival_secs)) )
        
        ret = """Alight
   agency (internal id): %d
   service_id (internal id): %d
   calendar:
%s
   timezone:
%s
   alightings:
%s"""%( self.agency,
        self.int_service_id,
        indent( self.calendar.expound("America/Chicago"), 6 ),
        indent( self.timezone.expound(), 6 ),
        indent( "\n".join(alightingstrs), 6 ) )

        return ret

class VertexNotFoundError(Exception): pass

Graph._cnew = lgs.gNew
Graph._cdel = lgs.gDestroy
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)
Graph._cremove_vertex = lgs.gRemoveVertex
Graph._cget_vertex = ccast(lgs.gGetVertex, Vertex)
Graph._cadd_edge = ccast(lgs.gAddEdge, Edge)
Graph._cshortest_path_tree = ccast(lgs.gShortestPathTree, ShortestPathTree)
Graph._cshortest_path_tree_retro = ccast(lgs.gShortestPathTreeRetro, ShortestPathTree)

Vertex._cnew = lgs.vNew
Vertex._cdel = lgs.vDestroy
Vertex._coutgoing_edges = ccast(lgs.vGetOutgoingEdgeList, ListNode)
Vertex._cincoming_edges = ccast(lgs.vGetIncomingEdgeList, ListNode)
Vertex._cpayload = ccast(lgs.vPayload, State)

Edge._cnew = lgs.eNew
Edge._cfrom_v = ccast(lgs.eGetFrom, Vertex)
Edge._cto_v = ccast(lgs.eGetTo, Vertex)
Edge._cpayload = ccast(lgs.eGetPayload, EdgePayload)
Edge._cwalk = ccast(lgs.eWalk, State)
Edge._cwalk_back = lgs.eWalkBack

EdgePayload._subtypes = {0:Street,1:None,2:None,3:Link,4:GenericPyPayload,5:None,
                         6:Wait,7:Headway,8:TripBoard,9:Crossing,10:Alight,
                         11:HeadwayBoard,12:Egress,13:HeadwayAlight,14:ElapseTime}
EdgePayload._cget_type = lgs.epGetType
EdgePayload._cwalk = lgs.epWalk
EdgePayload._cwalk_back = lgs.epWalkBack

ServicePeriod._cnew = lgs.spNew
ServicePeriod._crewind = ccast(lgs.spRewind, ServicePeriod)
ServicePeriod._cfast_forward = ccast(lgs.spFastForward, ServicePeriod)
ServicePeriod._cnext = ccast(lgs.spNextPeriod, ServicePeriod)
ServicePeriod._cprev = ccast(lgs.spPreviousPeriod, ServicePeriod)

ServiceCalendar._cnew = lgs.scNew
ServiceCalendar._cdel = lgs.scDestroy
ServiceCalendar._cperiod_of_or_before = ccast(lgs.scPeriodOfOrBefore, ServicePeriod)
ServiceCalendar._cperiod_of_or_after = ccast(lgs.scPeriodOfOrAfter, ServicePeriod)

Timezone._cdel = lgs.tzDestroy

State._cnew = lgs.stateNew
State._cdel = lgs.stateDestroy
State._ccopy = ccast(lgs.stateDup, State)

ListNode._cdata = ccast(lgs.liGetData, Edge)
ListNode._cnext = ccast(lgs.liGetNext, ListNode)

Street._cnew = lgs.streetNewElev
Street._cdel = lgs.streetDestroy
Street._cwalk = lgs.streetWalk
Street._cwalk_back = lgs.streetWalkBack

Egress._cnew = lgs.egressNew
Egress._cdel = lgs.egressDestroy
Egress._cwalk = lgs.egressWalk
Egress._cwalk_back = lgs.egressWalkBack

Link._cnew = lgs.linkNew
Link._cdel = lgs.linkDestroy
Link._cwalk = lgs.epWalk
Link._cwalk_back = lgs.linkWalkBack

Wait._cnew = lgs.waitNew
Wait._cdel = lgs.waitDestroy
Wait._cwalk = lgs.waitWalk
Wait._cwalk_back = lgs.waitWalkBack

ElapseTime._cnew = lgs.elapseTimeNew
ElapseTime._cdel = lgs.elapseTimeDestroy
ElapseTime._cwalk = lgs.elapseTimeWalk
ElapseTime._cwalk_back = lgs.elapseTimeWalkBack


TripBoard._cnew = lgs.tbNew
TripBoard._cdel = lgs.tbDestroy
TripBoard._cadd_boarding = lgs.tbAddBoarding
TripBoard._cwalk = lgs.epWalk

Crossing._cnew = lgs.crNew
Crossing._cdel = lgs.crDestroy

Alight._cnew = lgs.alNew
Alight._cdel = lgs.alDestroy

HeadwayBoard._cnew = lgs.hbNew
HeadwayBoard._cdel = lgs.hbDestroy
HeadwayBoard._cwalk = lgs.epWalk

HeadwayAlight._cnew = lgs.haNew
HeadwayAlight._cdel = lgs.haDestroy
HeadwayAlight._cwalk = lgs.epWalk

WalkOptions._cnew = lgs.woNew
WalkOptions._cdel = lgs.woDestroy

GenericPyPayload._cnew = lgs.cpNew
GenericPyPayload._cdel = lgs.cpDestroy
