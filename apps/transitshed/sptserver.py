from servable import Servable
from graphserver.graphdb import GraphDatabase
import time
from graphserver import core
from graphserver.core import State
from graphserver.ext.osm.osmdb import OSMDB
from contour import travel_time_contour
import json

class ContourServer(Servable):
    def __init__(self, graphdb_filename, osmdb_filename):

        # create cache of osm-node positions
        self.osmdb = OSMDB( osmdb_filename )
        self.node_positions = {}
        for node_id, tags, lat, lon in self.osmdb.nodes():
            self.node_positions[node_id] = (lon,lat)
        
        # incarnate graph from graphdb
        graphdb = GraphDatabase( graphdb_filename )
        self.graph = graphdb.incarnate()
    
    def strgraph(self):
        return str(self.graph)
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    
    def _contour(self, vertex_label, starttime, cutoff):
        #starttime = starttime or time.time()
        starttime = 1233172800
        
        t0 = time.time()
        spt = self.graph.shortest_path_tree( vertex_label, None, State(1,starttime), maxtime=starttime+int(cutoff*1.25) )
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
        contours = travel_time_contour( points, cutoff=cutoff )
        print "%s sec"%(time.time()-t0)
        
        print "done. here you go..."
        return json.dumps( contours )
    
    def label_contour(self, vertex_label, starttime=None, cutoff=1800):
        starttime = starttime or time.time()
        
        return self._contour( vertex_label, starttime, cutoff )
        
    def contour(self, lat, lon, starttime, cutoff):
        #=== get osm vertex ==
        print( "getting nearest vertex" )
        
        vlabel, vlat, vlon, vdist = self.osmdb.nearest_node( lat, lon )
        
        if vlabel is None:
            return json.dumps( "NO NEARBY INTERSECTION" )
        
        print( "found - %s"%vlabel )
        
        return self._contour( "osm"+vlabel, starttime, cutoff )
        
    def nodes(self):
        return "\n".join( ["%s-%s"%(k,v) for k,v in self.node_positions.items()] )
            
    def nearest_node(self, lat, lon):
        return json.dumps(self.osmdb.nearest_node( lat, lon ))
        
    def index(self):
        fp = open("index.html")
        indexhtml = fp.read()
        fp.close()
       
        fp = open("GMAPS_API_KEY")
        apikey = fp.read()
        fp.close() 

        return indexhtml%apikey 
    index.mime = "text/html"
    
    def jquery(self):
        fp = open("jquery.js")
        ret = fp.read()
        fp.close()
        return ret
        
    def bounds(self):
        return json.dumps(self.osmdb.bounds())

if __name__=='__main__':
    # a fine example node for bart: "ASBY" @ 1233172800
    # for trimet: "10071" @ 1233172800
    
    cserver = ContourServer("streetstrimet.db", "../package_graph/bigportland.sqlite")
    #cserver = ContourServer("streetsbart.db", "../package_graph/bartarea.sqlite")
    cserver.run_test_server()