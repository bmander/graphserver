from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_void_p, cast

from ..gsdll import CShadow, ccast, cproperty, lgs, libc
from .edgepayload import EdgePayload
from .exceptions import VertexNotFoundError
from .list import ListNode
from .state import State
from .walkable import Walkable
from .walkoptions import WalkOptions


class Graph(CShadow):
    size = cproperty(lgs.gSize, c_long)

    def __init__(self, numagencies=1):
        self.soul = self._cnew()
        self.numagencies = numagencies  # a central point that keeps track of how large the list of calendards need ot be in the state variables.

    def destroy(self, free_vertex_payloads=1, free_edge_payloads=1):
        # void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self.check_destroyed()

        self._cdel(self.soul, free_vertex_payloads, free_edge_payloads)
        self.soul = None

    def add_vertex(self, label):
        # Vertex* gAddVertex( Graph* this, char *label );
        self.check_destroyed()

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cadd_vertex(self.soul, label)

    def remove_vertex(self, label, free_edge_payloads=True):
        # void gRemoveVertex( Graph* this, char *label, int free_vertex_payload, int free_edge_payloads );

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cremove_vertex(self.soul, label, free_edge_payloads)

    def get_vertex(self, label):
        # Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cget_vertex(self.soul, label)

    def add_edge(self, fromv, tov, payload):
        # Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()

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

    def set_vertex_enabled(self, vertex_label, enabled):
        # void gSetVertexEnabled( Graph *this, char *label, int enabled );
        self.check_destroyed()

        if isinstance(vertex_label, str):
            vertex_label = vertex_label.encode("utf-8")
        lgs.gSetVertexEnabled(self.soul, vertex_label, enabled)

    @property
    def vertices(self):
        self.check_destroyed()

        count = c_long()
        p_va = lgs.gVertices(self.soul, byref(count))
        verts = []
        arr = cast(p_va, POINTER(c_void_p))  # a bit of necessary voodoo
        for i in range(count.value):
            v = Vertex.from_pointer(arr[i])
            verts.append(v)
        del arr
        libc.free(p_va)
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


class Vertex(CShadow):
    @property
    def label(self):
        self.check_destroyed()
        raw_label = lgs.vGetLabel(c_void_p(self.soul))
        if raw_label:
            if isinstance(raw_label, bytes):
                return raw_label.decode("utf-8")
            return raw_label
        return None

    degree_in = cproperty(lgs.vDegreeIn, c_int)
    degree_out = cproperty(lgs.vDegreeOut, c_int)

    def __init__(self, label):
        if isinstance(label, str):
            label = label.encode("utf-8")
        self.soul = self._cnew(label)

    def destroy(self):
        # void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?

        self.check_destroyed()
        self._cdel(self.soul, 1, 1)
        self.soul = None

    def to_xml(self):
        self.check_destroyed()
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (
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


Vertex._cnew = lgs.vNew
Vertex._cdel = lgs.vDestroy
Vertex._coutgoing_edges = ccast(lgs.vGetOutgoingEdgeList, ListNode)
Vertex._cincoming_edges = ccast(lgs.vGetIncomingEdgeList, ListNode)


class Edge(CShadow, Walkable):
    def __init__(self, from_v, to_v, payload):
        # Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
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

    enabled = cproperty(lgs.eGetEnabled, c_int, setter=lgs.eSetEnabled)


Vertex.edgeclass = Edge


Edge._cnew = lgs.eNew
Edge._cfrom_v = ccast(lgs.eGetFrom, Vertex)
Edge._cto_v = ccast(lgs.eGetTo, Vertex)
Edge._cpayload = ccast(lgs.eGetPayload, EdgePayload)
Edge._cwalk = ccast(lgs.eWalk, State)
Edge._cwalk_back = lgs.eWalkBack


Graph._cnew = lgs.gNew
Graph._cdel = lgs.gDestroy
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)
Graph._cremove_vertex = lgs.gRemoveVertex
Graph._cget_vertex = ccast(lgs.gGetVertex, Vertex)
Graph._cadd_edge = ccast(lgs.gAddEdge, Edge)
