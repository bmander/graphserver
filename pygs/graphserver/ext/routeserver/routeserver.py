from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
try:
    import json
except ImportError:
    import simplejson as json
    
from events import BoardEvent, AlightEvent, HeadwayBoardEvent, HeadwayAlightEvent, StreetEvent

def postprocess_path_raw(vertices, edges):
    retbuilder = []
    
    retbuilder.append("vertices")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex)) )
    
    retbuilder.append("")
    retbuilder.append("states")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex.payload)) )
    
    retbuilder.append("")
    retbuilder.append("edges")
    for i, edge in enumerate(edges):
        retbuilder.append( "%d %s"%(i, str(edge.payload)) )
        
    return "\n".join(retbuilder)

class RouteServer(Servable):
    def __init__(self, graphdb_filename, event_dispatch):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.event_dispatch = event_dispatch
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"

    def path(self, origin, dest, currtime=None, time_offset=None, transfer_penalty=0, walking_speed=1.0):
        if currtime is None:
            currtime = int(time.time())
            
        if time_offset is not None:
            currtime += time_offset
        
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret.append( self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
        
        spt.destroy()
        
        return json.dumps(ret, indent=2)
        
    def path_retro(self, origin, dest, currtime=None, time_offset=None, transfer_penalty=0, walking_speed=1.0):
        if currtime is None:
            currtime = int(time.time())
            
        if time_offset is not None:
            currtime += time_offset
        
        wo = WalkOptions()
        wo.transfer_penalty = transfer_penalty
        wo.walking_speed = walking_speed
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret.append( self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
        
        spt.destroy()
        
        return json.dumps(ret, indent=2)

    def path_raw(self, origin, dest, currtime=None):
        if currtime is None:
            currtime = int(time.time())
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = postprocess_path_raw(vertices, edges)
    
        spt.destroy()
        
        return ret
        
    def path_raw_retro(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree_retro( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path_retro( origin )
        
        ret = postprocess_path_raw(vertices, edges)

        spt.destroy()
        
        return ret
            
import sys

def main():
    usage = "python routeserver.py graphdb_filename gtfsdb_filename [port]"
    
    if len(sys.argv) < 2:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    gtfsdb_filename = sys.argv[2]
    
    if len(sys.argv)==4:
        port = int(sys.argv[3])
    else:
        port = 8080
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
        
    event_dispatch = {graphserver.core.TripBoard:BoardEvent(gtfsdb),
                      graphserver.core.Alight:AlightEvent(gtfsdb),
                      graphserver.core.Street:StreetEvent(),
                      graphserver.core.HeadwayBoard:HeadwayBoardEvent(gtfsdb),
                      graphserver.core.HeadwayAlight:HeadwayAlightEvent(gtfsdb)}
    
    gc = RouteServer(graphdb_filename, event_dispatch)
    gc.run_test_server(port=port)

if __name__ == '__main__':
    main()