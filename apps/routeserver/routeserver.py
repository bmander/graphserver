from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State
import time
import sys
import graphserver
from graphserver.util import TimeHelpers

from graphserver.ext.gtfs.gtfsdb import GTFSDatabase

gtfsdb = GTFSDatabase( "/home/brandon/urbanmapping/transit_routing/router/data/chicago.gtfsdb" )

def board_event(vertex1, edge, vertex2):
    event_time = vertex2.payload.time
    trip_id = vertex2.payload.trip_id
    stop_id = vertex1.label
    
    route_desc = list( gtfsdb.execute( "SELECT routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0][0]
    stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
    
    return "Board the %s \n  %s\n  %s"%(route_desc, stop_desc, TimeHelpers.unix_to_localtime( event_time, "America/Chicago" )) 

def alight_event(vertex1, edge, vertex2):
    event_time = vertex1.payload.time
    stop_id = vertex2.label
    
    stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
    
    return "Alight \n  %s\n  %s"%(stop_desc, TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
    
def street_event(vertex1, edge, vertex2):
    return "Walk"
    
event_dispatch = {graphserver.core.TripBoard:board_event,
                  graphserver.core.Alight:alight_event,
                  graphserver.core.Street:street_event}

def string_spt_vertex(vertex, level=0):
    ret = ["  "*level+str(vertex)]
    
    for edge in vertex.outgoing:
        ret.append( "  "*(level+1)+"%s"%(edge) )
        ret.append( string_spt_vertex( edge.to_v, level+1 ) )
    
    return "\n".join(ret)

class RouteServer(Servable):
    def __init__(self, graphdb_filename):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"
    
    def spt(self, label, currtime=None):
        
        currtime = currtime or int(time.time())
        
        spt = self.graph.shortest_path_tree( label, None, State(1,currtime) )
        
        return string_spt_vertex( spt.get_vertex( label ) )
        
    def path(self, origin, dest, currtime):
        
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime) )
        
        vertices, edges = spt.path( dest )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in event_dispatch:
                ret.append( event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
            #ret.append( (str(vertices[i].payload), str(edges[i].payload.__class__), str(vertices[i+1].payload)) )
        
        return "\n".join( [str(x) for x in ret] )
        
if __name__ == '__main__':
    # a fine example node for bart: "ASBY" @ 1233172800
    # for trimet: "10071" @ 1233172800
    
    GDB_FILENAME = "../package_graph/bartheadway.db"
    GDB_FILENAME = "/home/brandon/urbanmapping/transit_routing/router/data/chicago.gdb"
    
    gc = RouteServer(GDB_FILENAME)
    gc.run_test_server()