from libgs import libgs
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p, py_object, c_float, c_ulong
from ctypes import Structure, pointer, cast, POINTER, addressof, CFUNCTYPE
from _ctypes import Py_INCREF, Py_DECREF
from time import asctime, gmtime
from time import time as now
import pytz
import calendar
from util import TimeHelpers

"""
Helpers for wrapping c functions in python classes
"""


class _EmptyClass(object):
    pass

def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = _EmptyClass()
    ret.__class__ = cls
    return ret

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

class Vector(Structure):
    _fields_ = [("num_elements", c_int),
                ("num_alloc", c_int),
                ("expand_delta", c_int),
                ("elements", c_void_p)]
                
    def __new__(cls, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = libgs.vecNew( init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        
        pass
        
    def expand(self, amount):
        libgs.vecExpand( addressof(self), amount )
        
    def add(self, element):
        libgs.vecAdd( addressof(self), element )
        
    def get(self, index):
        return libgs.vecGet( addressof(self), index )
        
    def __repr__(self):
        return "<Vector shadow of %s (%d/%d)>"%(hex(addressof(self)),self.num_elements, self.num_alloc)

class Path(Structure):
    """Represents a path of vertices and edges as returned by ShortestPathTree.path()"""
    
    _fields_ = [("vertices", POINTER(Vector)),
                ("edges", POINTER(Vector))]
                
    def __new__(cls, origin, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = libgs.pathNew( origin.soul, init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, origin, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        pass
        
    def addSegment(self, vertex, edge):
        libgs.pathAddSegment( addressof(self), vertex.soul, edge.soul )
        
    def getVertex( self, i ):
        vertex_soul = libgs.pathGetVertex( addressof(self), i )
        
        # reinterpret the error code as an exception
        if vertex_soul is None:
            raise IndexError("%d is out of bounds"%i)
        
        return SPTVertex.from_pointer( vertex_soul )
        
    def getEdge( self, i ):
        edge_soul = libgs.pathGetEdge( addressof(self), i )
        
        # reinterpret the error code as an exception
        if edge_soul is None:
            raise IndexError("%d is out of bounds"%i)
            
        return Edge.from_pointer( edge_soul )
        
    def destroy( self ):
        libgs.pathDestroy( addressof(self) )
        
    @property
    def num_elements(self):
        return self.edges.contents.num_elements
        
    def __repr__(self):
        return "<Path shadowing %s with %d segments>"%(hex(addressof(self)), self.num_elements)

#=============================================================================#
# Core Graph Classes                                                          #
#=============================================================================#

class Graph(CShadow):
    
    size = cproperty(libgs.gSize, c_long)
    
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
        
    def remove_vertex(self, label, free_edge_payloads=True):
        #void gRemoveVertex( Graph* this, char *label, int free_vertex_payload, int free_edge_payloads );
        
        return self._cremove_vertex(self.soul, label, free_edge_payloads)
        
    def get_vertex(self, label):
        #Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)

    def get_vertex_by_index( self, index ):
        libgs.gGetVertexByIndex.restype = c_void_p
        return Vertex.from_pointer( libgs.gGetVertexByIndex( self.soul, index ) )

    def get_edge_by_index( self, index ):
        libgs.gGetEdgeByIndex.restype = c_void_p
        return Edge.from_pointer( libgs.gGetEdgeByIndex( self.soul, index ) )
        
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
        
        libgs.gSetVertexEnabled( self.soul, vertex_label, enabled )
        
    @property
    def vertices(self):
        self.check_destroyed()

        ret = []
        for i in range(self.size):
            ret.append( Vertex.from_pointer( libgs.gGetVertexByIndex( self.soul, i ) ) )

        return ret;
        
    def add_vertices(self, vs):
        a = (c_char_p * len(vs))()
        for i, v in enumerate(vs):
            a[i] = str(v)
        libgs.gAddVertices(self.soul, a, len(vs))
    
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
    
    def shortest_path_tree(self, fromv, tov, initstate, walk_options=None, maxtime=2000000000, hoplimit=1000000, weightlimit=2000000000):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not tov:
            tov = "*bogus^*^vertex*"
        
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime), c_int(hoplimit), c_long(weightlimit) )
            walk_options.destroy()
        else:
            ret = self._cshortest_path_tree( self.soul, fromv, tov, initstate.soul, walk_options.soul, c_long(maxtime), c_int(hoplimit), c_long(weightlimit) )
        
        if ret is None:
	  raise Exception( "Could not create shortest path tree" ) # this shouldn't happen; TODO: more descriptive error

	return ret

    def shortest_path_tree_retro(self, fromv, tov, finalstate, walk_options=None, mintime=0, hoplimit=1000000, weightlimit=2000000000):
        #Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
        self.check_destroyed()
        if not fromv:
            fromv = "*bogus^*^vertex*"
            
        if walk_options is None:
            walk_options = WalkOptions()
            ret = self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime), c_int(hoplimit), c_long(weightlimit) )
            walk_options.destroy()
        else:
            ret = self._cshortest_path_tree_retro( self.soul, fromv, tov, finalstate.soul, walk_options.soul, c_long(mintime), c_int(hoplimit), c_long(weightlimit) )

        if ret is None:
	  raise Exception( "Could not create shortest path tree" ) # this shouldn't happen; TODO: more descriptive error

        return ret

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"
        
class ShortestPathTree(CShadow):
    
    size = cproperty(libgs.sptSize, c_long)
    
    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies #a central point that keeps track of how large the list of calendards need ot be in the state variables.
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
            
    def add_vertex(self, shadow, hop=0):
        #Vertex* sptAddVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()
       
        return SPTVertex.from_pointer( libgs.sptAddVertex( self.soul, shadow.soul, hop ) )
        #return self._cadd_vertex(self.soul, shadow.soul, hop)
        
    def remove_vertex(self, label):
        #void sptRemoveVertex( ShortestPathTree* this, char *label, int free_vertex_payload, int free_edge_payloads );
        
        return self._cremove_vertex(self.soul, label)
        
    def get_vertex(self, label):
        #Vertex* sptGetVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()
        
        return self._cget_vertex(self.soul, label)
        
    def set_parent( self, fromv, tov, payload ):
        self.check_destroyed()
        
        e = self._cset_parent( self.soul, fromv, tov, payload.soul )
        
        if e != None: return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)
    
    @property
    def vertices(self):
        self.check_destroyed()

        ret = []
        for i in range(self.size):
            ret.append( SPTVertex.from_pointer( libgs.sptGetVertexByIndex( self.soul, i ) ) )

        return ret;

    def get_edge_by_index( self, index ):
        libgs.sptGetEdgeByIndex.restype = c_void_p
        return SPTEdge.from_pointer( libgs.sptGetEdgeByIndex( self.soul, index ) )

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

    def to_dot(self):
        self.check_destroyed()
        
        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"
    
    def path(self, destination):
        path_vertices, path_edges = self.path_retro(destination)
        
        if path_vertices is None:
            return (None,None)
        
        path_vertices.reverse()
        path_edges.reverse()
        
        return (path_vertices, path_edges)
        
    def path_retro(self,origin):
        self.check_destroyed()
        
        path_pointer = libgs.sptPathRetro( self.soul, origin )
        
        if path_pointer is None:
	    raise Exception( "A path to %s could not be found"%origin )
            
        path = Path.from_address( path_pointer )
        
        vertices = [path.getVertex( i ) for i in range(path.num_elements+1)]
        edges = [path.getEdge( i ) for i in range(path.num_elements)]
            
        path.destroy()
        
        return (vertices, edges)

class EdgePayload(CShadow, Walkable):
    def __init__(self):
        if self.__class__ == EdgePayload:
            raise "EdgePayload is an abstract type."
    
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None
        
    def __repr__(self):
        self.check_destroyed()
        return "<abstractedgepayload type=%s>" % self.type
    
    type = cproperty(libgs.epGetType, c_int)
    external_id = cproperty(libgs.epGetExternalId, c_long, setter=libgs.epSetExternalId)
    
    @classmethod
    def from_pointer(cls, ptr):
        """ Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None
        
        payloadtype = EdgePayload._subtypes[EdgePayload._cget_type(ptr)]
        ret = instantiate(payloadtype)
        ret.soul = ptr
        return ret

class State(CShadow):
    
    def __init__(self, n_agencies, time=None):
        if time is None:
            time = now()
        self.soul = self._cnew(n_agencies, long(time))
        
    def service_period(self, agency):
        soul = libgs.stateServicePeriod( self.soul, agency )
        return ServicePeriod.from_pointer( soul )
        
    def set_service_period(self, agency, sp):
        if agency>self.num_agencies-1:
            raise Exception("Agency index %d out of bounds"%agency)
        
        libgs.stateSetServicePeriod( self.soul, c_int(agency), sp.soul)
        
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
    
    def __repr__(self):
        self.check_destroyed()  
        
        ret = "<state time=%d weight=%s dist_walked=%s " \
              "num_transfers=%s trip_id=%s stop_sequence=%s>" % \
               (self.time,
               self.weight,
               self.dist_walked,
              self.num_transfers,
               self.trip_id,
               self.stop_sequence)
    
    # the state does not keep ownership of the trip_id, so the state
    # may not live longer than whatever object set its trip_id
    def dangerous_set_trip_id( self, trip_id ):
        libgs.stateDangerousSetTripId( self.soul, trip_id )
        
    time           = cproperty(libgs.stateGetTime, c_long, setter=libgs.stateSetTime)
    weight         = cproperty(libgs.stateGetWeight, c_long, setter=libgs.stateSetWeight)
    dist_walked    = cproperty(libgs.stateGetDistWalked, c_double, setter=libgs.stateSetDistWalked)
    num_transfers  = cproperty(libgs.stateGetNumTransfers, c_int, setter=libgs.stateSetNumTransfers)
    prev_edge      = cproperty(libgs.stateGetPrevEdge, c_void_p, EdgePayload, setter=libgs.stateSetPrevEdge )
    num_agencies     = cproperty(libgs.stateGetNumAgencies, c_int)
    trip_id          = cproperty(libgs.stateGetTripId, c_char_p)
    stop_sequence    = cproperty(libgs.stateGetStopSequence, c_int)
    
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
 
    transfer_penalty = cproperty(libgs.woGetTransferPenalty, c_int, setter=libgs.woSetTransferPenalty)
    turn_penalty = cproperty(libgs.woGetTurnPenalty, c_int, setter=libgs.woSetTurnPenalty)
    walking_speed = cproperty(libgs.woGetWalkingSpeed, c_float, setter=libgs.woSetWalkingSpeed)
    walking_reluctance = cproperty(libgs.woGetWalkingReluctance, c_float, setter=libgs.woSetWalkingReluctance)
    uphill_slowness = cproperty(libgs.woGetUphillSlowness, c_float, setter=libgs.woSetUphillSlowness)
    downhill_fastness = cproperty(libgs.woGetDownhillFastness, c_float, setter=libgs.woSetDownhillFastness)
    hill_reluctance = cproperty(libgs.woGetHillReluctance, c_float, setter=libgs.woSetHillReluctance)
    max_walk = cproperty(libgs.woGetMaxWalk, c_int, setter=libgs.woSetMaxWalk)
    walking_overage = cproperty(libgs.woGetWalkingOverage, c_float, setter=libgs.woSetWalkingOverage)

class Edge(CShadow, Walkable):
    def __init__(self, from_v, to_v, payload):
        #Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
        self.soul = self._cnew(from_v.soul, to_v.soul, payload.soul)
    
    def __repr__(self):
        return "<Edge %s->%s payload:%s>" % (self.from_v, self.to_v, self.payload)
        
    @property
    def from_v(self):
        libgs.eGetFrom.restype = c_long
        return libgs.eGetFrom( self.soul )
        
    @property
    def to_v(self):
        libgs.eGetTo.restype = c_long
        return libgs.eGetTo( self.soul )
        
    @property
    def payload(self):
        return self._cpayload(self.soul)
        
    def walk(self, state, walk_options):
        return self._cwalk(self.soul, state.soul, walk_options.soul)
        
    enabled = cproperty(libgs.eGetEnabled, c_int, setter=libgs.eSetEnabled)

class SPTEdge(CShadow, Walkable):
    def __init__(self, from_v, to_v, payload):
        self.soul = self._cnew(from_v.soul, to_v.soul, payload.soul)
    
    @property
    def from_v(self):
        return SPTVertex.from_pointer( libgs.spteGetFrom( self.soul ) )
        
    @property
    def to_v(self):
        return SPTVertex.from_pointer( libgs.spteGetTo( self.soul ) )
        
    @property
    def payload(self):
        return self._cpayload(self.soul)

    def __repr__(self):
        return "<SPTEdge '%s' -> '%s' via %s>"%(self.from_v.mirror.label, self.to_v.mirror.label, self.payload)
    
class Vertex(CShadow):
    
    label = cproperty(libgs.vGetLabel, c_char_p)
    degree_in = cproperty(libgs.vDegreeIn, c_int)
    degree_out = cproperty(libgs.vDegreeOut, c_int)
    edgeclass = Edge
    
    def __init__(self,graph,label):
        self.soul = self._cnew(graph.soul, label)
        
    def destroy(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?
        
        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None
    
    def __repr__(self):
        self.check_destroyed()
        return "<Vertex degree_out=%s degree_in=%s label=%s>" % (self.degree_out, self.degree_in, self.label)

    def outgoing(self, graph):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, graph)
        
    def incoming(self, graph):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, graph)

    def _edges(self, method, graph, index = -1):
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
                return graph.get_edge_by_index( node.data() )
            e.append( graph.get_edge_by_index( node.data() ) )
            node = node.next
            i = i+1
        if index == -1:
            return e

        return None

    def get_outgoing_edge(self, graph, i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, graph, i)
        
    def get_incoming_edge(self,graph, i):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, graph, i)
        
    def __hash__(self):
        return int(self.soul)
        
class SPTVertex(CShadow):
    
    degree_out = cproperty(libgs.sptvDegreeOut, c_int)
    hop = cproperty(libgs.sptvHop, c_int)
    mirror = cproperty(libgs.sptvMirror, c_void_p, Vertex )
    edgeclass = SPTEdge
    
    def __init__(self,mirror,hop=0):
        self.soul = self._cnew(mirror.soul,hop)
        
    def destroy(self):
        #void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?
        
        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None
    
    def __repr__(self):
        self.check_destroyed()
        return "<SPTVertex degree_out=%s mirror.label=%s>" % (self.degree_out, self.mirror.label)
    
    def outgoing(self, spt):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, spt)
    
    def parent(self, spt):
        return spt.get_edge_by_index( libgs.sptvGetParent( self.soul ) )

    @property
    def state(self):
        self.check_destroyed()
        return self._cstate(self.soul)

    def _edges(self, method, spt, index = -1):
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
                return spt.get_edge_by_index( node.data() )
            e.append( spt.get_edge_by_index( node.data() ) )
            node = node.next
            i = i+1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self,i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, spt, i)
        
    def __hash__(self):
        return int(self.soul)


class ListNode(CShadow):
    
    def data(self):
        libgs.liGetData.restype = c_ulong
        return libgs.liGetData(self.soul)
    
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

#CUSTOM TYPE API
class PayloadMethodTypes:
    """ Enumerates the ctypes of the function pointers."""
    destroy = CFUNCTYPE(c_void_p, py_object)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    
#=============================================================================#
# Edge Type Support Classes                                                   #
#=============================================================================#

class ServicePeriod(CShadow):   

    begin_time = cproperty(libgs.spBeginTime, c_long)
    end_time = cproperty(libgs.spEndTime, c_long)

    def __init__(self, begin_time, end_time, service_ids):
        n, sids = ServicePeriod._py2c_service_ids(service_ids)
        self.soul = self._cnew(begin_time, end_time, n, sids)
    
    @property
    def service_ids(self):
        count = c_int()
        ptr = libgs.spServiceIds(self.soul, byref(count))
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
    
    def datum_midnight(self, timezone_offset):
        return libgs.spDatumMidnight( self.soul, timezone_offset )
    
    def normalize_time(self, timezone_offset, time):
        return libgs.spNormalizeTime(self.soul, timezone_offset, time)
        
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
    head = cproperty( libgs.scHead, c_void_p, ServicePeriod )
       
    def __init__(self):
        self.soul = libgs.scNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    
    def get_service_id_int( self, service_id ):
        if type(service_id)!=type("string"):
            raise TypeError("service_id is supposed to be a string")
        
        return libgs.scGetServiceIdInt( self.soul, service_id );
        
    def get_service_id_string( self, service_id ):
        if type(service_id)!=type(1):
            raise TypeError("service_id is supposed to be an int, in this case")
        
        return libgs.scGetServiceIdString( self.soul, service_id )
        
    def add_period(self, begin_time, end_time, service_ids):
        sp = ServicePeriod( begin_time, end_time, [self.get_service_id_int(x) for x in service_ids] )
        
        libgs.scAddPeriod(self.soul, sp.soul)

    def period_of_or_after(self,time):
        soul = libgs.scPeriodOfOrAfter(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    def period_of_or_before(self,time):
        soul = libgs.scPeriodOfOrBefore(self.soul, time)
        return ServicePeriod.from_pointer(soul)
    
    @property
    def periods(self):
        curr = self.head
        while curr:
            yield curr
            curr = curr.next
            
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
    begin_time = cproperty(libgs.tzpBeginTime, c_long)
    end_time = cproperty(libgs.tzpEndTime, c_long)
    utc_offset = cproperty(libgs.tzpUtcOffset, c_long)
    
    def __init__(self, begin_time, end_time, utc_offset):
        self.soul = libgs.tzpNew(begin_time, end_time, utc_offset)
    
    @property
    def next_period(self):
        return TimezonePeriod.from_pointer( libgs.tzpNextPeriod( self.soul ) )
        
    def time_since_midnight(self, time):
        return libgs.tzpTimeSinceMidnight( self.soul, c_long(time) )
        
    def __getstate__(self):
        return (self.begin_time, self.end_time, self.utc_offset)
    
    def __setstate__(self, state):
        self.__init__(*state)
                
        
class Timezone(CShadow):
    head = cproperty( libgs.tzHead, c_void_p, TimezonePeriod )
    
    def __init__(self):
        self.soul = libgs.tzNew()
        
    def destroy(self):
        self.check_destroyed()
        
        self._cdel(self.soul)
        self.soul = None

    def add_period(self, timezone_period):
        libgs.tzAddPeriod( self.soul, timezone_period.soul)
        
    def period_of(self, time):
        tzpsoul = libgs.tzPeriodOf( self.soul, time )
        return TimezonePeriod.from_pointer( tzpsoul )
        
    def utc_offset(self, time):
        ret = libgs.tzUtcOffset( self.soul, time )
        
        if ret==-360000:
            raise IndexError( "%d lands within no timezone period"%time )
            
        return ret
        
    def time_since_midnight(self, time):
        ret = libgs.tzTimeSinceMidnight( self.soul, c_long(time) )
        
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
    def __init__(self):
        self.soul = self._cnew()

    def __getstate__(self):
        return tuple([])
        
    def __setstate__(self, state):
        self.__init__()
        
    @classmethod
    def reconstitute(self, state, resolver):
        return Link()

    def __str__(self):
        return "<Link 0x%x>"%self.soul
    
class Street(EdgePayload):
    length = cproperty(libgs.streetGetLength, c_double)
    name   = cproperty(libgs.streetGetName, c_char_p)
    rise = cproperty(libgs.streetGetRise, c_float, setter=libgs.streetSetRise)
    fall = cproperty(libgs.streetGetFall, c_float, setter=libgs.streetSetFall)
    slog = cproperty(libgs.streetGetSlog, c_float, setter=libgs.streetSetSlog)
    way = cproperty(libgs.streetGetWay, c_long, setter=libgs.streetSetWay)
    
    def __init__(self,name,length,rise=0,fall=0,reverse_of_source=False):
        self.soul = self._cnew(name, length, rise, fall,reverse_of_source)
            
    def __getstate__(self):
        return (self.name, self.length, self.rise, self.fall, self.slog, self.way, self.reverse_of_source)
        
    def __setstate__(self, state):
        name, length, rise, fall, slog, way, reverse_of_source = state
        self.__init__(name, length, rise, fall, reverse_of_source)
        self.slog = slog
        self.way = way
        
    def __repr__(self):
        return "<Street name='%s' length=%f rise=%f fall=%f way=%ld reverse=%s>"%(self.name, self.length, self.rise, self.fall, self.way,self.reverse_of_source)
        
    @classmethod
    def reconstitute(self, state, resolver):
        name, length, rise, fall, slog, way, reverse_of_source = state
        ret = Street( name, length, rise, fall, reverse_of_source )
        ret.slog = slog
        ret.way = way
        return ret
        
    @property
    def reverse_of_source(self):
        return libgs.streetGetReverseOfSource(self.soul)==1

class Egress(EdgePayload):
    length = cproperty(libgs.egressGetLength, c_double)
    name   = cproperty(libgs.egressGetName, c_char_p)
    
    def __init__(self,name,length):
        self.soul = self._cnew(name, length)
            
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
    end = cproperty(libgs.waitGetEnd, c_long)
    timezone = cproperty(libgs.waitGetTimezone, c_void_p, Timezone)
    
    def __init__(self, end, timezone):
        self.soul = self._cnew( end, timezone.soul )
        
    def __getstate__(self):
        return (self.end, self.timezone.soul)

    def __repr__(self):
        return "<Wait end=%ld>"%(self.end)

class ElapseTime(EdgePayload):
    seconds = cproperty(libgs.elapseTimeGetSeconds, c_long)
    
    def __init__(self, seconds):
        self.soul = self._cnew( seconds )
        
    def __repr__(self):
        self.check_destroyed()
        
        return "<ElapseTime seconds=%ld>"%(self.seconds)
        
    def __getstate__(self):
        return self.seconds
    
    @classmethod
    def reconstitute(cls, state, resolver):
        return cls(state)

class Headway(EdgePayload):
    
    begin_time = cproperty( libgs.headwayBeginTime, c_int )
    end_time = cproperty( libgs.headwayEndTime, c_int )
    wait_period = cproperty( libgs.headwayWaitPeriod, c_int )
    transit = cproperty( libgs.headwayTransit, c_int )
    trip_id = cproperty( libgs.headwayTripId, c_char_p )
    calendar = cproperty( libgs.headwayCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( libgs.headwayTimezone, c_void_p, Timezone )
    agency = cproperty( libgs.headwayAgency, c_int )
    int_service_id = cproperty( libgs.headwayServiceId, c_int )
    
    def __init__(self, begin_time, end_time, wait_period, transit, trip_id, calendar, timezone, agency, service_id):
        if type(service_id)!=type('string'):
            raise TypeError("service_id is supposed to be a string")
            
        int_sid = calendar.get_service_id_int( service_id )
        
        self.soul = libgs.headwayNew(begin_time, end_time, wait_period, transit, trip_id.encode("ascii"),  calendar.soul, timezone.soul, c_int(agency), ServiceIdType(int_sid))
        
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
        
    def __repr__(self):
        return "<Headway begin_time=%d end_time=%d wait_period=%d transit=%d trip_id=%s agency=%d int_service_id=%d>"% \
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
    calendar = cproperty( libgs.tbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( libgs.tbGetTimezone, c_void_p, Timezone )
    agency = cproperty( libgs.tbGetAgency, c_int )
    int_service_id = cproperty( libgs.tbGetServiceId, c_int )
    num_boardings = cproperty( libgs.tbGetNumBoardings, c_int )
    overage = cproperty( libgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
    
    @property
    def service_id(self):
        return self.calendar.get_service_id_string( self.int_service_id )
    
    def add_boarding(self, trip_id, depart, stop_sequence):
        self._cadd_boarding( self.soul, trip_id, depart, stop_sequence )
        
    def get_boarding(self, i):
        trip_id = libgs.tbGetBoardingTripId(self.soul, c_int(i))
        depart = libgs.tbGetBoardingDepart(self.soul, c_int(i))
        stop_sequence = libgs.tbGetBoardingStopSequence(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, depart, stop_sequence)
        
    def get_boarding_by_trip_id( self, trip_id ):
        boarding_index = libgs.tbGetBoardingIndexByTripId( self.soul, trip_id )
        
        if boarding_index == -1:
            return None
        
        return self.get_boarding( boarding_index )
    
    def search_boardings_list(self, time):
        return libgs.tbSearchBoardingsList( self.soul, c_int(time) )
        
    def get_next_boarding_index(self, time):
        return libgs.tbGetNextBoardingIndex( self.soul, c_int(time) )
        
    def get_next_boarding(self, time):
        i = self.get_next_boarding_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_boarding( i )
            
    def __repr__(self):
        return "<TripBoard int_sid=%d sid=%s agency=%d calendar=%s timezone=%s boardings=%s>"%(self.int_service_id, self.calendar.get_service_id_string(self.int_service_id), self.agency, hex(self.calendar.soul),hex(self.timezone.soul),[self.get_boarding(i) for i in range(self.num_boardings)])
        
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
        
        for trip_id, depart, stop_sequence in state['boardings']:
            ret.add_boarding( trip_id, depart, stop_sequence )
            
        return ret
        
    def expound(self):
        boardingstrs = []
        
        for i in range(self.num_boardings):
            trip_id, departure_secs, stop_sequence = self.get_boarding(i)
            boardingstrs.append( "on trip id='%s' at %s, stop sequence %s"%(trip_id, unparse_secs(departure_secs), stop_sequence) )
        
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
    calendar = cproperty( libgs.hbGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( libgs.hbGetTimezone, c_void_p, Timezone )
    agency = cproperty( libgs.hbGetAgency, c_int )
    int_service_id = cproperty( libgs.hbGetServiceId, c_int )
    trip_id = cproperty( libgs.hbGetTripId, c_char_p )
    start_time = cproperty( libgs.hbGetStartTime, c_int )
    end_time = cproperty( libgs.hbGetEndTime, c_int )
    headway_secs = cproperty( libgs.hbGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayBoard calendar=%s timezone=%s agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(hex(self.calendar.soul),
                                                                                                                                          hex(self.timezone.soul),
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
    calendar = cproperty( libgs.haGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( libgs.haGetTimezone, c_void_p, Timezone )
    agency = cproperty( libgs.haGetAgency, c_int )
    int_service_id = cproperty( libgs.haGetServiceId, c_int )
    trip_id = cproperty( libgs.haGetTripId, c_char_p )
    start_time = cproperty( libgs.haGetStartTime, c_int )
    end_time = cproperty( libgs.haGetEndTime, c_int )
    headway_secs = cproperty( libgs.haGetHeadwaySecs, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency, trip_id, start_time, end_time, headway_secs):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency, trip_id, start_time, end_time, headway_secs)
        
    def __repr__(self):
        return "<HeadwayAlight calendar=%s timezone=%s agency=%d service_id=%d trip_id=\"%s\" start_time=%d end_time=%d headway_secs=%d>"%(hex(self.calendar.soul),
                                                                                                                                          hex(self.timezone.soul),
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
    
    def __init__(self):
        self.soul = self._cnew()
        
    def add_crossing_time(self, trip_id, crossing_time):
        libgs.crAddCrossingTime( self.soul, trip_id, crossing_time )
        
    def get_crossing_time(self, trip_id):
        ret = libgs.crGetCrossingTime( self.soul, trip_id )
        if ret==-1:
            return None
        return ret
        
    def get_crossing(self, i):
        trip_id = libgs.crGetCrossingTimeTripIdByIndex( self.soul, i )
        crossing_time = libgs.crGetCrossingTimeByIndex( self.soul, i )
        
        if crossing_time==-1:
            return None
        
        return (trip_id, crossing_time)
    
    @property
    def size(self):
        return libgs.crGetSize( self.soul )
    
    def get_all_crossings(self):
        for i in range(self.size):
            yield self.get_crossing( i )
        
    def __getstate__(self):
        return list(self.get_all_crossings())
        
    @classmethod
    def reconstitute(cls, state, resolver):
        ret = Crossing()
        
        for trip_id, crossing_time in state:
            ret.add_crossing_time( trip_id, crossing_time )
        
        return ret
        
    def expound(self):
        ret = []
        
        ret.append( "Crossing" )
        
        for trip_id, crossing_time in self.get_all_crossings():
            ret.append( "%s: %s"%(trip_id, crossing_time) )
            
        return "\n".join( ret )

    def __repr__(self):
        return "<Crossing %s>"%list(self.get_all_crossings())
        
class TripAlight(EdgePayload):
    calendar = cproperty( libgs.alGetCalendar, c_void_p, ServiceCalendar )
    timezone = cproperty( libgs.alGetTimezone, c_void_p, Timezone )
    agency = cproperty( libgs.alGetAgency, c_int )
    int_service_id = cproperty( libgs.alGetServiceId, c_int )
    num_alightings = cproperty( libgs.alGetNumAlightings, c_int )
    overage = cproperty( libgs.tbGetOverage, c_int )
    
    def __init__(self, service_id, calendar, timezone, agency):
        service_id = service_id if type(service_id)==int else calendar.get_service_id_int(service_id)
        
        self.soul = self._cnew(service_id, calendar.soul, timezone.soul, agency)
        
    def add_alighting(self, trip_id, arrival, stop_sequence):
        libgs.alAddAlighting( self.soul, trip_id, arrival, stop_sequence )
        
    def get_alighting(self, i):
        trip_id = libgs.alGetAlightingTripId(self.soul, c_int(i))
        arrival = libgs.alGetAlightingArrival(self.soul, c_int(i))
        stop_sequence = libgs.alGetAlightingStopSequence(self.soul, c_int(i))
        
        if trip_id is None:
            raise IndexError("Index %d out of bounds"%i)
        
        return (trip_id, arrival, stop_sequence)
    
    @property
    def alightings(self):
        for i in range(self.num_alightings):
            yield self.get_alighting( i )
        
    def search_alightings_list(self, time):
        return libgs.alSearchAlightingsList( self.soul, c_int(time) )
        
    def get_last_alighting_index(self, time):
        return libgs.alGetLastAlightingIndex( self.soul, c_int(time) )
        
    def get_last_alighting(self, time):
        i = self.get_last_alighting_index(time)
        
        if i == -1:
            return None
        else:
            return self.get_alighting( i )
            

    def get_alighting_by_trip_id( self, trip_id ):
        alighting_index = libgs.alGetAlightingIndexByTripId( self.soul, trip_id )
        
        if alighting_index == -1:
            return None
        
        return self.get_alighting( alighting_index )
        
    def __repr__(self):
        return "<TripAlight int_sid=%d agency=%d calendar=%s timezone=%s alightings=%s>"%(self.int_service_id, self.agency, hex(self.calendar.soul),hex(self.timezone.soul),[self.get_alighting(i) for i in range(self.num_alightings)])
        
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
        
        ret = TripAlight(int_sid, calendar, timezone, agency)
        
        for trip_id, arrival, stop_sequence in state['alightings']:
            ret.add_alighting( trip_id, arrival, stop_sequence )
            
        return ret
        
    def expound(self):
        alightingstrs = []
        
        for i in range(self.num_alightings):
            trip_id, arrival_secs, stop_sequence = self.get_alighting(i)
            alightingstrs.append( "on trip id='%s' at %s, stop sequence %s"%(trip_id, unparse_secs(arrival_secs), stop_sequence) )
        
        ret = """TripAlight
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

Graph._cnew = libgs.gNew
Graph._cdel = libgs.gDestroy
Graph._cadd_vertex = ccast(libgs.gAddVertex, Vertex)
Graph._cremove_vertex = libgs.gRemoveVertex
Graph._cget_vertex = ccast(libgs.gGetVertex, Vertex)
Graph._cadd_edge = ccast(libgs.gAddEdge, Edge)
Graph._cshortest_path_tree = ccast(libgs.gShortestPathTree, ShortestPathTree)
Graph._cshortest_path_tree_retro = ccast(libgs.gShortestPathTreeRetro, ShortestPathTree)

ShortestPathTree._cnew = libgs.sptNew
ShortestPathTree._cdel = libgs.sptDestroy
ShortestPathTree._cadd_vertex = ccast(libgs.sptAddVertex, SPTVertex)
ShortestPathTree._cremove_vertex = libgs.sptRemoveVertex
ShortestPathTree._cget_vertex = ccast(libgs.sptGetVertex, SPTVertex)
ShortestPathTree._cset_parent = ccast(libgs.sptSetParent, SPTEdge)

Vertex._cnew = libgs.vNew
Vertex._cdel = libgs.vDestroy
Vertex._coutgoing_edges = ccast(libgs.vGetOutgoingEdgeList, ListNode)
Vertex._cincoming_edges = ccast(libgs.vGetIncomingEdgeList, ListNode)

SPTVertex._cnew = libgs.sptvNew
SPTVertex._cdel = libgs.sptvDestroy
SPTVertex._coutgoing_edges = ccast(libgs.sptvGetOutgoingEdgeList, ListNode)
SPTVertex._cstate = ccast(libgs.sptvState, State)

Edge._cnew = libgs.eNew
Edge._cfrom_v = ccast(libgs.eGetFrom, Vertex)
Edge._cto_v = ccast(libgs.eGetTo, Vertex)
Edge._cpayload = ccast(libgs.eGetPayload, EdgePayload)
Edge._cwalk = ccast(libgs.eWalk, State)
Edge._cwalk_back = libgs.eWalkBack

SPTEdge._cnew = libgs.eNew
SPTEdge._cfrom_v = ccast(libgs.eGetFrom, SPTVertex)
SPTEdge._cto_v = ccast(libgs.eGetTo, SPTVertex)
SPTEdge._cpayload = ccast(libgs.eGetPayload, EdgePayload)
SPTEdge._cwalk = ccast(libgs.eWalk, State)
SPTEdge._cwalk_back = libgs.eWalkBack

EdgePayload._subtypes = {0:Street,1:None,2:None,3:Link,5:None,
                         6:Wait,7:Headway,8:TripBoard,9:Crossing,10:TripAlight,
                         11:HeadwayBoard,12:Egress,13:HeadwayAlight,14:ElapseTime}
EdgePayload._cget_type = libgs.epGetType
EdgePayload._cwalk = libgs.epWalk
EdgePayload._cwalk_back = libgs.epWalkBack

ServicePeriod._cnew = libgs.spNew
ServicePeriod._crewind = ccast(libgs.spRewind, ServicePeriod)
ServicePeriod._cfast_forward = ccast(libgs.spFastForward, ServicePeriod)
ServicePeriod._cnext = ccast(libgs.spNextPeriod, ServicePeriod)
ServicePeriod._cprev = ccast(libgs.spPreviousPeriod, ServicePeriod)

ServiceCalendar._cnew = libgs.scNew
ServiceCalendar._cdel = libgs.scDestroy
ServiceCalendar._cperiod_of_or_before = ccast(libgs.scPeriodOfOrBefore, ServicePeriod)
ServiceCalendar._cperiod_of_or_after = ccast(libgs.scPeriodOfOrAfter, ServicePeriod)

Timezone._cdel = libgs.tzDestroy

State._cnew = libgs.stateNew
State._cdel = libgs.stateDestroy
State._ccopy = ccast(libgs.stateDup, State)

ListNode._cdata = ccast(libgs.liGetData, Edge)
ListNode._cnext = ccast(libgs.liGetNext, ListNode)

Street._cnew = libgs.streetNewElev
Street._cdel = libgs.streetDestroy
Street._cwalk = libgs.streetWalk
Street._cwalk_back = libgs.streetWalkBack

Egress._cnew = libgs.egressNew
Egress._cdel = libgs.egressDestroy
Egress._cwalk = libgs.egressWalk
Egress._cwalk_back = libgs.egressWalkBack

Link._cnew = libgs.linkNew
Link._cdel = libgs.linkDestroy
Link._cwalk = libgs.epWalk
Link._cwalk_back = libgs.linkWalkBack

Wait._cnew = libgs.waitNew
Wait._cdel = libgs.waitDestroy
Wait._cwalk = libgs.waitWalk
Wait._cwalk_back = libgs.waitWalkBack

ElapseTime._cnew = libgs.elapseTimeNew
ElapseTime._cdel = libgs.elapseTimeDestroy
ElapseTime._cwalk = libgs.elapseTimeWalk
ElapseTime._cwalk_back = libgs.elapseTimeWalkBack

TripBoard._cnew = libgs.tbNew
TripBoard._cdel = libgs.tbDestroy
TripBoard._cadd_boarding = libgs.tbAddBoarding
TripBoard._cwalk = libgs.epWalk

Crossing._cnew = libgs.crNew
Crossing._cdel = libgs.crDestroy

TripAlight._cnew = libgs.alNew
TripAlight._cdel = libgs.alDestroy

HeadwayBoard._cnew = libgs.hbNew
HeadwayBoard._cdel = libgs.hbDestroy
HeadwayBoard._cwalk = libgs.epWalk

HeadwayAlight._cnew = libgs.haNew
HeadwayAlight._cdel = libgs.haDestroy
HeadwayAlight._cwalk = libgs.epWalk

WalkOptions._cnew = libgs.woNew
WalkOptions._cdel = libgs.woDestroy

