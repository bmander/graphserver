try:
    from graphserver.dll import lgs, free
except ImportError:
    from dll import lgs, free #so I can run this script from the same folder
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p
from ctypes import Structure, pointer, cast, POINTER, addressof
from time import asctime, gmtime
from time import time as now

MEMTRACE = True

import copy
def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = copy._EmptyClass()
    ret.__class__ = cls
    return ret

"""

These classes map C structs to Python Ctypes Structures.

"""

def walkable(cls, walkf, walk_backf):
    walkf.restype = POINTER(State)
    walk_backf.restype = POINTER(State)
    cls._cwalk = walkf
    cls._cwalk_back = walk_backf
    
    def walk(self, state):
        return self._cwalk(self, state).contents
    
    def walk_back(self, state):
        return self._cwalk_back(self, state).contents
    
    cls.walk = walk
    cls.walk_back = walk_back
       
    
def collapsable(cls, collapsef, collapse_backf):
    collapsef.restype = POINTER(cls)
    collapse_backf.restype = POINTER(cls)
    cls._ccollapse = collapsef
    cls._ccollapse_back = collapse_backf
        
    def collapse(self):
        return self._ccollapse(self, state)
    
    def collapse_back(self):
        return lgs._ccollapse_back(self, state)
    
    cls.collapse = collapse
    cls.collapse_back = collapse_back
    
def castpayload(func):
    def meth(self):
        p = func(self)
        if not p:
            return None
        #print "Type = %s" % p.contents.type
        typ = EdgePayloadEnumTypes[p.contents.type]    
        if not typ:
            return None
        return cast(p, POINTER(typ)).contents
    return meth


def cdelete(self, delf):
    try:
        if MEMTRACE:
            print "Freeing %s" % self
        delf(byref(self))
    except: pass

def returntype(type, methods):
    for m in methods:
        m.restype = type
        
def cproperty(cfunc, restype, ptrclass=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    
    cfunc.restype = restype
    cfunc.argtypes = [c_void_p]
    def prop(self):
        ret = cfunc( c_void_p( self.soul ) )
        if ptrclass:
            ret = ptrclass.from_pointer(ret)
        return ret
    return property(prop)

def ccast(func, cls):
    func.restype = c_void_p
    def _cast(self, *args):
        return cls.from_pointer(func(*args))
    return _cast

"""

Type Definitions

"""
EdgePayloadEnumType = c_int
ServiceIdType = c_int

"""

Class Definitions

"""

class Graph():
    _cnew = lgs.gNew
    _cdel = lgs.gDestroy
    _cadd_vertex = lgs.gAddVertex
    _cget_vertex = lgs.gGetVertex
    _cadd_edge = lgs.gAddEdge
    
    def __init__(self):
        self.soul = self._cnew()
        
    @classmethod
    def from_pointer(cls, ptr):
        ret = instantiate(Graph)
        ret.soul = ptr
        
        return ret
        
    def __del__(self):
        #void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self._cdel(self.soul, 1, 1)
    
    def add_vertex(self, label):
        #Vertex* gAddVertex( Graph* this, char *label );
        return self._cadd_vertex(self.soul, label)
        
    def get_vertex(self, label):
        #Vertex* gGetVertex( Graph* this, char *label ) {
        return self._cget_vertex(self.soul, label)
        
    def add_edge( self, fromv, tov, payload ):
        #Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        return self._cadd_edge( self.soul, fromv, tov, payload.soul )
    
    @property
    def vertices(self):
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
        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o: continue
            for e in o:
                edges.append(e)
        return edges    
    
    def shortest_path_tree(self, fromv, tov, initstate):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )        
        return self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul )
        
    def shortest_path_tree_retro(self, fromv, tov, finalstate):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
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

    def shortest_path(self, from_v, to_v, init_state):
        path_vertices = []
        path_edges    = []
   
        spt = self.shortest_path_tree( from_v, to_v, init_state)
        curr = spt.get_vertex( to_v )
    
        print spt.to_dot()
        
        #if the end node wasn't found
        if not curr:
            raise Exception("Node not found.") # TODO

        path_vertices.append(curr)
        incoming = curr.get_incoming_edge(0)
        while incoming:
            path_edges.append(incoming)
            curr = incoming.from_v
            path_vertices.append(curr)
            incoming = curr.get_incoming_edge(0)

        return path_vertices.reverse(), path_edges.reverse()
    
    def shortest_path_retro(from_v, to_v, final_state):
        path_vertices = []
        path_edges    = []
          
        spt = self.shortest_path_tree( from_v, to_v, final_state, False )
        curr = spt.get_vertex( from_v )
        path_vertices.append(curr)

        incoming = curr.edge_in(0)
        while incoming:
            path_edges.append(incoming)
            curr = incoming.from_v
            path_vertices.append(curr)
            incoming = curr.edge_in(0)

        return path_vertices, path_edges

    def to_dot(self):
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"


class CalendarDay():   

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
    
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(CalendarDay)
        ret.soul = ptr
        return ret
    
    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)



class State():
    
    def __init__(self, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(long(time))
    
    def __copy__(self):
        return self._ccopy(self.soul)
    
    def clone(self):
        return self.__copy__()
    
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        ret = "<state time='%s' weight='%s' dist_walked='%s' " \
              "num_transfers='%s' prev_edge_type='%s' prev_edge_name='%s'>" % \
              (asctime(gmtime(self.time)),
               self.weight,
               self.dist_walked,
               self.num_transfers,
               self.prev_edge_type,
               self.prev_edge_name)
        if self.calendar_day_ptr:
            ret += self.calendar_day
        return ret + "</state>"
    
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(State)
        ret.soul = ptr
        return ret
    
    time           = cproperty(lgs.stateGetTime, c_long)
    weight         = cproperty(lgs.stateGetWeight, c_long)
    dist_walked    = cproperty(lgs.stateGetDistWalked, c_double)
    num_transfers  = cproperty(lgs.stateGetNumTransfers, c_int)
    prev_edge_type = cproperty(lgs.stateGetPrevEdgeType, c_int)
    prev_edge_name = cproperty(lgs.stateGetPrevEdgeName, c_char_p)
    calendar_day   = cproperty(lgs.stateCalendarDay, c_void_p, CalendarDay)
    
#returntype(POINTER(State), [lgs.stateDup, lgs.stateNew])
    

class Vertex():
    
    label = cproperty(lgs.vGetLabel, c_char_p)
    
    def __init__(self,label=None):
        if label:
            vNew = lgs.vNew
            vNew.restype =c_void_p
            vNew.argtypes=[c_char_p]
            
            self.soul = vNew(label)
        
    def __del__(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        
        vDestroy = lgs.vDestroy
        vDestroy.argtypes=[c_void_p,c_int,c_int]
        
        vDestroy(self.soul, 1, 1)
        
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = Vertex()
        ret.soul = ptr
        return ret
    
    @property
    def degree_in(self):
        # char* vGetLabel( Vertex* this ) {
        vDegreeIn = lgs.vDegreeIn
        vDegreeIn.restype=c_int
        vDegreeIn.argtypes=[c_void_p]
        
        return vDegreeIn(self.soul)
        
    @property
    def degree_out(self):
        # char* vDegreeOut( Vertex* this ) {
        vDegreeOut = lgs.vDegreeOut
        vDegreeOut.restype=c_int
        vDegreeOut.argtypes=[c_void_p]
        
        return vDegreeOut(self.soul)
    
    def to_xml(self):
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (self.degree_out, self.degree_in, self.label)
    
    def __str__(self):
        return self.to_xml()


    @property
    def outgoing(self):
        return self._edges(self._coutgoing_edges)
        
    @property
    def incoming(self):
        return self._edges(self._cincoming_edges)

    def _edges(self, method, index = -1):
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
        return self._edges(self._coutgoing_edges, i)
        
    def get_incoming_edge(self,i):
        return self._edges(self._cincoming_edges, i)

""" things not implemented after I moved over to the "soul" model

    @property
    @castpayload
    def payload(self):
        return self.payload_ptr
    
    def walk(self, state):
        return cast(lgs.eWalk(self, state), State)
"""

#cdelete(Vertex, lgs.vDestroy)
#returntype(POINTER(Vertex), [lgs.vNew])

class Edge():
    
    def __init__(self, from_v, to_v, payload):
        #Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
        
        eNew = lgs.eNew
        eNew.restype =c_void_p
        eNew.argtypes=[c_void_p, c_void_p, c_void_p]
        
        self.soul = eNew(from_v.soul, to_v.soul, payload.soul)

    
    def __str__(self):
        return "<Edge>%s%s</Edge>" % (self.from_v, self.to_v)

    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(Edge)
        ret.soul = ptr
        return ret
        
    @property
    def from_v(self):
        eGetFrom = lgs.eGetFrom
        eGetFrom.restype=c_void_p
        eGetFrom.argtypes=[c_void_p]
        
        vertexsoul = eGetFrom(self.soul)
        
        return Vertex.from_pointer(vertexsoul)
        
    @property
    def to_v(self):
        eGetTo = lgs.eGetTo
        eGetTo.restype=c_void_p
        eGetTo.argtypes=[c_void_p]
        
        vertexsoul = eGetTo(self.soul)
        
        return Vertex.from_pointer(vertexsoul)
        
    @property
    def payload(self):
        payloadtypes = {0:Street,1:TripHopSchedule,2:TripHop,3:Link,5:None}
        
        eGetPayload = lgs.eGetPayload
        eGetPayload.restype=c_void_p
        eGetPayload.argtypes=[c_void_p]
        
        payloadsoul = eGetPayload(self.soul)
        
        epGetType = lgs.epGetType
        epGetType.restype=c_int
        epGetType.argtypes=[c_void_p]
        
        payloadtype = epGetType(payloadsoul)
        
        return payloadtypes[payloadtype].from_pointer( payloadsoul )
    
#walkable(Edge, lgs.epWalk, lgs.epWalkBack)
#collapsable(Edge, lgs.epCollapse, lgs.epCollapseBack)

#returntype(POINTER(Edge), [lgs.eNew])


class ListNode():
    @property
    def data(self):
        return self._cdata(self.soul)
    
    @property
    def next(self):
        return self._cnext(self.soul)
        
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(ListNode)
        ret.soul = ptr
        return ret

    
class EdgePayload():
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<abstractedgepayload type='%s'/>" % self.type
        
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
            
        ret = instantiate(cls)
        ret.soul = ptr
        return ret


#walkable(EdgePayload, lgs.epWalk, lgs.epWalkBack)
#collapsable(EdgePayload, lgs.epCollapse, lgs.epCollapseBack)
#cdelete(EdgePayload, lgs.epDestroy)

    
class Link(EdgePayload):
    name = cproperty(lgs.linkGetName, c_char_p)
    
    def __init__(self):
        linkNew = lgs.linkNew
        linkNew.restype=c_void_p
        linkNew.argtypes=[]
        
        self.soul = linkNew()

    def to_xml(self):
        return "<link name='%s'/>" % (self.name)
    
#walkable(Link, lgs.linkWalk, lgs.linkWalkBack)
#cdelete(Link, lgs.linkDestroy)
#returntype(POINTER(Link), [lgs.linkNew])

class Street(EdgePayload):
    length = cproperty(lgs.streetGetLength, c_double)
    name   = cproperty(lgs.streetGetName, c_char_p)
    
    def __init__(self,name,length):
        if name and length:
            streetNew = lgs.streetNew
            streetNew.restype=c_void_p
            streetNew.argtypes=[c_char_p, c_double]
            
            self.soul = streetNew(name,length)
        
    #there will be no delete function, because Street is designed to be taken by Graph and deleted alongside it
    
    def to_xml(self):
        return "<street name='%s' length='%f' />" % (self.name, self.length)

#walkable(Street, lgs.streetWalk, lgs.streetWalkBack)
#returntype(POINTER(Street), [lgs.streetNew])


class TripHop(EdgePayload):

    def __init__():
        pass
        
    depart = cproperty( lgs.triphopDepart, c_int )
    arrive = cproperty( lgs.triphopArrive, c_int )
    transit = cproperty( lgs.triphopTransit, c_int )
    trip_id = cproperty( lgs.triphopTripId, c_char_p )

    SEC_IN_HOUR = 3600
    SEC_IN_MINUTE = 60

    def to_xml(self):
        return "<triphop depart='%02d:%02d' arrive='%02d:%02d' transit='%s' trip_id='%s' />" % \
                        (int(self.depart/self.SEC_IN_HOUR), int(self.depart%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        int(self.arrive/self.SEC_IN_HOUR), int(self.arrive%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        self.transit, self.trip_id)
    
#walkable(TripHop, lgs.triphopWalk, lgs.triphopWalkBack)
    
class TripHopSchedule(EdgePayload):
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
        func = lgs.thsGetHop
        func.restype = c_void_p
        func.argtypes = [c_void_p, c_int]
        
        hopsoul = func(self.soul, i)
        
        return TripHop.from_pointer( hopsoul )
    
    @property
    def triphops(self):
        hops = []
        for i in range(self.n):
            hops.append( self.triphop( i ) )
        return hops
    
    def to_xml(self):
        ret = "<triphopschedule service_id='%s'>" % self.service_id
        for triphop in self.triphops:
          ret += triphop.to_xml()

        ret += "</triphopschedule>"
        return ret


#walkable(TripHopSchedule, lgs.thsWalk, lgs.thsWalkBack)
#returntype(POINTER(TripHopSchedule), [lgs.thsNew])


Graph._cnew = lgs.gNew
Graph._cdel = lgs.gDestroy
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)
Graph._cget_vertex = ccast(lgs.gGetVertex, Vertex)
Graph._cadd_edge = ccast(lgs.gAddEdge, Edge)
Graph._cshortest_path_tree = ccast(lgs.gShortestPathTree, Graph)
Graph._cshortest_path_tree_retro = ccast(lgs.gShortestPathTreeRetro, Graph)

Vertex._coutgoing_edges = ccast(lgs.vGetOutgoingEdgeList, ListNode)
Vertex._cincoming_edges = ccast(lgs.vGetIncomingEdgeList, ListNode)

CalendarDay._cnew = lgs.calNew
CalendarDay._cappend_day = ccast(lgs.calAppendDay, CalendarDay)
CalendarDay._crewind = ccast(lgs.calRewind, CalendarDay)
CalendarDay._cfast_forward = ccast(lgs.calFastForward, CalendarDay)
CalendarDay._cday_of_or_after = ccast(lgs.calDayOfOrAfter, CalendarDay)
CalendarDay._cday_of_or_before = ccast(lgs.calDayOfOrBefore, CalendarDay)
CalendarDay._cnext = ccast(lgs.calNextDay, CalendarDay)
CalendarDay._cprev = ccast(lgs.calPreviousDay, CalendarDay)

State._cnew = lgs.stateNew
State._ccopy = ccast(lgs.stateDup, State)

ListNode._cdata = ccast(lgs.liGetData, Edge)
ListNode._cnext = ccast(lgs.liGetNext, ListNode)


EdgePayload._fields_ = [('type', EdgePayloadEnumType)]

Link._fields_ = [('type', EdgePayloadEnumType), ('name',c_char_p)]


Street._fields_ = [('type',   EdgePayloadEnumType),
                   ('name',   c_char_p),
                   ('length', c_double)]

#TripHopSchedule._fields_ = [('type',            c_int),
#                            ('n',               c_int),
#                            ('hops_ptr',        POINTER(TripHop)),
#                            ('service_id',      c_int),
#                            ('calendar',        c_void_p),
#                            ('timezone_offset', c_int)]

# placed here to allow the forward declaration of TripHopSchedule
#TripHop._fields_ = [('type',         EdgePayloadEnumType),
#                    ('depart',       c_int),
#                   ('arrive',       c_int),
#                    ('transit',      c_int),
#                    ('trip_id',      c_char_p),
#                    ('schedule_ptr', POINTER(TripHopSchedule))]

EdgePayloadEnumTypes = [Street,
                        TripHopSchedule,
                        TripHop,
                        Link,
                        None, #ruby value in the code...
                        None]

TripHop._TYPE = EdgePayloadEnumTypes.index(TripHop)
