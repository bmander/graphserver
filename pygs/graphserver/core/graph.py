from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_void_p, cast
from typing import TYPE_CHECKING, Any, Optional, Union

from ..gsdll import CShadow, ccast, cproperty, lgs, libc
from .edgepayload import EdgePayload
from .exceptions import VertexNotFoundError
from .list import ListNode
from .state import State
from .walkable import Walkable
from .walkoptions import WalkOptions

if TYPE_CHECKING:
    from .state import State


class Graph(CShadow):
    size = cproperty(lgs.gSize, c_long)  # type: ignore

    def __init__(self, numagencies: int = 1) -> None:
        self.soul = self._cnew()  # type: ignore
        self.numagencies = numagencies  # a central point that keeps track of how large the list of calendards need ot be in the state variables.

    def destroy(
        self, free_vertex_payloads: int = 1, free_edge_payloads: int = 1
    ) -> None:
        # void gDestroy( Graph* this, int free_vertex_payloads, int free_edge_payloads );
        self.check_destroyed()

        self._cdel(self.soul, free_vertex_payloads, free_edge_payloads)  # type: ignore
        self.soul = None

    def add_vertex(self, label: Union[str, bytes]) -> Optional[Any]:
        # Vertex* gAddVertex( Graph* this, char *label );
        self.check_destroyed()

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cadd_vertex(self.soul, label)  # type: ignore

    def remove_vertex(
        self, label: Union[str, bytes], free_edge_payloads: bool = True
    ) -> Optional[Any]:
        # void gRemoveVertex( Graph* this, char *label, int free_vertex_payload, int free_edge_payloads );

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cremove_vertex(self.soul, label, free_edge_payloads)  # type: ignore

    def get_vertex(self, label: Union[str, bytes]) -> Optional[Any]:
        # Vertex* gGetVertex( Graph* this, char *label );
        self.check_destroyed()

        if isinstance(label, str):
            label = label.encode("utf-8")

        return self._cget_vertex(self.soul, label)  # type: ignore

    def add_edge(
        self, fromv: Union[str, bytes], tov: Union[str, bytes], payload: EdgePayload
    ) -> Optional[Any]:
        # Edge* gAddEdge( Graph* this, char *from, char *to, EdgePayload *payload );
        self.check_destroyed()

        if isinstance(fromv, str):
            fromv = fromv.encode("utf-8")
        if isinstance(tov, str):
            tov = tov.encode("utf-8")

        e = self._cadd_edge(self.soul, fromv, tov, payload.soul)  # type: ignore

        if e is not None:
            return e

        if not self.get_vertex(fromv):
            raise VertexNotFoundError(fromv)
        raise VertexNotFoundError(tov)

    def set_vertex_enabled(
        self, vertex_label: Union[str, bytes], enabled: bool
    ) -> None:
        # void gSetVertexEnabled( Graph *this, char *label, int enabled );
        self.check_destroyed()

        if isinstance(vertex_label, str):
            vertex_label = vertex_label.encode("utf-8")
        lgs.gSetVertexEnabled(self.soul, vertex_label, enabled)  # type: ignore

    @property
    def vertices(self) -> list["Vertex"]:
        self.check_destroyed()

        count = c_long()
        p_va = lgs.gVertices(self.soul, byref(count))  # type: ignore
        verts: list["Vertex"] = []
        arr = cast(p_va, POINTER(c_void_p))  # a bit of necessary voodoo
        for i in range(count.value):
            v = Vertex.from_pointer(arr[i])
            if v is not None:
                verts.append(v)  # type: ignore
        del arr
        libc.free(p_va)
        return verts

    def add_vertices(self, vs: list[str]) -> None:
        a = (c_char_p * len(vs))()
        for i, v in enumerate(vs):
            a[i] = str(v).encode("utf-8")
        lgs.gAddVertices(self.soul, a, len(vs))  # type: ignore

    @property
    def edges(self) -> list["Edge"]:
        self.check_destroyed()

        edges = []
        for vertex in self.vertices:
            o = vertex.outgoing
            if not o:
                continue
            for e in o:
                edges.append(e)
        return edges

    def to_dot(self) -> str:
        self.check_destroyed()

        ret = "digraph G {"
        for e in self.edges:
            ret += "    %s -> %s;\n" % (e.from_v.label, e.to_v.label)
        return ret + "}"


class Vertex(CShadow):
    @property
    def label(self) -> Optional[str]:
        self.check_destroyed()
        raw_label = lgs.vGetLabel(self.soul)  # type: ignore
        if raw_label:
            if isinstance(raw_label, bytes):
                return raw_label.decode("utf-8")
            return str(raw_label)
        return None

    degree_in = cproperty(lgs.vDegreeIn, c_int)  # type: ignore
    degree_out = cproperty(lgs.vDegreeOut, c_int)  # type: ignore

    def __init__(self, label: Union[str, bytes]) -> None:
        if isinstance(label, str):
            label = label.encode("utf-8")
        self.soul = self._cnew(label)  # type: ignore

    def destroy(self) -> None:
        # void vDestroy(Vertex* this, int free_vertex_payload, int free_edge_payloads) ;
        # TODO - support parameterization?

        self.check_destroyed()
        self._cdel(self.soul, 1, 1)  # type: ignore
        self.soul = None

    def to_xml(self) -> str:
        self.check_destroyed()
        return "<Vertex degree_out='%s' degree_in='%s' label='%s'/>" % (
            self.degree_out,
            self.degree_in,
            self.label,
        )

    def __str__(self) -> str:
        self.check_destroyed()
        return self.to_xml()

    @property
    def outgoing(self) -> list["Edge"]:
        self.check_destroyed()
        result = self._edges(self._coutgoing_edges)  # type: ignore
        return result if isinstance(result, list) else []

    @property
    def incoming(self) -> list["Edge"]:
        self.check_destroyed()
        result = self._edges(self._cincoming_edges)  # type: ignore
        return result if isinstance(result, list) else []

    def _edges(
        self, method: Any, index: int = -1
    ) -> Union[list["Edge"], Optional["Edge"]]:
        self.check_destroyed()
        e: list["Edge"] = []
        node = method(self.soul)
        if not node:
            if index == -1:
                return e
            else:
                return None
        i = 0
        while node:
            if index != -1 and i == index:
                return node.data(edgeclass=self.edgeclass)  # type: ignore
            e.append(node.data(edgeclass=self.edgeclass))  # type: ignore
            node = node.next
            i = i + 1
        if index == -1:
            return e
        return None

    def get_outgoing_edge(self, i: int) -> Optional["Edge"]:
        self.check_destroyed()
        result = self._edges(self._coutgoing_edges, i)  # type: ignore
        return result if not isinstance(result, list) else None

    def get_incoming_edge(self, i: int) -> Optional["Edge"]:
        self.check_destroyed()
        result = self._edges(self._cincoming_edges, i)  # type: ignore
        return result if not isinstance(result, list) else None

    def __hash__(self) -> int:
        return int(self.soul) if self.soul else 0


Vertex._cnew = lgs.vNew  # type: ignore
Vertex._cdel = lgs.vDestroy  # type: ignore
Vertex._coutgoing_edges = ccast(lgs.vGetOutgoingEdgeList, ListNode)  # type: ignore
Vertex._cincoming_edges = ccast(lgs.vGetIncomingEdgeList, ListNode)  # type: ignore


class Edge(CShadow, Walkable):
    def __init__(self, from_v: "Vertex", to_v: "Vertex", payload: EdgePayload) -> None:
        # Edge* eNew(Vertex* from, Vertex* to, EdgePayload* payload);
        self.soul = self._cnew(from_v.soul, to_v.soul, payload.soul)  # type: ignore

    def __str__(self) -> str:
        return self.to_xml()

    def to_xml(self) -> str:
        return "<Edge>%s</Edge>" % (self.payload)

    @property
    def from_v(self) -> "Vertex":
        return self._cfrom_v(self.soul)  # type: ignore

    @property
    def to_v(self) -> "Vertex":
        return self._cto_v(self.soul)  # type: ignore

    @property
    def payload(self) -> EdgePayload:
        return self._cpayload(self.soul)  # type: ignore

    def walk(self, state: State, walk_options: WalkOptions) -> "State":
        return self._cwalk(self.soul, state.soul, walk_options.soul)  # type: ignore

    enabled = cproperty(lgs.eGetEnabled, c_int, setter=lgs.eSetEnabled)  # type: ignore


Vertex.edgeclass = Edge  # type: ignore


Edge._cnew = lgs.eNew  # type: ignore
Edge._cfrom_v = ccast(lgs.eGetFrom, Vertex)  # type: ignore
Edge._cto_v = ccast(lgs.eGetTo, Vertex)  # type: ignore
Edge._cpayload = ccast(lgs.eGetPayload, EdgePayload)  # type: ignore
Edge._cwalk = ccast(lgs.eWalk, State)  # type: ignore
Edge._cwalk_back = lgs.eWalkBack  # type: ignore


Graph._cnew = lgs.gNew  # type: ignore
Graph._cdel = lgs.gDestroy  # type: ignore
Graph._cadd_vertex = ccast(lgs.gAddVertex, Vertex)  # type: ignore
Graph._cremove_vertex = lgs.gRemoveVertex  # type: ignore
Graph._cget_vertex = ccast(lgs.gGetVertex, Vertex)  # type: ignore
Graph._cadd_edge = ccast(lgs.gAddEdge, Edge)  # type: ignore
