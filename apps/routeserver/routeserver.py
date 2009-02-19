from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
import json

class RouteServer(Servable):
    def __init__(self, graphdb_filename, event_dispatch):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.event_dispatch = event_dispatch
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"

    def path(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = []
        for i in range(len(edges)):
            edgetype = edges[i].payload.__class__
            if edgetype in self.event_dispatch:
                ret.append( self.event_dispatch[ edges[i].payload.__class__ ]( vertices[i], edges[i], vertices[i+1] ) )
        
        spt.destroy()
        
        return json.dumps(ret)

    def path_raw(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = "\n".join([str(x) for x in vertices]) + "\n\n" + "\n".join([str(x) for x in edges])

        spt.destroy()
        
        return ret
            
import sys
if __name__ == '__main__':
    usage = "python routeserver.py graphdb_filename gtfsdb_filename"
    
    if len(sys.argv) < 2:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    gtfsdb_filename = sys.argv[2]
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )

    def board_event(vertex1, edge, vertex2):
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label
        
        route_desc = list( gtfsdb.execute( "SELECT routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0][0]
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        loc = (lat,lon)
        return (what, where, when, loc)

    def alight_event(vertex1, edge, vertex2):
        event_time = vertex1.payload.time
        stop_id = vertex2.label
        
        stop_desc = list( gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, "America/Chicago" ))
        loc = (lat,lon)
        return (what, where, when, loc)
        
    def street_event(vertex1, edge, vertex2):
        return ("Walk", "", "", None)
        
    event_dispatch = {graphserver.core.TripBoard:board_event,
                      graphserver.core.Alight:alight_event,
                      graphserver.core.Street:street_event}
    
    gc = RouteServer(graphdb_filename, event_dispatch)
    gc.run_test_server()