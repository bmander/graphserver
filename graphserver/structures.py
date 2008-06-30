try:
    from graphserver.dll import lgs, free
except ImportError:
    from dll import lgs, free #so I can run this script from the same folder
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p
from ctypes import Structure, pointer, cast, POINTER, addressof
from time import asctime, gmtime
from time import time as now

MEMTRACE = True

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

"""

Type Definitions

"""
EdgePayloadEnumType = c_int
ServiceIdType = c_int

"""

Class Definitions

"""

class Graph(Structure):
    _fields_ = [('vertices_hash_ptr', c_void_p)]

    def __new__(cls):
        return lgs.gNew().contents
    
    def __del__(self):
        cdelete(self, lgs.gDestroy)
    
    def add_vertex(self, vertex_name):
        lgs.gAddVertex(self.c_ref, c_char_p(vertex_name))
    
    def get_vertex(self, key):
        p = cast(lgs.gGetVertex(self.c_ref, c_char_p(key)), POINTER(Vertex))
        if p:
            return p.contents
        return None 

    @property
    def vertices(self):
        count = c_int()
        p_va = lgs.gVertices(self.c_ref, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p)) # a bit of necessary voodoo
        for i in range(count.value):
            v = cast(arr[i], POINTER(Vertex)).contents
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

    
    def add_edge(self, from_key, to_key, payload):
        e = lgs.gAddEdge(self.c_ref, c_char_p(from_key), c_char_p(to_key), byref(payload))
        e = cast(e, POINTER(Edge)).contents
        assert(addressof(e.payload) == addressof(payload))
        return e
    
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
    
    def shortest_path(self, from_v, to_v, init_state):
        path_vertices = []
        path_edges    = []
   
        spt = self.shortest_path_tree( from_v, to_v, init_state, True )
        curr = spt.get_vertex( to_v )
    
        print spt.to_dot()
        
        #if the end node wasn't found
        if not curr:
            raise "Node not found." # TODO

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

    @property
    def c_ref(self):
        return byref(self)

    def to_dot(self):
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"

returntype(POINTER(Graph), [lgs.gNew, lgs.gShortestPathTree, lgs.gShortestPathTreeRetro])


class CalendarDay(Structure):   
    def __new__(self, begin_time, end_time, service_ids, daylight_savings):
        n, sids = CalendarDay._py2c_service_ids(service_ids)
        return lgs.calNew(c_long(begin_time), c_long(end_time), 
                           c_int(n), sids, c_int(daylight_savings)).contents
    
    def __init__(self, begin_time, end_time, service_ids, daylight_savings):
        pass
        
    def append_day(self, begin_time, end_time, service_ids, daylight_savings):
        n, sids = self._py2c_service_ids(service_ids)
        return lgs.calAppendDay(self.c_ref, c_long(begin_time), c_long(end_time), 
                                     c_int(n), sids, c_int(daylight_savings))
    
    @property
    def service_ids(self):
        ids = []
        for i in range(self.n_service_ids):
            ids.append(self.service_ids_ptr[i])
        return ids
    
    @property
    def previous(self):
        if self.prev_day_ptr:
            return self.prev_day_ptr.contents
        return None

    @property
    def next(self):
        if self.next_day_ptr:
            return self.next_day_ptr.contents
        else: return None

    def rewind(self):
        return lgs.calRewind(self.c_ref).contents
        
    def fast_forward(self):
        return lgs.calFastForward(self.c_ref).contents
    
    def day_of_or_after(self, time):
        return lgs.calDayOfOrAfter(self.c_ref, c_long(time))
        
    def day_of_or_before(self, time):
        return lgs.calDayOfOrBefore(self.c_ref, c_long(time))
    
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<calendar begin_time='%s' end_time='%s' service_ids='%s'/>" % \
            (asctime(gmtime(self.begin_time)), asctime(gmtime(self.end_time)), 
             ",".join(map(str, self.service_ids)))
    
    @property
    def c_ref(self):
        return byref(self)
    
    @staticmethod
    def _py2c_service_ids(service_ids):
        ns = len(service_ids)
        asids = (ServiceIdType * ns)()
        for i in range(ns):
            asids[i] = ServiceIdType(service_ids[i])
        return (ns, asids)

returntype(POINTER(CalendarDay), [lgs.calFastForward, lgs.calRewind, lgs.calDayOfOrAfter, 
                                  lgs.calDayOfOrBefore, lgs.calAppendDay, lgs.calNew])


class State(Structure):
    def __new__(self, time=None, 
                 weight=None, 
                 dist_walked=None,
                 num_transfers=None):
        if not time:
            time = int(now())
        return lgs.stateNew(c_long(time)).contents
    
    def __init__(self, time=None, 
                 weight=None, 
                 dist_walked=None,
                 num_transfers=None):
        pass
    
    def clone(self):
        return lgs.stateDup(byref(self))
    
    @property
    def calendar_day(self):
        if self.calendar_day_ptr:
            return self.calendar_day_ptr.contents
        return None
    
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
    
returntype(POINTER(State), [lgs.stateDup, lgs.stateNew])
    

class Vertex(Structure):    
    def __new__(self, label):
        v = lgs.vNew(c_char_p(label)).contents
        return v
    
    def __init__(self, label):
        pass
    
    def __str__(self):
        return self.to_xml()
    
    def to_xml(self):
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (self.degree_out, self.degree_in, self.label)

    @property
    def outgoing(self):
        return self._edges(lgs.vGetOutgoingEdgeList)
        
    @property
    def incoming(self):
        return self._edges(lgs.vGetIncomingEdgeList)

    def _edges(self, method, index = -1):
        e = []
        edges = method(byref(self))
        if not edges: 
            if index == -1:
                return e
            else: 
                print "return none1"
                return None
        edges = edges.contents
        i = 0
        while edges:
            if index != -1 and i == index:
                return edges.data
            e.append(edges.data)
            edges = edges.next
            i = i+1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self,i):
        return self._edges(lgs.vGetOutgoingEdgeList, i)
        
    def get_incoming_edge(self,i):
        return self._edges(lgs.vGetIncomingEdgeList, i)
    
    @property
    @castpayload
    def payload(self):
        return self.payload_ptr
    
    def walk(self, state):
        return cast(lgs.eWalk(self, state), State)

#cdelete(Vertex, lgs.vDestroy)
returntype(POINTER(Vertex), [lgs.vNew])

class Edge(Structure):
    def __new__(cls, from_v, to_v, payload):
        return lgs.eNew(byref(from_v), byref(to_v), byref(payload)).contents
    
    def __init__(self, from_v, to_v, payload):
        pass 
    
    def __str__(self):
        return "<Edge>%s%s</Edge>" % (self.from_v, self.to_v)
    
    @property
    def from_v(self):
        return self.from_ptr.contents
    
    @property
    def to_v(self):
        return self.to_ptr.contents
    
    
    @property
    @castpayload
    def payload(self):
        return self.payload_ptr
    
walkable(Edge, lgs.epWalk, lgs.epWalkBack)
collapsable(Edge, lgs.epCollapse, lgs.epCollapseBack)

returntype(POINTER(Edge), [lgs.eNew])


class ListNode(Structure):
    @property
    def data(self):
        if self.data_ptr:
            return self.data_ptr.contents
        else: return None
    
    @property
    def next(self):
        if self.next_ptr:
            return self.next_ptr.contents
        else: return None

returntype(POINTER(ListNode), [lgs.vGetIncomingEdgeList, lgs.vGetOutgoingEdgeList])
    
class EdgePayload(Structure):
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<abstractedgepayload type='%s'/>" % self.type


walkable(EdgePayload, lgs.epWalk, lgs.epWalkBack)
collapsable(EdgePayload, lgs.epCollapse, lgs.epCollapseBack)
#cdelete(EdgePayload, lgs.epDestroy)

    
class Link(Structure):
    def __new__(cls):
        return lgs.linkNew().contents

    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<link name='%s' type='%s'/>" % (self.name, self.type)
    
walkable(Link, lgs.linkWalk, lgs.linkWalkBack)
#cdelete(Link, lgs.linkDestroy)
returntype(POINTER(Link), [lgs.linkNew])

class Street(Structure):
    def __new__(cls,name,l):
        return lgs.streetNew(c_char_p(name), c_double(l)).contents

    def __init__(self, name, length):
        pass

    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<street name='%s' length='%f' />" % (self.name, self.length)


walkable(Street, lgs.streetWalk, lgs.streetWalkBack)
returntype(POINTER(Street), [lgs.streetNew])


class TripHop(Structure):
    _TYPE = 0 # set later
    def __init__(self, type, depart, arrive, transit, trip_id, schedule=None):
        self.type = self._TYPE
        self.depart = c_int(depart)
        self.arrive = c_int(arrive)
        self.transit = c_int(arrive - depart)
        self.trip_id = c_char_p(trip_id)
        if schedule:
            self.schedule = pointer(schedule)


    SEC_IN_HOUR = 3600
    SEC_IN_MINUTE = 60
    
    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        return "<triphop depart='%02d:%02d' arrive='%02d:%02d' transit='%s' trip_id='%s' />" % \
                        (int(self.depart/self.SEC_IN_HOUR), int(self.depart%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        int(self.arrive/self.SEC_IN_HOUR), int(self.arrive%self.SEC_IN_HOUR/self.SEC_IN_MINUTE),
                        self.transit, self.trip_id)
    
walkable(TripHop, lgs.triphopWalk, lgs.triphopWalkBack)
    
class TripHopSchedule(Structure):
    def __new__(cls, hops, service_id, calendar, timezone_offset):
        n = len(hops)
        departs = (c_int * n)()
        arrives = (c_int * n)()
        trip_ids = (c_char_p * n)()
        if isinstance(hops[0], TripHop):
            for i in range(n):
                departs[i] = hops[i].depart
                arrives[i] = hops[i].arrive
                trip_ids[i] = hops[i].trip_id
        elif isinstance(hops[0], (tuple,list)):
            for i in range(n):
                departs[i] = hops[i][0]
                arrives[i] = hops[i][1]
                trip_ids[i] = c_char_p(hops[i][2])
        else:
            raise "Unknown hops initializing type."
            
        return lgs.thsNew(departs, arrives, trip_ids, n, 
                    ServiceIdType(service_id), byref(calendar), c_int(timezone_offset) ).contents

    def __init__(self, hops, service_id, calendar, timezone_offset):
        pass
    
    @property
    def triphops(self):
        hops = []
        for i in range(self.n):
            hops.append(self.hops_ptr[i])
        return hops
        
    def __str__(self):
        return self.to_xml()
    
    def to_xml(self):
        ret = "<triphopschedule service_id='%s'>" % self.service_id
        for triphop in self.triphops:
          ret += triphop.to_xml()

        ret += "</triphopschedule>"
        return ret


walkable(TripHopSchedule, lgs.thsWalk, lgs.thsWalkBack)
returntype(POINTER(TripHopSchedule), [lgs.thsNew])

CalendarDay._fields_ = [('begin_time',      c_long),
                        ('end_time',        c_long),
                        ('n_service_ids',   c_int),
                        ('service_ids_ptr', POINTER(ServiceIdType)),
                        ('daylight_savings',c_int),
                        ('prev_day_ptr',    POINTER(CalendarDay)),
                        ('next_day_ptr',    POINTER(CalendarDay))]

State._fields_ = [('time',            c_long),
                  ('weight',          c_long),
                  ('dist_walked',     c_double),
                  ('num_transfers',   c_int),
                  ('prev_edge_type',  EdgePayloadEnumType),
                  ('prev_edge_name',  c_char_p),
                  ('calendar_day_ptr',POINTER(CalendarDay))]

Edge._fields_ = [('from_ptr', POINTER(Vertex)),
                 ('to_ptr', POINTER(Vertex)),
                 ('payload_ptr', POINTER(EdgePayload))]

EdgePayload._fields_ = [('type', EdgePayloadEnumType)]

Link._fields_ = [('type', EdgePayloadEnumType), ('name',c_char_p)]

Vertex._fields_ = [('degree_out', c_int),
                   ('degree_in', c_int),
                   ('outgoing_ptr', POINTER(ListNode)),
                   ('incoming_ptr', POINTER(ListNode)),
                   ('label', c_char_p),
                   ('payload_ptr', POINTER(EdgePayload))]

ListNode._fields_ = [('data_ptr', POINTER(Edge)),
            ('next_ptr', POINTER(ListNode))]

Street._fields_ = [('type', EdgePayloadEnumType),('name', c_char_p),('length', c_double)]

TripHopSchedule._fields_ = [('type', c_int),('n',c_int),('hops_ptr',POINTER(TripHop)),
                            ('service_id',c_int),('calendar',c_void_p),('timezone_offset', c_int)]

# placed here to allow the forward declaration of TripHopSchedule
TripHop._fields_ = [('type', EdgePayloadEnumType),('depart',c_int),('arrive',c_int),
                    ('transit',c_int),('trip_id',c_char_p),('schedule_ptr', POINTER(TripHopSchedule))]

EdgePayloadEnumTypes = [Street,
                        TripHopSchedule,
                        TripHop,
                        Link,
                        None, #ruby value in the code...
                        None]

TripHop._TYPE = EdgePayloadEnumTypes.index(TripHop)




def _test():
    _test_calendar()
    _test_vertex()
    _test_edge()
    _test_street()
    _test_triphop()
    _test_triphop_schedule()
    _test_graph()
    print "\nAssertions passed.\n"
    
def _test_graph():
    g = Graph()
    g.add_vertex("home")
    g.add_vertex("work")
    s = Street( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    assert(g.get_vertex("home").label == 'home')
    assert(g.get_vertex("work").label == 'work')
    assert(s.name == "helloworld")
    assert(s.length == 1)
    assert(isinstance(e.payload, Street))
    assert(e.payload.name == "helloworld")
    assert(e.from_v.label == "home")
    assert(str(e) == 
           """<Edge><Vertex degree_out='1' degree_in='0' label='home'/>"""
           """<Vertex degree_out='0' degree_in='1' label='work'/></Edge>""")
    assert(e.to_v.label == "work")
    assert(len(g.vertices) == 2)
    assert(g.vertices[0].label == 'home')
    
    print g.shortest_path("home", "work", State())
    
    
    #l = Link()
    x = g.add_edge("work", "home", Link())
    assert(x.payload.name == "LINK")
    print x.payload
    
    
    print "Okay... dumping the vertices"
    for v in g.vertices:
        print v    
    
    assert(g)
    
def _test_triphop_schedule():
    hops = [TripHop(1, 0, 1*3600, 1, "Foo to Bar", schedule=None), 
                           TripHop(1, 1*3600, 2*3600, 1, "Bar to Cow", schedule=None)]
    
    # using hop objects
    ths = TripHopSchedule(hops, 1, CalendarDay(0, 1*3600*24, [1,2], 0), 0)
    assert(len(ths.triphops) == 2)
    assert(ths.triphops[0].trip_id == 'Foo to Bar')
    # using a tuple
    ths = TripHopSchedule([(0,1*3600,'Foo to Bar'),
                           (1*3600,2*3600,'Bar to Cow')], 1, CalendarDay(0, 1*3600*24, [1,2], 0), 0)
    assert(ths.triphops[0].trip_id == 'Foo to Bar')
    assert(len(ths.triphops) == 2)
    print ths
    
def _test_triphop():
    th = TripHop(1, 0, 1*3600, 1, "Foo to Bar", schedule=None)
    print th

def _test_street():
    x = lgs.streetNew(c_char_p("foo"), c_double(1.2)).contents
    print "API %s" % x
    x = Street("mystreet", 1.1)
    print "%s" % x

def _test_list_node():
    l = ListNode()
    
def _test_edge():
    ep = EdgePayload()
    e = Edge(Vertex("home"),Vertex("work"), ep)
    print e

def _test_vertex():
    v = Vertex("home")
    v.payload_ptr = pointer(EdgePayload(1))
    assert(v.label == "home")
    assert(len(v.incoming) == 0)
    assert(len(v.outgoing) == 0)
    print v

def _test_calendar():
    c = CalendarDay(0, 1*3600*24, [1,2], 0)
    assert(c.begin_time == 0)
    assert(c.end_time == 1*3600*24)
    assert(len(c.service_ids) == 2)
    assert(c.service_ids == [1,2])
    print c
    print c.append_day(c.end_time, c.end_time+1*3600*24, [3,4,5], 0)
    assert(c.next.service_ids == [3,4,5])
    print c.next
    assert(c.previous == None)
    assert(addressof(c.next.previous)== addressof(c))
    assert(addressof(c.fast_forward())== addressof(c.next))
    assert(addressof(c.next.rewind())== addressof(c))
    
    return c
    
if __name__ == '__main__':
    _test()