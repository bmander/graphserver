from ctypes import c_void_p

from ..gsdll import CShadow, ccast, cproperty, lgs
from .graph import Graph
from .state import State
from .walkoptions import WalkOptions


class ContractionHierarchy(CShadow):
    upgraph = cproperty(lgs.chUpGraph, c_void_p, Graph)
    downgraph = cproperty(lgs.chDownGraph, c_void_p, Graph)

    def __init__(self):
        self.soul = lgs.chNew()

    def shortest_path(self, fromv_label, tov_label, init_state, walk_options):
        # GET UPGRAPH AND DOWNGRAPH SPTS
        sptup = self.upgraph.shortest_path_tree(
            fromv_label, None, init_state, walk_options
        )
        sptdown = self.downgraph.shortest_path_tree_retro(
            None, tov_label, State(0, 10000000), walk_options
        )

        # FIND SMALLEST MEETUP VERTEX
        meetup_vertices = []
        for upvv in sptup.vertices:
            downvv = sptdown.get_vertex(upvv.label)
            if downvv is not None:
                meetup_vertices.append(
                    (upvv.state.weight + downvv.state.weight, upvv.label)
                )
        min_meetup = min(meetup_vertices)[1]

        # GET AND JOIN PATHS TO MEETUP VERTEX
        upvertices, upedges = sptup.path(min_meetup)
        downvertices, downedges = sptdown.path_retro(min_meetup)

        edges = upedges + downedges

        ret = [ee.payload for ee in edges]

        sptup.destroy()
        sptdown.destroy()

        return ret


def get_contraction_hierarchies(
    graph: Graph, walk_options: WalkOptions, search_limit: int = 1
) -> ContractionHierarchy:
    """Get the global ContractionHierarchy instance."""
    return ContractionHierarchy.from_pointer(
        lgs.get_contraction_hierarchies(graph.soul, walk_options.soul, search_limit)
    )
