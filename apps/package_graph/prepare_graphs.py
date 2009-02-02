from graphserver.core import State, Graph, TripBoard, Crossing, Alight, Link, ServiceCalendar, Timezone, TimezonePeriod, Street
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
import sys
import pytz
from datetime import timedelta, datetime, time
from graphserver.util import TimeHelpers
from graphserver.graphdb import GraphDatabase
from pyproj import Proj

def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)
        
def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def gtfsdb_to_service_calendar(gtfsdb, agency_id):
    """Given gtfsdb and agency_id, returns graphserver.core.ServiceCalendar"""
    
    # grab pytz timezone by agency_id, via gtfsdb
    timezone_name = gtfsdb.agency_timezone_name( agency_id )
    timezone = pytz.timezone( timezone_name )

    # grab date, day service bounds
    day_start, day_end = gtfsdb.day_bounds()
    start_date, end_date = gtfsdb.date_range()

    # init empty calendar
    cal = ServiceCalendar()

    # for each day in service range, inclusive
    for currdate in iter_dates(start_date, end_date):
        
        # get and encode in utf-8 the service_ids of all service periods running thos date
        service_ids = [x.encode('utf8') for x in gtfsdb.service_periods( currdate )]
        
        # figure datetime.datetime bounds of this service day
        currdate_start = datetime.combine(currdate, time(0))
        currdate_local_start = timezone.localize(currdate_start)
        service_period_begins = timezone.normalize( currdate_local_start + timedelta(seconds=day_start) )
        service_period_ends = timezone.normalize( currdate_local_start + timedelta(seconds=day_end)  )

        # enter as entry in service calendar
        cal.add_period( TimeHelpers.datetime_to_unix(service_period_begins), TimeHelpers.datetime_to_unix(service_period_ends), service_ids )

    return cal

def load_bundle_to_boardalight_graph(g, bundle_id, bundle, service_id, sc, tz):
    stop_time_bundles = list(bundle.stop_time_bundles(service_id))
    
    # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
    if len(stop_time_bundles)<2:
        return
        
    #add board edges
    for stop_time_bundle in stop_time_bundles[:-1]:
        
        if len(stop_time_bundle)==0:
            return
        
        trip_id, departure_time, arrival_time, stop_id, stop_sequence = stop_time_bundle[0]
        
        bundlestop_label = "%d-%s-%s"%(bundle_id,stop_id,service_id)
        g.add_vertex( bundlestop_label )
        
        b = TripBoard(service_id, sc, tz, 0)
        for trip_id, departure_time, arrival_time, stop_id, stop_sequence in stop_time_bundle:
            b.add_boarding( trip_id, departure_time )
            
        g.add_edge( stop_id, bundlestop_label, b )
        
    #add alight edges
    for stop_id in bundle.stop_ids[1:]:
        bundlestop_label = "%d-%s-%s"%(bundle_id,stop_id,service_id)
        g.add_vertex( bundlestop_label )
            
        g.add_edge( bundlestop_label, stop_id, Alight() )
    
    # add crossing edges
    for j, crossing_time in enumerate(bundle.crossings):
        c = Crossing( crossing_time )
        g.add_edge( "%d-%s-%s"%(bundle_id,bundle.stop_ids[j],service_id), "%d-%s-%s"%(bundle_id,bundle.stop_ids[j+1],service_id), c )

def load_gtfsdb_to_boardalight_graph(g, gtfsdb, agency_id, service_ids, reporter=sys.stdout):
    
    # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
    tz = Timezone.generate(gtfsdb.agency_timezone_name( agency_id ))
    sc = gtfsdb_to_service_calendar(gtfsdb, agency_id )

    # enter station vertices
    for stop_id, stop_name, stop_lat, stop_lon in gtfsdb.stops():
        g.add_vertex( stop_id )
    
    # compile trip bundles from gtfsdb
    if reporter: reporter.write( "Compiling trip bundles...\n" )
    bundles = gtfsdb.compile_trip_bundles(reporter=reporter)

    # load bundles to graph
    if reporter: reporter.write( "Loading trip bundles into graph...\n" )
    n_bundles = len(bundles)
    for bundle_num, bundle in enumerate( bundles ):
        if reporter and bundle_num%((n_bundles//100)+1)==0: reporter.write( "%d/%d trip bundles loaded\n"%(bundle_num, n_bundles) )
        
        for service_id in service_ids:
            load_bundle_to_boardalight_graph(g, bundle_num, bundle, service_id, sc, tz)

def dist(p1, p2, proj=lambda x,y:(x,y)):
    x1,y1 = proj(*p1)
    x2,y2 = proj(*p2)
    
    return ((x1-x2)**2 + (y1-y2)**2)**0.5

def load_streets_to_graph(g, osmdb, proj_epsg, reporter=None):
    proj = Proj(init='epsg:%d'%proj_epsg)
    
    n_ways = osmdb.count_ways()
    
    for i, way in enumerate( osmdb.ways() ):
        
        if reporter and i%(n_ways//100+1)==0: reporter.write( "%d/%d ways loaded\n"%(i, n_ways))
        
        #distance = sum( [((x2-x1)**2+(y2-y1)**2)**0.5 for (x1,y1),(x2,y2) in cons(way.geom)] )
        distance = sum( [dist(p1, p2, proj) for p1, p2 in cons(way.geom)] )
        
        vertex1_label = "osm"+way.nds[0]
        vertex2_label = "osm"+way.nds[-1]
        
        x1, y1 = way.geom[0]
        x2, y2 = way.geom[-1]
        
        g.add_vertex( vertex1_label )
        g.add_vertex( vertex2_label )
        g.add_edge( vertex1_label, vertex2_label, Street( way.id, distance ) )
        g.add_edge( vertex2_label, vertex1_label, Street( way.id, distance ) )
        
def load_transit_street_links_to_graph( g, osmdb, gtfsdb, reporter=None ):
    n = gtfsdb.count_stops()
    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        if reporter and i%(n//200+1)==0: reporter.write( "%d/%d stops linked\n"%(i, n))
        
        osm_id, osm_lat, osm_lon, osm_dist = osmdb.nearest_node( stop_lat, stop_lon )
         
        if osm_id:
            g.add_edge( stop_id, "osm"+osm_id, Link( ) )
            g.add_edge( "osm"+osm_id, stop_id, Link( ) )

def process_transit_graph():
    GTFSDB_FILENAME = "ext/gtfs/bart.gtfsdb"
    AGENCY_ID = "BART"
    GRAPHDB_FILENAME = "bart.db" 
    
    #GTFSDB_FILENAME = "ext/gtfs/trimet.gtfsdb"
    #AGENCY_ID = "TriMet"
    #ORIGIN_VERTEX_ID = "10071"
    #GRAPHDB_FILENAME = "trimet.db" 
    
    gtfsdb = GTFSDatabase( GTFSDB_FILENAME )
    
    g = Graph()
    service_ids = [x.encode("ascii") for x in gtfsdb.service_ids()]
    load_gtfsdb_to_boardalight_graph(g, gtfsdb, agency_id=AGENCY_ID, service_ids=service_ids)
    
    graphdb = GraphDatabase( GRAPHDB_FILENAME, overwrite=True )
    graphdb.populate( g, reporter=sys.stdout )
    
def process_street_graph():
    OSMDB_FILENAME = "ext/osm/bartarea.sqlite"
    GRAPHDB_FILENAME = "bartstreets.db"
    
    print( "Opening OSM-DB '%s'"%OSMDB_FILENAME )
    osmdb = OSMDB( OSMDB_FILENAME )
    
    g = Graph()
    load_streets_to_graph( g, osmdb, 26910, sys.stdout )
    
    graphdb = GraphDatabase( GRAPHDB_FILENAME, overwrite=True )
    graphdb.populate( g, reporter=sys.stdout )
    
def process_transit_street_graph(graphdb_filename, gtfsdb_filename, agency_id, osmdb_filename, projection_epsg):
    g = Graph()

    # Load gtfsdb ==============================
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    service_ids = [x.encode("ascii") for x in gtfsdb.service_ids()]
    load_gtfsdb_to_boardalight_graph(g, gtfsdb, agency_id=agency_id, service_ids=service_ids)
    
    # Load osmdb ===============================
    
    print( "Opening OSM-DB '%s'"%osmdb_filename )
    osmdb = OSMDB( osmdb_filename )
    
    load_streets_to_graph( g, osmdb, projection_epsg, sys.stdout )
    
    # Link osm to transit ======================
    
    load_transit_street_links_to_graph( g, osmdb, gtfsdb, reporter=sys.stdout )
    
    # Export to graphdb ========================
    
    graphdb = GraphDatabase( graphdb_filename, overwrite=True )
    graphdb.populate( g, reporter=sys.stdout )

import sys
if __name__=='__main__':

    #process_transit_graph()
    #process_street_graph()
    #process_transit_street_graph("streetsbart.db", "bart.gtfsdb", "BART", "bartarea.sqlite", 26910 )
    process_transit_street_graph("streetstrimet.db", "trimet.gtfsdb", "TriMet", "bigportland.sqlite", 26910 )

    
    

