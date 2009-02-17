from servable import Servable
from graphserver.graphdb import GraphDatabase
import time
from graphserver import core
from graphserver.core import State
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.util import TimeHelpers
from contour import travel_time_contour
import json
from rtree import Rtree
from glineenc import encode_pairs

class ContourServer(Servable):
    def __init__(self, graphdb_filename, osmdb_filename, home_point):
        self.home_point = home_point

        # create cache of osm-node positions
        self.osmdb = OSMDB( osmdb_filename )
        self.node_positions = {}
        self.index = Rtree()
        for node_id, tags, lat, lon in self.osmdb.nodes():
            self.node_positions[node_id] = (lon,lat)
            self.index.add( int(node_id), (lon,lat,lon,lat) )
        
        # incarnate graph from graphdb
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
    
    def strgraph(self):
        return str(self.graph)
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    
    def _contour(self, vertex_label, starttime, cutoff, step=None):
        starttime = starttime or time.time()
        #starttime = 1233172800
        
        t0 = time.time()
        spt = self.graph.shortest_path_tree( vertex_label, None, State(1,starttime) , maxtime=starttime+int(cutoff*1.25) )
        t1 = time.time()
        print t1-t0
        
        #gather points corresponding to osm intersections (x,y,t)
        points = []
        t0 = time.time()
        for vertex in spt.vertices:
            if "osm" in vertex.label:
                x, y = self.node_positions[vertex.label[3:]]
                points.append( (x, y, vertex.payload.time-starttime) )
        t1 = time.time()
        print t1-t0
        
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
        
    def contour(self, lat, lon, year, month, day, hour, minute, second, cutoff, step=60*15, encoded=False):
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
        
        contours = self._contour( "osm"+vlabel, starttime, cutoff, step )
        
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
        
    def index(self):
        fp = open("index.html")
        indexhtml = fp.read()
        fp.close()
       
        fp = open("GMAPS_API_KEY")
        apikey = fp.read()
        fp.close() 

        return indexhtml%(apikey, self.home_point[0], self.home_point[1])
    index.mime = "text/html"
    
    def jquery(self):
        fp = open("jquery.js")
        ret = fp.read()
        fp.close()
        return ret
        
    def bounds(self):
        return json.dumps(self.osmdb.bounds())

if __name__=='__main__':    
    from SETTINGS import GRAPHDB_FILENAME, OSMDB_FILENAME, CENTER
    
    print "Graphdb is %s"%GRAPHDB_FILENAME
    print "OSMdb is %s"%OSMDB_FILENAME
    print "Centerpoint is %s"%(CENTER,)
    
    cserver = ContourServer( GRAPHDB_FILENAME, OSMDB_FILENAME, CENTER )
    cserver.run_test_server()
