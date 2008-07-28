try:
    from graphserver.core import Graph, State
except ImportError:
    from core import Graph, State
from time import time as now

class XMLGraphEngine(object):
    """ Provides a high level API to graph functions, outputing data to XML."""

    def __init__(self, graph):
        self.gg = graph
        
    def __del__(self):
        self.gg.destroy()

    @property
    def graph(self):
        return self.gg

    def parse_init_state(self, numauthorities, time=int(now()), ):
        return State(numauthorities, time)

    def shortest_path_general(self,dir_forward,doubleback,from_v,to_v,**statevars):
        if not self.gg.get_vertex(from_v) and self.gg.get_vertex(to_v):
            raise
        init_state = self.parse_init_state(self.gg.numauthorities, **statevars)
        #print init_state
        try:
            #Throws RuntimeError if no shortest path found.
            if not dir_forward:
                spt = self.gg.shortest_path_tree_retro(from_v, to_v, init_state)
                if doubleback:
                    origin = spt.get_vertex(from_v)
                    if origin is not None:
                        departure_time = origin.payload.time
                        spt = self.gg.shortest_path_tree( from_v, to_v, State(self.gg.numauthorities, departure_time) )
                        vertices, edges = spt.path(to_v)
                    else:
                        vertices, edges = None, None
                else:
                    vertices, edges = spt.path_retro(from_v)
            else:
                spt = self.gg.shortest_path_tree(from_v, to_v, init_state)
                if doubleback:
                    dest = spt.get_vertex(to_v)
                    if dest is not None:
                        arrival_time = dest.payload.time
                        spt = self.gg.shortest_path_tree_retro( from_v, to_v, State(self.gg.numauthorities, arrival_time) )
                        vertices, edges = spt.path_retro(from_v)
                    else:
                        vertices, edges = None, None
                else:
                    vertices, edges = spt.path(to_v)
            ret = ["<?xml version='1.0'?><route>"]
            if vertices is None:
                ret.append("<error>destination unreachable</error>")
            else:
                for i in range(len(edges)):
                    ret.append(vertices[i].to_xml())
                    ret.append(edges[i].to_xml())
                ret.append(vertices[-1].to_xml())
            ret.append("</route>")
            spt.destroy()
            return "".join(ret)
        # TODO
        #except ArgumentError, e:
        #    raise "ERROR: Invalid parameters."
        except RuntimeError, e:
            raise "Couldn't find a shortest path from #{from} to #{to}"
            
    def shortest_path(self, from_v, to_v, **statevars):
        return self.shortest_path_general( True, True, from_v, to_v, **statevars )
            
    def shortest_path_retro(self, from_v, to_v, **statevars):
        return self.shortest_path_general( False, True, from_v, to_v, **statevars )

    def all_vertex_labels(self):
        ret = ["<?xml version='1.0'?>"]
        ret.append("<labels>")
        for v in self.gg.vertices:
            ret.append("<label>%s</label>" % v.label)
        ret.append("</labels>")
        return "".join(ret)

    def outgoing_edges(self, label):
        ret = ["<?xml version='1.0'?>"]
        
        v = self.gg.get_vertex(label)
        
        ret.append("<edges>")
        for e in v.outgoing:
            ret.append("<edge>")
            ret.append("<dest>%s</dest>" % e.to_v.to_xml())
            ret.append("<payload>%s</payload>" %e.payload.to_xml())
            ret.append("</edge>")
        ret.append("</edges>")
        return "".join(ret)

    def walk_edges_general(self, forward_dir, label, **statevars):
        vertex = self.gg.get_vertex( label )
        init_state = self.parse_init_state(self.gg.numauthorities, **statevars)

        ret = ["<?xml version='1.0'?>"]
        ret.append("<vertex>")
        ret.append(init_state.to_xml())
        ret.append("<outgoing_edges>")
        for edge in vertex.outgoing:
            ret.append("<edge>")
            ret.append("<destination label='%s'>" % edge.to_v.label)
            if forward_dir:
                if hasattr( edge.payload, 'collapse' ):
                    collapsed = edge.payload.collapse( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    ret.append(collapsed.walk( init_state ).to_xml())
                else:
                    ret.append("<state/>")
            else:
                if hasattr( edge.payload, 'collapse_back' ):
                    collapsed = edge.payload.collapse_back( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    ret.append(collapsed.walk_back( init_state ).to_xml())
                else:
                    ret.append("<state/>")
            ret.append("</destination>")
            if collapsed:
                ret.append("<payload>%s</payload>" % collapsed.to_xml())
            else:
                ret.append("<payload/>")
            ret.append("</edge>")
        ret.append("</outgoing_edges>")
        ret.append("</vertex>")
        return "".join(ret)
        
    def walk_edges(self, label, **statevars):
        return self.walk_edges_general( True, label, **statevars )
        
    def walk_edges_retro(self, label, **statevars):
        return self.walk_edges_general( False, label, **statevars )
        
    def collapse_edges(self, label, **statevars):
        vertex = self.gg.get_vertex( label )
        init_state = self.parse_init_state(self.gg.numauthorities, **statevars)
        ret = ["<?xml version='1.0'?>"]
        ret.append("<vertex>")
        ret.append(init_state.to_xml())
        ret.append("<outgoing_edges>")
        for edge in vertex.outgoing:
            ret.append("<edge>")
            ret.append("<destination label='%s' />" % edge.to_v.label)
            collapsed = edge.payload.collapse( init_state )
            if collapsed:
                ret.append("<payload>%s</payload>" % collapsed.to_xml())
            else:
                ret.append("<payload/>")
            ret.append("</edge>")
        ret.append("</outgoing_edges>")
        ret.append("</vertex>")
        return "".join(ret)
    
def _test():
    #from pygs.engine import *
    e = XMLGraphEngine()
    
