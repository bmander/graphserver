
from graphserver.graphdb import GraphDatabase
from graphserver.core import State, WalkOptions
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
import yaml
import graphserver
from prender import processing

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def main(settings_filename):
    settings = yaml.load( open(settings_filename).read() )
    starttime = settings['origin_time']
    cutoff = settings['cutoff']
    
    # get gtfsdb
    gtfsdb = GTFSDatabase( settings['gtfsdb_filename'] )
    
    # get osmdb
    osmdb = OSMDB( settings['osmdb_filename'] )
    geom_cache = {}
    for i, way in enumerate(osmdb.ways()):
        if i%1000==0: print i
        geom_cache[way.id] = way.geom
    
    # incarnate graph from graphdb
    graphdb = GraphDatabase( settings['graphdb_filename'] )
    graph = graphdb.incarnate()
    
    wo = WalkOptions()
    spt = graph.shortest_path_tree( settings['origin_label'], None, State(1,starttime), wo, maxtime=starttime+int(cutoff*1.25) )
    spt.set_thicknesses( settings['origin_label'] )
    wo.destroy()
    
    segs = []
    for vertex in spt.vertices:
        for edge in vertex.outgoing:
            if edge.payload.__class__ == graphserver.core.Street:
                segs.append( (geom_cache[ edge.payload.name ], edge.thickness) )
            #elif edge.payload.__class__ == graphserver.core.Crossing:
            #    print edge.from_v.incoming[0].from_v.label
            #    print edge.to_v.outgoing[0].to_v.label
            #    print edge.payload
                
    l, b = float('inf'), float('inf')
    r, t = -float('inf'), -float('inf')
    
    for seg, thickness in segs:
        for x,y in seg:
            l = min(x,l)
            b = min(y,b)
            r = max(x,r)
            t = max(y,t)
            
    print l, b, r, t

    mr = processing.MapRenderer()
    mr.start(l,b,r,t,3000) #left,bottom,right,top,width
    mr.smooth()
    mr.background(255,255,255)
    #mr.strokeWeight(0.0001)
    
    for seg, thickness in segs:
        for (x1,y1), (x2,y2) in cons(seg):
            mr.strokeWeight( (thickness**0.5)*0.000005 )
            mr.line(x1,y1,x2,y2)
    
    mr.saveLocal("map.png")
    mr.stop()

    
if __name__ == '__main__':
    main( "settings.yaml" )