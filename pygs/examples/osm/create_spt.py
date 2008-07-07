import time
from osm import OSM, Node, Way
import sys
sys.path.append('../..')
from structures import Graph, Street, State


from urllib import urlopen
def get_osm_xml( left, bottom, right, top ):
    fp = urlopen( "http://api.openstreetmap.org/api/0.5/map?bbox=%f,%f,%f,%f"%(left,bottom,right,top) )
    return fp.read()

def main():
    #print get_osm_xml( -122.33, 47.66, -122.31, 47.68 )
 
    print "read osm file"
    osm = OSM("map.osm")

    print "load vertices into graph file"
    g = Graph()
    for nodeid in osm.nodes.keys():
        g.add_vertex( str(nodeid) )

    print "load edges into graph file"
    for wayid, way in osm.ways.iteritems():
        if 'highway' in way.tags:
            len = way.length(osm.nodes)
            
            if way.tags['highway']=='cycleway':
                len = len/3
            elif way.tags['highway']=='motorway':
                len = len*100
            elif way.tags['highway']=='footway':
                len = len/2
            
            g.add_edge( str(way.fromv), str(way.tov), Street( wayid, len ) )
            g.add_edge( str(way.tov), str(way.fromv), Street( wayid, len ) )
        
    random_vertex_label = "53217079"
    
    print "find shortest path tree"
    t0 = time.time()
    spt = g.shortest_path_tree( random_vertex_label, "bogus", State(0) )
    t1 = time.time()
    print "took: %f"%(t1-t0)
    
    fp = open("points.txt", "w")
    for edge in spt.edges:
        osmway = osm.ways[ edge.payload.name ]
        weight = edge.to_v.payload.weight
        points = osmway.get_projected_points(osm.nodes)
        length = osmway.length(osm.nodes)
        
        fp.write( "%s:%s:%f:%d:"%(edge.from_v.label,edge.to_v.label,length,weight)+",".join( [" ".join([str(c) for c in p]) for p in points] ) + "\n" )
    fp.close()
        
if __name__=='__main__':
    main()