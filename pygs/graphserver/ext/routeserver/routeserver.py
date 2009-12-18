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
import yaml
import os
    
from events import BoardEvent, AlightEvent, HeadwayBoardEvent, HeadwayAlightEvent, StreetEvent, StreetTurnEvent

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
    
def postprocess_path(vertices, edges, vertex_events, edge_events):
    for edge1,vertex1,edge2,vertex2 in zip( [None]+edges, vertices, edges+[None], vertices[1:]+[None,None] ):
        #fire vertex events
        for handler in vertex_events:
            if handler.applies_to( edge1, vertex1, edge2 ):
                yield handler( edge1, vertex1, edge2 )
        
        #fire edge events
        for handler in edge_events:
            if handler.applies_to( vertex1, edge2, vertex2 ):
                yield handler( vertex1, edge2, vertex2 )

class RouteServer(Servable):
    def __init__(self, graphdb_filename, vertex_events, edge_events):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.vertex_events = vertex_events
        self.edge_events = edge_events
    
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
        
        ret = list(postprocess_path(vertices, edges, self.vertex_events, self.edge_events))
        
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
        
        ret = list(postprocess_path(vertices, edges, self.vertex_events, self.edge_events))
        
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
        
def import_class(handler_class_path_string):
    sys.path.append( os.getcwd() )
    
    handler_class_path = handler_class_path_string.split(".")
    
    class_name = handler_class_path[-1]
    package_name = ".".join(handler_class_path[:-1])
    
    package = __import__(package_name, fromlist=[class_name])
    
    try:
        handler_class = getattr( package, class_name )
    except AttributeError:
        raise AttributeError( "Can't find %s. Only %s"%(class_name, dir(package)) )
    
    return handler_class
    
def get_handler_instances( handler_definitions, handler_type ):
    for handler in handler_definitions[handler_type]:
        handler_class = import_class( handler['name'] )
        handler_instance = handler_class(**handler.get("args", {}))
        
        yield handler_instance
        


def main():
    
    usage = "python routeserver.py graphdb_filename config_filename [port]"
    
    if len(sys.argv) < 2:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    config_filename = sys.argv[2]
    
    if len(sys.argv)==4:
        port = int(sys.argv[3])
    else:
        port = 8080
    
    handler_definitions = yaml.load( open(config_filename).read() )
    
    edge_events = list(get_handler_instances( handler_definitions, 'edge_handlers' ) )
    vertex_events = list(get_handler_instances( handler_definitions, 'vertex_handlers' ) )
    
    print edge_events
    print vertex_events
    
    gc = RouteServer(graphdb_filename, vertex_events, edge_events)
    gc.run_test_server(port=port)

if __name__ == '__main__':
    main()