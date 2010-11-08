from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.graphdb import GraphDatabase
from graphserver.core import Link, Street
from graphserver.vincenty import vincenty

import sys
from optparse import OptionParser

def main():
    usage = """usage: python gdb_link_gtfs_gtfs.py <graphdb_filename> <gtfsdb_filename> <range>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 3:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]
    gtfsdb_filename  = args[1]
    range = float(args[2])
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    gdb = GraphDatabase( graphdb_filename )

    n_stops = gtfsdb.count_stops()

    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        print "%d/%d %s"%(i,n_stops,stop_id),
        
        station_vertex_id = "sta-%s"%stop_id
        
        for link_stop_id, link_stop_name, link_stop_lat, link_stop_lon in gtfsdb.nearby_stops( stop_lat, stop_lon, range ):
            if link_stop_id == stop_id:
                continue
            
            print ".",
            
            link_length = vincenty( stop_lat, stop_lon, link_stop_lat, link_stop_lon)
            link_station_vertex_id = "sta-%s"%link_stop_id
            gdb.add_edge( station_vertex_id, link_station_vertex_id, Street("link", link_length) )
            
        print ""

if __name__=='__main__':
    main()
