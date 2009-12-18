from graphserver.graphdb import GraphDatabase
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.osm.profiledb import ProfileDB
from graphserver import compiler
from graphserver.core import Graph
import sys
from sys import argv
    
def process_street_graph(osmdb_filename, graphdb_filename, profiledb_filename, slogs={}):
    OSMDB_FILENAME = "ext/osm/bartarea.sqlite"
    GRAPHDB_FILENAME = "bartstreets.db"
    
    print( "Opening OSM-DB '%s'"%osmdb_filename )
    osmdb = OSMDB( osmdb_filename )
    
    if profiledb_filename:
        print( "Opening ProfileDB '%s'"%profiledb_filename )
        profiledb = ProfileDB( profiledb_filename )
    else:
        print( "No ProfileDB supplied" )
        profiledb = None
    
    g = Graph()
    compiler.load_streets_to_graph( g, osmdb, profiledb, slogs, reporter=sys.stdout )
    
    graphdb = GraphDatabase( graphdb_filename, overwrite=True )
    graphdb.populate( g, reporter=sys.stdout )
    
def process_transit_graph(graphdb_filename, gtfsdb_filenames, osmdb_filename=None, profiledb_filename=None, agency_id=None, link_stations=False, slogs={}):
    g = Graph()

    if profiledb_filename:
        print( "Opening ProfileDB '%s'"%profiledb_filename )
        profiledb = ProfileDB( profiledb_filename )
    else:
        print( "No ProfileDB supplied" )
        profiledb = None

    if osmdb_filename:
        # Load osmdb ===============================
        print( "Opening OSM-DB '%s'"%osmdb_filename )
        osmdb = OSMDB( osmdb_filename )
        compiler.load_streets_to_graph( g, osmdb, profiledb, slogs, reporter=sys.stdout )
    
    # Load gtfsdb ==============================
   
    for i, gtfsdb_filename in enumerate(gtfsdb_filenames): 
        gtfsdb = GTFSDatabase( gtfsdb_filename )
        service_ids = [x.encode("ascii") for x in gtfsdb.service_ids()]
        compiler.load_gtfsdb_to_boardalight_graph(g, str(i), gtfsdb, agency_id=agency_id, service_ids=service_ids)
        if osmdb_filename:
            compiler.load_transit_street_links_to_graph( g, osmdb, gtfsdb, reporter=sys.stdout )
        
        if link_stations:
            compiler.link_nearby_stops( g, gtfsdb )

    # Export to graphdb ========================
    
    graphdb = GraphDatabase( graphdb_filename, overwrite=True )
    graphdb.populate( g, reporter=sys.stdout )


def main():
    from optparse import OptionParser
    usage = """usage: python compile_graph.py [options] <graphdb_filename> """
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--osmdb", dest="osmdb_filename", default=None,
                      help="conflate with the compiled OSMDB", metavar="FILE")
    parser.add_option("-l", "--link",
                      action="store_true", dest="link", default=False,
                      help="create walking links between adjacent/nearby stations if not compiling with an OSMDB")
    parser.add_option("-g", "--gtfsdb",
                      action="append", dest="gtfsdb_files", default=[],
                      help="compile with the specified GTFS file(s)")
    parser.add_option("-p", "--profiledb",
                      dest="profiledb_filename", default=None,
                      help="compile road network with elevation information from profiledb")
    parser.add_option("-s", "--slog",
                      action="append", dest="slog_strings", default=[],
                      help="specify slog for highway type, in highway_type:slog form. For example, 'motorway:10.5'")

    (options, args) = parser.parse_args()
    
    slogs = {}
    for slog_string in options.slog_strings:
        highway_type,slog_penalty = slog_string.split(":")
        slogs[highway_type] = float(slog_penalty)
    print slogs
    
    if len(args) != 1 or not options.osmdb_filename and not len(options.gtfsdb_files):
        parser.print_help()
        exit(-1)

    graphdb_filename = args[0]

    # just street graph compilation
    if options.osmdb_filename and not len(options.gtfsdb_files):
        process_street_graph(options.osmdb_filename, graphdb_filename, options.profiledb_filename, slogs)
        exit(0)
    
    
    process_transit_graph(graphdb_filename, options.gtfsdb_files,
                          osmdb_filename=options.osmdb_filename,
                          profiledb_filename=options.profiledb_filename,
                          link_stations=options.link and not options.osmdb_filename, slogs=slogs)
    exit(0)
        
if __name__=='__main__': main()
