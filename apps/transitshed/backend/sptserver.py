from servable import Servable
from graphserver.graphdb import GraphDatabase
import time
from graphserver import core
from graphserver.core import State, WalkOptions
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.util import TimeHelpers
from contour import travel_time_contour
import json
from rtree import Rtree
from glineenc import encode_pairs
from urllib import urlopen
import yaml

class ContourServer(Servable):
    def __init__(self, settings_filename):
        settings = yaml.load( open( settings_filename ) )
        
        self.home_point = settings['center']
        
        # create cache of osm-node positions
        self.osmdb = OSMDB( settings['osmdb_filename'] )
        self.gtfsdb = GTFSDatabase( settings['gtfsdb_filename'] )
        self.port = settings['port']
        self.node_positions = {}
        self.index = Rtree()
        for node_id, tags, lat, lon in self.osmdb.nodes():
            self.node_positions[node_id] = (lon,lat)
            self.index.add( int(node_id), (lon,lat,lon,lat) )
        
        # incarnate graph from graphdb
        graphdb = GraphDatabase( settings['graphdb_filename'] )
        self.graph = graphdb.incarnate()
    
    def strgraph(self):
        return str(self.graph)
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    
    def _get_important_routes(self, spt):
        # set edge thicknesses
        t0 = time.time()
        print "setting thicknesses"
        spt.set_thicknesses( vertex_label )
        t1 = time.time()
        print "took %s"%(t1-t0)
        
        t0 = time.time()
        print "finding gateway boardings"
        # use thicknesses to determine important boardings
        origin = spt.get_vertex( vertex_label )
        sum_thickness = sum( [edge.thickness for edge in origin.outgoing] )
        
        important_boardings = sorted( filter(lambda x: x.payload.__class__==core.TripBoard and \
                                                        x.thickness/float(sum_thickness) > 0.01, spt.edges),
                                      key = lambda x:x.thickness )
                                               
        for edge in important_boardings:
            print "gateway to %f%% vertices"%(100*edge.thickness/float(sum_thickness))
            print "hop onto trip '%s' at stop '%s', time '%s'"%(edge.to_v.payload.trip_id, edge.from_v.label, edge.to_v.payload.time)
        print "took %ss"%(time.time()-t0)
    
    def _contour(self, vertex_label, starttime, cutoff, step=None, speed=0.85):
        starttime = starttime or time.time()
        
        #=== find shortest path tree ===
        print "Finding shortest path tree"
        t0 = time.time()
        wo = WalkOptions()
        wo.walking_speed = speed
        spt = self.graph.shortest_path_tree( vertex_label, None, State(1,starttime), wo, maxtime=starttime+int(cutoff*1.25) )
        wo.destroy()
        t1 = time.time()
        print "took %s s"%(t1-t0)
        
        #=== cobble together ETA surface ===
        print "Creating ETA surface from OSM points..."
        points = []
        t0 = time.time()
        for vertex in spt.vertices:
            if "osm" in vertex.label:
                x, y = self.node_positions[vertex.label[3:]]
                points.append( (x, y, vertex.payload.time-starttime) )
        t1 = time.time()
        print "Took %s s"%(t1-t0)
        
        spt.destroy()
        
        #=== create contour ===
        print "creating contour...",
        
        t0 = time.time()
        contours = travel_time_contour( points, cutoff=cutoff, cellsize=0.004, fudge=1.7, step=step )
        print "%s sec"%(time.time()-t0)
        
        print "done. here you go..."
        return contours
    
    def label_contour(self, vertex_label, starttime=None, cutoff=1800):
        starttime = starttime or time.time()
        
        return json.dumps( self._contour( vertex_label, starttime, cutoff ) )
        
    def contour(self, lat, lon, year, month, day, hour, minute, second, cutoff, step=60*15, encoded=False, speed=0.85):
        if step is not None and step < 600:
            raise Exception( "Step cannot be less than 600 seconds" )
        
        starttime = TimeHelpers.localtime_to_unix( year, month, day, hour, minute, second, "America/Los_Angeles" )
        
        #=== get osm vertex ==
        print( "getting nearest vertex" )
        
        #find osmid of origin intersection
        t0 = time.time()
        range = 0.001
        bbox = (lon-range, lat-range, lon+range, lat+range)
        candidates = self.index.intersection( bbox )
        vlabel, vlat, vlon, vdist = self.osmdb.nearest_of( lat, lon, candidates )
        t1 = time.time()
        print( "done, took %s seconds"%(t1-t0) )
        
        #vlabel, vlat, vlon, vdist = self.osmdb.nearest_node( lat, lon )
        
        if vlabel is None:
            return json.dumps( "NO NEARBY INTERSECTION" )
        
        print( "found - %s"%vlabel )
        
        contours = self._contour( "osm"+vlabel, starttime, cutoff, step, speed )
        
        if encoded:
            encoded_contours = []
            for contour in contours:
                encoded_contour = []
                for ring in contour:
                    encoded_contour.append( encode_pairs( [(lat,lon) for lon,lat in ring] ) )
                encoded_contours.append( encoded_contour )
                
            contours = encoded_contours
        
        return json.dumps( contours )
        
    def nodes(self):
        return "\n".join( ["%s-%s"%(k,v) for k,v in self.node_positions.items()] )
            
    def nearest_node(self, lat, lon):
        range = 0.005
        bbox = (lon-range, lat-range, lon+range, lat+range)
        print bbox
        print self.index.intersection( bbox )
        
        return json.dumps(self.osmdb.nearest_node( lat, lon ))
        
    def bounds(self):
        return json.dumps(self.osmdb.bounds())
    
    def run_test_server(self):
        Servable.run_test_server(self, self.port)

if __name__=='__main__':    
    from sys import argv

    usage = "python sptserver.py settings_filename"
    
    if len(argv) < 2:
        print usage
        quit()
    
    cserver = ContourServer( argv[1] )
    
    print "bounds are %s"%cserver.bounds()
    
    cserver.run_test_server()
    
