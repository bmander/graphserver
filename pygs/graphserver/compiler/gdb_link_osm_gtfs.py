from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.graphdb import GraphDatabase
from graphserver.core import Link

import sys
from optparse import OptionParser

def main():
    usage = """usage: python gdb_link_osm_gtfs.py <graphdb_filename> <osmdb_filename> <gtfsdb_filename>"""
    parser = OptionParser(usage=usage)
    
    (options, args) = parser.parse_args()
    
    if len(args) != 3:
        parser.print_help()
        exit(-1)
        
    graphdb_filename = args[0]
    osmdb_filename   = args[1]
    gtfsdb_filename  = args[2]
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    osmdb = OSMDB( osmdb_filename )
    gdb = GraphDatabase( graphdb_filename )

    n_stops = gtfsdb.count_stops()

    c = gdb.get_cursor()
    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        print "%d/%d"%(i,n_stops)
        
        nd_id, nd_lat, nd_lon, nd_dist = osmdb.nearest_node( stop_lat, stop_lon )
        station_vertex_id = "sta-%s"%stop_id
        osm_vertex_id = "osm-%s"%nd_id
        
        print station_vertex_id, osm_vertex_id
        
        gdb.add_edge( station_vertex_id, osm_vertex_id, Link(), c )
        gdb.add_edge( osm_vertex_id, station_vertex_id, Link(), c )
    
    gdb.commit()
    
if __name__=='__main__':
    main()