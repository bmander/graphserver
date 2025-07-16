from ctypes import POINTER, Structure, addressof, byref, c_int, c_long, c_void_p, cast
from typing import Optional

from ..gsdll import CShadow, ccast, cproperty, lgs
from ..vector import Vector
from .edgepayload import EdgePayload
from .exceptions import VertexNotFoundError
from .graph import Edge, Vertex
from .list import ListNode
from .state import State
from .walkoptions import WalkOptions


class SPTEdge(Edge):
    def to_xml(self):
        return "<SPTEdge>%s</SPTEdge>" % (self.payload)


class SPTVertex(CShadow):
    @property
    def label(self):
        self.check_destroyed()
        raw_label = lgs.sptvGetLabel(c_void_p(self.soul))
        if raw_label:
            if isinstance(raw_label, bytes):
                return raw_label.decode("utf-8")
            return raw_label
        return None

    degree_in = cproperty(lgs.sptvDegreeIn, c_int)
    degree_out = cproperty(lgs.sptvDegreeOut, c_int)
    hop = cproperty(lgs.sptvHop, c_int)
    mirror = cproperty(lgs.sptvMirror, c_void_p, Vertex)
    edgeclass = SPTEdge

    def __init__(self, mirror, hop=0):
        self.soul = self._cnew(mirror.soul, hop)

    def destroy(self):
        # void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?

        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None

    def to_xml(self):
        self.check_destroyed()
        return "<SPTVertex degree_out='%s' degree_in='%s' label='%s'/>" % (
            self.degree_out,
            self.degree_in,
            self.label,
        )

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
    def state(self):
        self.check_destroyed()
        return self._cstate(self.soul)

    def _edges(self, method, index=-1):
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
                return node.data(edgeclass=self.edgeclass)
            e.append(node.data(edgeclass=self.edgeclass))
            node = node.next
            i = i + 1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self, i):
        self.check_destroyed()
        return self._edges(self._coutgoing_edges, i)

    def get_incoming_edge(self, i):
        self.check_destroyed()
        return self._edges(self._cincoming_edges, i)

    def __hash__(self):
        return int(self.soul)


class Path(Structure):
    """Represents a path of vertices and edges as returned by ShortestPathTree.path()"""

    _fields_ = [("vertices", POINTER(Vector)), ("edges", POINTER(Vector))]

    def __new__(
        cls, origin: Vertex, init_size: int = 50, expand_delta: int = 50
    ) -> "Path":
        # initiate the Path Struct with a C constructor
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        soul = lgs.pathNew(origin.soul, init_size, expand_delta)

        # wrap an instance of this class around that pointer
        return cls.from_address(soul)

    def __init__(
        self, origin: Vertex, init_size: int = 50, expand_delta: int = 50
    ) -> None:
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        pass

    def addSegment(self, vertex: Vertex, edge: Edge) -> None:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        lgs.pathAddSegment(addressof(self), vertex.soul, edge.soul)

    def getVertex(self, i: int) -> Optional["SPTVertex"]:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        vertex_soul = lgs.pathGetVertex(addressof(self), i)

        # reinterpret the error code as an exception
        if vertex_soul is None:
            raise IndexError("%d is out of bounds" % i)

        return SPTVertex.from_pointer(vertex_soul)

    def getEdge(self, i: int) -> Optional[Edge]:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        edge_soul = lgs.pathGetEdge(addressof(self), i)

        # reinterpret the error code as an exception
        if edge_soul is None:
            raise IndexError("%d is out of bounds" % i)

        return Edge.from_pointer(edge_soul)

    def destroy(self) -> None:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        lgs.pathDestroy(addressof(self))

    @property
    def num_elements(self) -> int:
        return self.edges.contents.num_elements

    def __repr__(self) -> str:
        return "<Path shadowing %s with %d segments>" % (
            hex(addressof(self)),
            self.num_elements,
        )


class ShortestPathTree(CShadow):
    size = cproperty(lgs.sptSize, c_long)

    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies  # a central point that keeps track of how large the list of calendards need ot be in the state variables.

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    def add_vertex(self, shadow, hop=0):
        # Vertex* sptAddVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()

        return self._cadd_vertex(self.soul, shadow.soul, hop)

    def remove_vertex(self, label):
        # void sptRemoveVertex( ShortestPathTree* this, char *label, int free_vertex_payload, int free_edge_payloads );

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cremove_vertex(self.soul, label)

    def get_vertex(self, label):
        # Vertex* sptGetVertex( ShortestPathTree* this, char *label );
        self.check_destroyed()

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cget_vertex(self.soul, label)

    def add_edge(self, fromv, tov, payload):
        # Edge* sptAddEdge( ShortestPathTree* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()

        # Encode strings to bytes for ctypes compatibility in Python 3
        if isinstance(fromv, str):
            fromv = fromv.encode("utf-8")
        if isinstance(tov, str):
            tov = tov.encode("utf-8")

        e = self._cadd_edge(self.soul, fromv, tov, payload.soul)

        if e is not None:
            return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)

    @property
    def vertices(self):
        self.check_destroyed()

        count = c_long()
        p_va = lgs.sptVertices(self.soul, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p))  # a bit of necessary voodoo
        for i in range(count.value):
            v = SPTVertex.from_pointer(arr[i])
            verts.append(v)
        return verts

    @property
    def edges(self):
        self.check_destroyed()

        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o:
                continue
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
            return (None, None)

        path_vertices.reverse()
        path_edges.reverse()

        return (path_vertices, path_edges)

    def path_retro(self, origin):
        self.check_destroyed()

        if isinstance(origin, str):
            origin = origin.encode("utf-8")

        path_pointer = lgs.sptPathRetro(self.soul, origin)

        if path_pointer is None:
            raise Exception("A path to %s could not be found" % origin)

        path = Path.from_address(path_pointer)

        vertices = [path.getVertex(i) for i in range(path.num_elements + 1)]
        edges = [path.getEdge(i) for i in range(path.num_elements)]

        path.destroy()

        return (vertices, edges)


ShortestPathTree._cnew = lgs.sptNew
ShortestPathTree._cdel = lgs.sptDestroy
ShortestPathTree._cadd_vertex = ccast(lgs.sptAddVertex, SPTVertex)
ShortestPathTree._cremove_vertex = lgs.sptRemoveVertex
ShortestPathTree._cget_vertex = ccast(lgs.sptGetVertex, SPTVertex)
ShortestPathTree._cadd_edge = ccast(lgs.sptAddEdge, Edge)


SPTVertex._cnew = lgs.sptvNew
SPTVertex._cdel = lgs.sptvDestroy
SPTVertex._coutgoing_edges = ccast(lgs.sptvGetOutgoingEdgeList, ListNode)
SPTVertex._cincoming_edges = ccast(lgs.sptvGetIncomingEdgeList, ListNode)
SPTVertex._cstate = ccast(lgs.sptvState, State)


SPTEdge._cnew = lgs.eNew
SPTEdge._cfrom_v = ccast(lgs.eGetFrom, SPTVertex)
SPTEdge._cto_v = ccast(lgs.eGetTo, SPTVertex)
SPTEdge._cpayload = ccast(lgs.eGetPayload, EdgePayload)
SPTEdge._cwalk = ccast(lgs.eWalk, State)
SPTEdge._cwalk_back = lgs.eWalkBack


def shortest_path_tree(
    graph,
    fromv,
    tov,
    initstate,
    walk_options=None,
    maxtime=2000000000,
    hoplimit=1000000,
    weightlimit=2000000000,
):
    # Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
    graph.check_destroyed()
    if not tov:
        tov = "*bogus^*^vertex*"

    if isinstance(fromv, str):
        fromv = fromv.encode("utf-8")
    if isinstance(tov, str):
        tov = tov.encode("utf-8")

    if walk_options is None:
        walk_options = WalkOptions()
        ret = ShortestPathTree.from_pointer(
            lgs.gShortestPathTree(
                graph.soul,
                fromv,
                tov,
                initstate.soul,
                walk_options.soul,
                c_long(int(maxtime)),
                c_int(hoplimit),
                c_long(int(weightlimit)),
            )
        )
        walk_options.destroy()
    else:
        ret = ShortestPathTree.from_pointer(
            lgs.gShortestPathTree(
                graph.soul,
                fromv,
                tov,
                initstate.soul,
                walk_options.soul,
                c_long(int(maxtime)),
                c_int(hoplimit),
                c_long(int(weightlimit)),
            )
        )

    if ret is None:
        raise Exception(
            "Could not create shortest path tree"
        )  # this shouldn't happen; TODO: more descriptive error

    return ret


def shortest_path_tree_retro(
    graph,
    fromv,
    tov,
    finalstate,
    walk_options=None,
    mintime=0,
    hoplimit=1000000,
    weightlimit=2000000000,
):
    # Graph* gShortestPathTree( Graph* this, char *from, char *to, State* init_state )
    graph.check_destroyed()
    if not fromv:
        fromv = "*bogus^*^vertex*"

    if isinstance(fromv, str):
        fromv = fromv.encode("utf-8")
    if isinstance(tov, str):
        tov = tov.encode("utf-8")

    if walk_options is None:
        walk_options = WalkOptions()
        ret = ShortestPathTree.from_pointer(
            lgs.gShortestPathTreeRetro(
                graph.soul,
                fromv,
                tov,
                finalstate.soul,
                walk_options.soul,
                c_long(int(mintime)),
                c_int(hoplimit),
                c_long(int(weightlimit)),
            )
        )
        walk_options.destroy()
    else:
        ret = ShortestPathTree.from_pointer(
            lgs.gShortestPathTreeRetro(
                graph.soul,
                fromv,
                tov,
                finalstate.soul,
                walk_options.soul,
                c_long(int(mintime)),
                c_int(hoplimit),
                c_long(int(weightlimit)),
            )
        )

    if ret is None:
        raise Exception(
            "Could not create shortest path tree"
        )  # this shouldn't happen; TODO: more descriptive error

    return ret
