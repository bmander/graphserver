from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.osm.osmfilters import FindDisjunctGraphsFilter
import xml.sax
from graphserver.ext.osm.osm import Node, Way

def cons(ary):
    for i in range(len(ary)-1):
        yield ary[i], ary[i+1]

def render_gtfsdb(gtfsdb, mr):

    points = dict([(id,(lat, lon)) for id, name, lat, lon in gtfsdb.execute( "SELECT * FROM stops" )])

    for (route_id,) in gtfsdb.execute( "SELECT route_id FROM routes" ):
        print route_id
        for (trip_id,) in gtfsdb.execute("SELECT trip_id FROM trips WHERE route_id=? LIMIT 1",(route_id,) ):
            stop_seq = [stop_id for (stop_id,) in gtfsdb.execute("SELECT stop_id FROM stop_times where trip_id=? ORDER BY stop_sequence",(trip_id,))]
            
            for s1, s2 in cons(stop_seq):
                (lat1,lon1),(lat2,lon2)=points[s1],points[s2]
                mr.line(lon1,lat1,lon2,lat2)
                #print lat1,lon1,lat2,lon2

    mr.stroke(255,0,0)
    mr.strokeWeight(0.0005)
    for lat,lon in points.values():
        mr.point( lon, lat )
        
def render_osmdb(osmdb, mr):
    n = osmdb.count_ways()
    
    for i, way in enumerate(osmdb.ways()):
        if i%1000==0: print "way %d/%d"%(i,n)
        
        for (lon1,lat1),(lon2,lat2) in cons(way.geom):
            mr.line(lon1,lat1,lon2,lat2)

def main():

    gtfsdb = GTFSDatabase( "data/washingtondc.gtfsdb" )
    osmdb = OSMDB( "data/washingtondc.osmdb" )
    ll,bb,rr,tt = list(gtfsdb.execute( "SELECT min(stop_lon), min(stop_lat), max(stop_lon), max(stop_lat) FROM stops" ))[0]

    from prender import processing
    mr = processing.MapRenderer()
    mr.start(ll,bb,rr,tt,4000) #left,bottom,right,top,width
    mr.smooth()
    mr.strokeWeight(0.000001)
    mr.background(255,255,255)

    mr.stroke(128,128,128)
    render_osmdb(osmdb, mr)

    mr.stroke(0,0,0)
    render_gtfsdb(gtfsdb, mr)
        
    mr.saveLocal("map.png")
    mr.stop()
    
if __name__=='__main__':
    main()
