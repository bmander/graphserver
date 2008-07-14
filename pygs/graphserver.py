
try:
    from pygs.gsdll import lgs, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
except ImportError:
    #so I can run this script from the same folder
    from gsdll import lgs, cproperty, ccast, CShadow, instantiate, PayloadMethodTypes
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p, py_object
from ctypes import Structure, pointer, cast, POINTER, addressof
from _ctypes import Py_INCREF, Py_DECREF
from time import asctime, gmtime
from time import time as now


"""

These classes map C structs to Python Ctypes Structures.

"""

class Collapsable:
    def collapse(self, state):
        return self._ccollapse(self.soul, state.soul)
    
    def collapse_back(self,state):
        return self._ccollapse_back(self.soul, state.soul)

class Walkable:
    """ Implements the walkable interface. """
    def walk(self, state):
        return State.from_pointer(self._cwalk(self.soul, state.soul))
        
    def walk_back(self, state):
        return State.from_pointer(self._cwalk_back(self.soul, state.soul))



"""

CType Definitions

"""

ServiceIdType = c_int

"""

Class Definitions

"""

class Graph(CShadow):
    
    size = cproperty(lgs.gSize, c_long)
    
    def __init__(self):
        self.soul = self._cnew()
        
    def destroy(self, free_vertex_payloads=1, free_edge_payloads=1):
        #void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self.check_destroyed()
        
        self._cdel(self.soul, free_vertex_payloads, free_edge_payloads)
        self.soul = None
            
    def add_vertex(self, label):
        #Vertex* gAddVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cadd_vertex(self.soul, label)
        
    def get_vertex(self, label):
        #Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)
        
    def add_edge( self, fromv, tov, payload ):
        #Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()
        
        return self._cadd_edge( self.soul, fromv, tov, payload.soul )
    
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
    
    def shortest_path_tree(self, fromv, tov, initstate):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()

        return self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul )
        
    def shortest_path_tree_retro(self, fromv, tov, finalstate):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        
        return self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul )
    """
    def shortest_path_tree(self, from_key, to_key, init, direction=True):
        if direction:
            if not to_key:
                to_key = ""
            tree = lgs.gShortestPathTree(self.c_ref, c_char_p(from_key), c_char_p(to_key), byref(init))
        else:
            if not from_key:
                from_key = ""
            tree = lgs.gShortestPathTreeRetro(self.c_ref, c_char_p(from_key), c_char_p(to_key), byref(init))
        return tree.contents
    """

    """
    def shortest_path(self, from_v, to_v, init_state):
        self.check_destroyed()
        
        path_vertices = []
        path_edges    = []
   
        spt = self.shortest_path_tree( from_v, to_v, init_state)
        curr = spt.get_vertex( to_v )
        
        #if the destination isn't in the SPT, there is no route
        if curr is None:
            return None, None
    
        path_vertices.append( curr )
        
        while curr.label != from_v:
            edge_in = curr.incoming[0]
            path_edges.append( edge_in )
            curr = edge_in.from_v
            path_vertices.append( curr )
    
        path_vertices.reverse()
        path_edges.reverse()
        return (path_vertices, path_edges)
    
    def shortest_path_retro(from_v, to_v, final_state):
        self.check_destroyed()
        
        path_vertices = []
        path_edges    = []
          
        spt = self.shortest_path_tree( from_v, to_v, final_state, False )
        curr = spt.get_vertex( from_v )
        
        #if the origin isn't in the SPT, there is no route
        if curr is None:
            return None,None
        
        path_vertices.append(curr)

        incoming = curr.edge_in(0)
        while incoming:
            path_edges.append(incoming)
            curr = incoming.from_v
            path_vertices.append(curr)
            incoming = curr.edge_in(0)

        return path_vertices, path_edges
    """

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"

class ShortestPathTree(Graph):
    def path(self, vertex):
        self.check_destroyed()
        
        path_vertices = []
        path_edges    = []
   
        curr = self.get_vertex( vertex )
        
        #if the destination isn't in the SPT, there is no route
        if curr is None:
            return None, None
    
        path_vertices.append( curr )
        
        while len(curr.incoming) != 0:
            edge_in = curr.incoming[0]
            path_edges.append( edge_in )
            curr = edge_in.from_v
            path_vertices.append( curr )
    
        path_vertices.reverse()
        path_edges.reverse()
        return (path_vertices, path_edges)

    def destroy(self):
        #destroy the vertex State instances, but not the edge EdgePayload instances, as they're owned by the parent graph
        super(ShortestPathTree, self).destroy(1, 0)

class Calendar:
    """Calendar provides a set of convient methods for dealing with the wrapper class CalendarDay, which
       wraps a single node in the doubly linked list that represents a calendar in Graphserver."""
    def __init__(self):
        self.service_id_directory = {}
        self.head = None
        self.tail = None
        
        self.curr = None
        
    def add_day(self, begin_time, end_time, service_ids, daylight_savings=0):

        if self.head is not None and (begin_time <= self.tail.end_time):
            raise Exception( "begin_time (%d) is not after the tail's end_time (%d)"%(begin_time,self.tail.end_time) )

        #translate service_ids to numbers
        for service_id in service_ids:
            if service_id not in self.service_id_directory:
                self.service_id_directory[service_id]=len(self.service_id_directory)+1
        service_ids = [self.service_id_directory[x] for x in service_ids]

        if self.head is None:
            cday = CalendarDay(begin_time,end_time,service_ids,daylight_savings)
            self.head = cday
            self.tail = cday
        else:
            self.tail.append_day( begin_time, end_time, service_ids, daylight_savings )
            self.tail = self.tail.next
            
    def day_of_or_after(self,time):
        if self.head is None:
            return None
            
        return self.head.day_of_or_after(time)
        
    def day_of_or_before(self,time):
        if self.head is None:
            return None
        
        return self.head.day_of_or_before(time)
    
    def days(self):
        curr = self.head
        while curr is not None:
            yield curr
            curr = curr.next
        

class CalendarDay(CShadow):   

    begin_time = cproperty(lgs.calBeginTime, c_long)
    end_time = cproperty(lgs.calEndTime, c_long)
    daylight_savings = cproperty(lgs.calDaylightSavings, c_int)
    

    def __init__(self, begin_time, end_time, service_ids, daylight_savings):
        n, sids = CalendarDay._py2c_service_ids(service_ids)
        self.soul = self._cnew(begin_time, end_time, n, sids, daylight_savings)
        
    def append_day(self, begin_time, end_time, service_ids, daylight_savings):
        n, sids = self._py2c_service_ids(service_ids)
        return self._cappend_day(self.soul, begin_time, end_time, n, sids, daylight_savings)
    
    @property
    def service_ids(self):
        count = c_int()
        ptr = lgs.calServiceIds(self.soul, byref(count))
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
    
    def day_of_or_after(self, time):
        return self._cday_of_or_after(self.soul, time)
        
    def day_of_or_before(self, time):
        return self._cday_of_or_before(self.soul, time)
    
    def __str__(self):
        return self.to_xml()
    
    def to_xml(self):
        return "<calendar begin_time='%s' end_time='%s' service_ids='%s'/>" % \
            (asctime(gmtime(self.begin_time)), asctime(gmtime(self.end_time)), 
             ",".join(map(str, self.service_ids)))
        
    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)



class State(CShadow):
    
    def __init__(self, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(long(time))
        
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
        
        ret = "<state time='%s' weight='%s' dist_walked='%s' " \
              "num_transfers='%s' prev_edge_type='%s' prev_edge_name='%s'>" % \
              (asctime(gmtime(self.time)),
               self.weight,
               self.dist_walked,
               self.num_transfers,
               self.prev_edge_type,
               self.prev_edge_name)
        if self.calendar_day:
            ret += self.calendar_day.to_xml()
        return ret + "</state>"
        
    time           = cproperty(lgs.stateGetTime, c_long, setter=lgs.stateSetTime)
    weight         = cproperty(lgs.stateGetWeight, c_long, setter=lgs.stateSetWeight)
    dist_walked    = cproperty(lgs.stateGetDistWalked, c_double, setter=lgs.stateSetDistWalked)
    num_transfers  = cproperty(lgs.stateGetNumTransfers, c_int, setter=lgs.stateSetNumTransfers)
    prev_edge_type = cproperty(lgs.stateGetPrevEdgeType, c_int) # should not use: setter=lgs.stateSetPrevEdgeType)
    prev_edge_name = cproperty(lgs.stateGetPrevEdgeName, c_char_p, setter=lgs.stateSetPrevEdgeName)
    calendar_day   = cproperty(lgs.stateCalendarDay, c_void_p, CalendarDay, setter=lgs.stateSetCalendarDay)
        

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
                print "return none1"
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

""" things not implemented after I moved over to the "soul" model
    
    def walk(self, state):
        return cast(lgs.vWalk(self, state), State)
"""

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
        
    def walk(self, state):
        return self._cwalk(self.soul, state.soul)


class ListNode(CShadow):
    @property
    def data(self):
        return self._cdata(self.soul)
    
    @property
    def next(self):
        return self._cnext(self.soul)

            
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
    def walk(self, state):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_impl(s)
    
    @failsafe(1)
    def walk_back(self, state):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_back_impl(s)

    @failsafe(0)
    def collapse(self, state):
        return self.collapse_impl(state)

    @failsafe(0)
    def collapse_back(self, state):
        return self.collapse_back_impl(state)
     
    """ These methods should be overridden by subclasses as deemed fit. """
    def walk_impl(self, state):
        return state

    def walk_back_impl(self, state):
        return state

    def collapse_impl(self, state):
        return self

    def collapse_back_impl(self, state):
        return self

    """ These methods provide the interface from the C world to py method implementation. """
    def _cwalk(self, stateptr):
        return self.walk(State.from_pointer(stateptr)).soul

    def _cwalk_back(self, stateptr):
        return self.walk_back(State.from_pointer(stateptr)).soul

    def _ccollapse(self, stateptr):
        return self.collapse(State.from_pointer(stateptr)).soul

    def _ccollapse_back(self, stateptr):
        return self.collapse_back(State.from_pointer(stateptr)).soul

    def _cfree(self):
        #print "Freeing %s..." % self
        # After this is freed in the C world, this can be freed
        Py_DECREF(self)
        self.soul = None
        
        
        
    _cmethodptrs = [PayloadMethodTypes.destroy(_cfree),
                    PayloadMethodTypes.walk(_cwalk),
                    PayloadMethodTypes.walk_back(_cwalk_back),
                    PayloadMethodTypes.collapse(_ccollapse),
                    PayloadMethodTypes.collapse_back(_ccollapse_back)]

    _cmethods = lgs.defineCustomPayloadType(*_cmethodptrs)

 
class NoOpPyPayload(GenericPyPayload):
    def __init__(self, num):
        self.num = num
        super(NoOpPyPayload,self).__init__()
    
    """ Dummy class."""
    def walk_impl(self, state):
        print "%s walking..." % self
        
    def walk_back_impl(self, state):
        print "%s walking back..." % self
        
        
    def to_xml(self):
        return "<NoOpPyPayload type='%s' num='%s'/>" % (self.type, self.num)
    
class Link(EdgePayload):
    name = cproperty(lgs.linkGetName, c_char_p)
    
    def __init__(self):
        self.soul = self._cnew()

    def to_xml(self):
        self.check_destroyed()
        
        return "<Link name='%s'/>" % (self.name)
    
class Street(EdgePayload):
    length = cproperty(lgs.streetGetLength, c_double)
    name   = cproperty(lgs.streetGetName, c_char_p)
    
    def __init__(self,name,length):
        self.soul = self._cnew(name, length)
            
    def to_xml(self):
        self.check_destroyed()
        
        return "<Street name='%s' length='%f' />" % (self.name, self.length)


class TripHop(EdgePayload):
        
    depart = cproperty( lgs.triphopDepart, c_int )
    arrive = cproperty( lgs.triphopArrive, c_int )
    transit = cproperty( lgs.triphopTransit, c_int )
    trip_id = cproperty( lgs.triphopTripId, c_char_p )

    SEC_IN_HOUR = 3600
    SEC_IN_MINUTE = 60

    def to_xml(self):
        return "<TripHop depart='%02d:%02d' arrive='%02d:%02d' transit='%s' trip_id='%s' />" % \
                        (int(self.depart/self.SEC_IN_HOUR), int(self.depart%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        int(self.arrive/self.SEC_IN_HOUR), int(self.arrive%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        self.transit, self.trip_id)
    
class TripHopSchedule(EdgePayload):
    
    calendar = cproperty( lgs.thsGetCalendar, c_void_p, CalendarDay )
    timezone_offset = cproperty( lgs.thsGetTimezoneOffset, c_int )
    
    def __init__(self, hops, service_id, calendar, timezone_offset):
        #TripHopSchedule* thsNew( int *departs, int *arrives, char **trip_ids, int n, ServiceId service_id, CalendarDay* calendar, int timezone_offset );
        
        n = len(hops)
        departs = (c_int * n)()
        arrives = (c_int * n)()
        trip_ids = (c_char_p * n)()
        for i in range(n):
            departs[i] = hops[i][0]
            arrives[i] = hops[i][1]
            trip_ids[i] = c_char_p(hops[i][2])
            
        self.soul = lgs.thsNew(departs, arrives, trip_ids, n, ServiceIdType(service_id), calendar.soul, c_int(timezone_offset) )
    
    n = cproperty(lgs.thsGetN, c_int)
    service_id = cproperty(lgs.thsGetServiceId, c_int)
        
    def triphop(self, i):
        self.check_destroyed()
        
        return self._chop(self.soul, i)
    
    @property
    def triphops(self):
        self.check_destroyed()
        
        hops = []
        for i in range(self.n):
            hops.append( self.triphop( i ) )
        return hops
    
    def to_xml(self):
        self.check_destroyed()
        
        ret = "<TripHopSchedule service_id='%s'>" % self.service_id
        for triphop in self.triphops:
          ret += triphop.to_xml()

        ret += "</TripHopSchedule>"
        return ret
        
    def collapse(self, state):
        self.check_destroyed()
        
        func = lgs.thsCollapse
        func.restype = c_void_p
        func.argtypes = [c_void_p, c_void_p]
        
        triphopsoul = func(self.soul, state.soul)
        
        return TripHop.from_pointer( triphopsoul )

Graph._cnew = lgs.gNew
Graph._cdel = lgs.gDestroy
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)
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


EdgePayload._subtypes = {0:Street,1:TripHopSchedule,2:TripHop,3:Link,4:GenericPyPayload,5:None}
EdgePayload._cget_type = lgs.epGetType
EdgePayload._cwalk = lgs.epWalk
EdgePayload._cwalk_back = lgs.epWalkBack
EdgePayload._ccollapse = ccast(lgs.epCollapse, EdgePayload)
EdgePayload._ccollapse_back = ccast(lgs.epCollapseBack, EdgePayload)

CalendarDay._cnew = lgs.calNew
CalendarDay._cappend_day = ccast(lgs.calAppendDay, CalendarDay)
CalendarDay._crewind = ccast(lgs.calRewind, CalendarDay)
CalendarDay._cfast_forward = ccast(lgs.calFastForward, CalendarDay)
CalendarDay._cday_of_or_after = ccast(lgs.calDayOfOrAfter, CalendarDay)
CalendarDay._cday_of_or_before = ccast(lgs.calDayOfOrBefore, CalendarDay)
CalendarDay._cnext = ccast(lgs.calNextDay, CalendarDay)
CalendarDay._cprev = ccast(lgs.calPreviousDay, CalendarDay)

State._cnew = lgs.stateNew
State._cdel = lgs.stateDestroy
State._ccopy = ccast(lgs.stateDup, State)

ListNode._cdata = ccast(lgs.liGetData, Edge)
ListNode._cnext = ccast(lgs.liGetNext, ListNode)

TripHopSchedule._cdel = lgs.thsDestroy
TripHopSchedule._chop = ccast(lgs.thsGetHop, TripHop)
TripHopSchedule._cwalk = lgs.thsWalk
TripHopSchedule._cwalk_back = lgs.thsWalkBack
#TripHopSchedule._ccollapse = ccast(lgs.thsCollapse, TripHop)
#TripHopSchedule._ccollapse_back = lgs.thsCollapseBack
#TripHopSchedule._collapse_type = TripHop

Street._cnew = lgs.streetNew
Street._cdel = lgs.streetDestroy
Street._cwalk = lgs.streetWalk
Street._cwalk_back = lgs.streetWalkBack

Link._cnew = lgs.linkNew
Link._cdel = lgs.linkDestroy
Link._cwalk = lgs.linkWalk
Link._cwalk_back = lgs.linkWalkBack

GenericPyPayload._cnew = lgs.cpNew
GenericPyPayload._cdel = lgs.cpDestroy
