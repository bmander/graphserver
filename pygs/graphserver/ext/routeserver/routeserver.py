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
from fcgi import WSGIServer
    
from events import BoardEvent, AlightEvent, HeadwayBoardEvent, HeadwayAlightEvent, StreetEvent, StreetTurnEvent

class SelfEncoderHelper(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_jsonable"):
            return obj.to_jsonable()
        return json.JSONEncoder.default(self, obj)

def postprocess_path_raw(vertices, edges):
    retbuilder = []
    
    retbuilder.append("vertices")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex)) )
    
    retbuilder.append("")
    retbuilder.append("states")
    for i, vertex in enumerate(vertices):
        retbuilder.append( "%d %s"%(i, str(vertex.state)) )
    
    retbuilder.append("")
    retbuilder.append("edges")
    for i, edge in enumerate(edges):
        retbuilder.append( "%d %s"%(i, str(edge.payload)) )
        
    return "\n".join(retbuilder)
    
def postprocess_path(vertices, edges, vertex_events, edge_events):
    context = {}
    
    for edge1,vertex1,edge2,vertex2 in zip( [None]+edges, vertices, edges+[None], vertices[1:]+[None,None] ):
        #fire vertex events
        for handler in vertex_events:
            if handler.applies_to( edge1, vertex1, edge2 ):
                event = handler( edge1, vertex1, edge2, context=context )
                if event is not None:
                    yield handler.__class__.__name__, event
        
        #fire edge events
        for handler in edge_events:
            if handler.applies_to( vertex1, edge2, vertex2 ):
                event = handler( vertex1, edge2, vertex2, context=context )
                if event is not None:
                    yield handler.__class__.__name__, event

class RouteServer(Servable):
    def __init__(self, graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders):
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
        self.vertex_events = vertex_events
        self.edge_events = edge_events
        self.vertex_reverse_geocoders = vertex_reverse_geocoders
        
    def bounds(self, jsoncallback=None):
        """returns bounding box that encompases the bounding box from all member reverse geocoders"""
        
        l, b, r, t = None, None, None, None
        
        for reverse_geocoder in self.vertex_reverse_geocoders:
            gl, gb, gr, gt = reverse_geocoder.bounds()
            l = min(l,gl) if l else gl
            b = min(b,gb) if b else gb
            r = max(r,gr) if r else gr
            t = max(t,gt) if t else gt
        
        if jsoncallback is None:
            return json.dumps([l,b,r,t])
        else:
            return "%s(%s)"%(jsoncallback,json.dumps([l,b,r,t]))
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"
    
    def get_vertex_id_raw( self, lat, lon ):
        for reverse_geocoder in self.vertex_reverse_geocoders:
            ret = reverse_geocoder( lat, lon )
            if ret is not None:
                return ret
                
        return None
        
    def get_vertex_id( self, lat, lon ):
        return json.dumps( self.get_vertex_id_raw( lat, lon ) )

    def path(self, 
             origin, 
             dest,
             currtime=None, 
             time_offset=None, 
             transfer_penalty=0, 
             walking_speed=1.0,
             hill_reluctance=1.5,
             turn_penalty=None,
             walking_reluctance=None,
             max_walk=None,
             jsoncallback=None):
        
        performance = {}
        
        if currtime is None:
            currtime = int(time.time())
            
        if time_offset is not None:
            currtime += time_offset
        
        # time path query
        t0 = time.time()
        wo = WalkOptions()
        wo.transfer_penalty=transfer_penalty
        wo.walking_speed=walking_speed
        wo.hill_reluctance=hill_reluctance
        if turn_penalty is not None:
            wo.turn_penalty = turn_penalty
        if walking_reluctance is not None:
            wo.walking_reluctance = walking_reluctance
        if max_walk is not None:
            wo.max_walk = max_walk
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
       
        try:
          vertices, edges = spt.path( dest )
	except Exception, e:
	  return json.dumps( {'error':str(e)} )

        performance['path_query_time'] = time.time()-t0
        
        t0 = time.time()
        narrative = list(postprocess_path(vertices, edges, self.vertex_events, self.edge_events))
        performance['narrative_postprocess_time'] = time.time()-t0
        
        t0 = time.time()
        wo.destroy()
        spt.destroy()
        performance['cleanup_time'] = time.time()-t0
        
        ret = {'narrative':narrative, 'performance':performance}
        
        if jsoncallback is None:
            return json.dumps(ret, indent=2, cls=SelfEncoderHelper)
        else:
            return "%s(%s)"%(jsoncallback,json.dumps(ret, indent=2, cls=SelfEncoderHelper))
            
    def geompath(self, lat1,lon1,lat2,lon2, 
                 currtime=None, 
                 time_offset=None, 
                 transfer_penalty=0, 
                 walking_speed=1.0, 
                 hill_reluctance=1.5,
                 turn_penalty=None,
                 walking_reluctance=None,
                 max_walk=None,
                 jsoncallback=None):
        origin_vertex_label = self.get_vertex_id_raw( lat1, lon1 )
        dest_vertex_label = self.get_vertex_id_raw( lat2, lon2 )
        
        if origin_vertex_label is None:
            raise Exception( "could not find a vertex near (%s,%s)"%(lat1,lon1) )
        if dest_vertex_label is None:
            raise Exception( "could not find a vertex near (%s,%s)"%(lat2,lon2) )
            
        return self.path( origin_vertex_label,
                     dest_vertex_label,
                     currtime,
                     time_offset,
                     transfer_penalty,
                     walking_speed,
                     hill_reluctance,
                     turn_penalty,
                     walking_reluctance,
                     max_walk,
                     jsoncallback )
        
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
        
        return json.dumps(ret, indent=2, cls=SelfEncoderHelper)

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
    if handler_definitions is None:
        return
    
    if handler_type not in handler_definitions:
        return
    
    for handler in handler_definitions[handler_type]:
        handler_class = import_class( handler['name'] )
        handler_instance = handler_class(**handler.get("args", {}))
        
        yield handler_instance
        

from optparse import OptionParser
def main():
    
    # get command line input
    usage = """python routeserver.py graphdb_filename config_filename"""
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--port", dest="port", default="8080",
                      help="Port to serve HTTP, if serving as a standalone server")
    parser.add_option("-s", "--socket", dest="socket", default=None, 
                      help="Socket on which serve fastCGI. If both port and socket are specified, serves as an fastCGI backend.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.print_help()
        exit(-1)
        
    graphdb_filename, config_filename = args
    
    # get narrative handler classes
    handler_definitions = yaml.load( open(config_filename).read() )
    
    edge_events = list(get_handler_instances( handler_definitions, 'edge_handlers' ) )
    vertex_events = list(get_handler_instances( handler_definitions, 'vertex_handlers' ) )
    vertex_reverse_geocoders = list(get_handler_instances( handler_definitions, 'vertex_reverse_geocoders' ) )
    
    # explain to the nice people which handlers were loaded
    print "edge event handlers:"
    for edge_event in edge_events:
        print "   %s"%edge_event
    print "vertex event handlers:"
    for vertex_event in vertex_events:
        print "   %s"%vertex_event
    print "vertex reverse geocoders:"
    for vertex_reverse_geocoder in vertex_reverse_geocoders:
        print "   %s"%vertex_reverse_geocoder
    
    # start up the routeserver
    gc = RouteServer(graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders)
    
    # serve as either an HTTP server or an fastCGI backend
    if options.socket:
        print "Starting fastCGI backend serving at %s"%options.socket
        WSGIServer(gc.wsgi_app(), bindAddress = options.socket).run()
    else:
        gc.run_test_server(port=int(options.port))

if __name__ == '__main__':
    main()
