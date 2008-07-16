"""Here's a little example whereby a shortest path tree is generated for the San Francisco area starting at the node "65287655",
   which corresponds to an intersection near the Presidio. The output is a text file where each line represents a branch in the 
   shortest path tree. The line takes the format STARTING_VERTEX:ENDING_VERTEX:LENGTH:x1 y1,x2 y2..."""
   
   
import time
from pygs.ext.osm.osm import OSM, Node, Way
from pygs.graphserver import Graph, Street, State
from pygs.ext.osm.load_osm import add_osm_to_graph
from pyproj import Proj

def main():
    #print get_osm_xml( -122.33, 47.66, -122.31, 47.68 )
    utmzone10 = Proj(init='epsg:26910')
 
    g = Graph()
    osm = OSM("sf.osm")
    
    add_osm_to_graph(g, osm, utmzone10, {'cycleway':0.3333, 'footway':0.5, 'motorway':100} )
        
    random_vertex_label = "65287655" #one end of Pitt Ave in Sebastapol
    
    print "find shortest path tree"
    t0 = time.time()
    spt = g.shortest_path_tree( random_vertex_label, "bogus", State(0) )
    t1 = time.time()
    print "took: %f"%(t1-t0)
    
    fp = open("points.txt", "w")
    for edge in spt.edges:
        osmway = osm.ways[ edge.payload.name ]
        weight = edge.to_v.payload.weight
        points = osmway.get_projected_points(osm.nodes, utmzone10)
        length = osmway.length(osm.nodes, utmzone10)
        
        fp.write( "%s:%s:%f:%d:"%(edge.from_v.label,edge.to_v.label,length,weight)+",".join( [" ".join([str(c) for c in p]) for p in points] ) + "\n" )
    fp.close()
        
if __name__=='__main__':
    main()