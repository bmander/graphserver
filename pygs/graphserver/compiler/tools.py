from graphserver.core import State, Graph, TripBoard, HeadwayBoard, HeadwayAlight, Crossing, Alight, Link, ServiceCalendar, Timezone, TimezonePeriod, Street
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
import sys
import pytz
from datetime import timedelta, datetime, time
from graphserver.util import TimeHelpers
from graphserver.graphdb import GraphDatabase
from vincenty import vincenty

def iter_dates(startdate, enddate):
    currdate = startdate
    while currdate <= enddate:
        yield currdate
        currdate += timedelta(1)
        
def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def gtfsdb_to_service_calendar(gtfsdb, agency_id=None):
    """Given gtfsdb and agency_id, returns graphserver.core.ServiceCalendar"""
    
    # grab pytz timezone by agency_id, via gtfsdb
    timezone_name = gtfsdb.agency_timezone_name( agency_id )
    timezone = pytz.timezone( timezone_name )

    # grab date, day service bounds
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
        service_period_begins = timezone.normalize( currdate_local_start )
        service_period_ends = timezone.normalize( currdate_local_start + timedelta(hours=24)  )

        # enter as entry in service calendar
        cal.add_period( TimeHelpers.datetime_to_unix(service_period_begins), TimeHelpers.datetime_to_unix(service_period_ends), service_ids )

    return cal

def load_bundle_to_boardalight_graph(g, agency_namespace, bundle, service_id, sc, tz):
    stop_time_bundles = list(bundle.stop_time_bundles(service_id))
    
    # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
    if len(stop_time_bundles)<2:
        return
        
    # If there are no stop_times in a bundle on this service day, there is nothing to load
    if len(stop_time_bundles[0])==0:
        return
        
    #add board edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[:-1]):
        
        if len(stop_time_bundle)==0:
            continue
        
        trip_id, departure_time, arrival_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i)
        
        g.add_vertex( patternstop_vx_name )
        
        b = TripBoard(service_id, sc, tz, 0)
        for trip_id, departure_time, arrival_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            b.add_boarding( trip_id, departure_time )
            
        g.add_edge( "sta-%s"%stop_id, patternstop_vx_name, b )
        
    #add alight edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[1:]):
        if len(stop_time_bundle)==0:
            continue

        trip_id, departure_time, arrival_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i+1)
        g.add_vertex( patternstop_vx_name )
        
        al = Alight(service_id, sc, tz, 0)
        for trip_id, departure_time, arrival_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            al.add_alighting( trip_id.encode('ascii'), arrival_time )
            
        g.add_edge( patternstop_vx_name, "sta-%s"%stop_id, al )
    
    # add crossing edges
    for j, crossing_time in enumerate(bundle.pattern.crossings):
        c = Crossing( crossing_time )
        g.add_edge( "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,j), "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,j+1), c )
            
def load_gtfsdb_to_boardalight_graph(g, agency_namespace, gtfsdb, agency_id, service_ids, reporter=sys.stdout):
    
    # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
    tz = Timezone.generate(gtfsdb.agency_timezone_name( agency_id ))
    sc = gtfsdb_to_service_calendar(gtfsdb, agency_id )

    # enter station vertices
    for stop_id, stop_name, stop_lat, stop_lon in gtfsdb.stops():
        g.add_vertex( "sta-%s"%stop_id )
    
    # compile trip bundles from gtfsdb
    if reporter: reporter.write( "Compiling trip bundles...\n" )
    bundles = gtfsdb.compile_trip_bundles(reporter=reporter)

    # load bundles to graph
    if reporter: reporter.write( "Loading trip bundles into graph...\n" )
    n_bundles = len(bundles)
    for i, bundle in enumerate(bundles):
        if reporter and i%((n_bundles//100)+1)==0: reporter.write( "%d/%d trip bundles loaded\n"%(i, n_bundles) )
        
        for service_id in service_ids:
            load_bundle_to_boardalight_graph(g, agency_namespace, bundle, service_id, sc, tz)
            
    # load headways
    if reporter: reporter.write( "Loading headways trips to graph...\n" )
    for trip_id, start_time, end_time, headway_secs in gtfsdb.execute( "SELECT * FROM frequencies" ):
        service_id = list(gtfsdb.execute( "SELECT service_id FROM trips WHERE trip_id=?", (trip_id,) ))[0][0]
        service_id = service_id.encode('utf-8')
        
        hb = HeadwayBoard( service_id, sc, tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
        ha = HeadwayAlight( service_id, sc, tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
        
        stoptimes = list(gtfsdb.execute( "SELECT * FROM stop_times WHERE trip_id=? ORDER BY stop_sequence", (trip_id,)) )
        
        #add board edges
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[:-1]:
            g.add_vertex( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id) )
            g.add_edge( "sta-%s"%stop_id, "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), hb )
            
        #add alight edges
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[1:]:
            g.add_vertex( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id) )
            g.add_edge( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), "sta-%s"%stop_id, ha )
            print ha
        
        #add crossing edges
        for (trip_id1, arrival_time1, departure_time1, stop_id1, stop_sequence1, stop_dist_traveled1), (trip_id2, arrival_time2, departure_time2, stop_id2, stop_sequence2,stop_dist_traveled2) in cons(stoptimes):
            g.add_edge( "hwv-%s-%s-%s"%(agency_namespace,stop_id1, trip_id1), "hwv-%s-%s-%s"%(agency_namespace,stop_id2, trip_id2), Crossing(arrival_time2-departure_time1) )
            
    # load connections
    if reporter: reporter.write( "Loading connections to graph...\n" )
    for stop_id1, stop_id2, conn_type, distance in gtfsdb.execute( "SELECT * FROM connections" ):
        g.add_edge( "sta-%s"%stop_id1, "sta-%s"%stop_id2, Street( conn_type, distance ) )
        g.add_edge( "sta-%s"%stop_id2, "sta-%s"%stop_id1, Street( conn_type, distance ) )
            
def link_nearby_stops(g, gtfsdb, range=0.05, obstruction=1.4):
    """Adds Street links of length obstruction*dist(A,B) directly between all station pairs closer than <range>"""

    print "Linking nearby stops..."

    for stop_id1, stop_name1, lat1, lon1 in gtfsdb.stops():
        g.add_vertex( "sta-%s"%stop_id1 )
        
        for stop_id2, stop_name2, lat2, lon2 in gtfsdb.nearby_stops(lat1, lon1, range):
            if stop_id1 == stop_id2:
                continue
            
            print "linking %s to %s"%(stop_id1, stop_id2)
            
            g.add_vertex( "sta-%s"%stop_id2 )
            
            dd = obstruction*vincenty( lat1, lon1, lat2, lon2 )
            print dd
            
            g.add_edge( "sta-%s"%stop_id1, "sta-%s"%stop_id2, Street("walk", dd) )
            g.add_edge( "sta-%s"%stop_id2, "sta-%s"%stop_id1, Street("walk", dd) )

def profile_rise_fall(profile):
    rise = 0
    fall = 0
    for (s1, e1), (s2,e2) in cons(profile):
        diff = e2-e1
        if diff>0:
            rise += diff
        elif diff<0:
            fall -= diff
    return (rise,fall)

def load_streets_to_graph(g, osmdb, profiledb=None, slogs={}, reporter=None ):
    
    n_edges = osmdb.count_edges()
    
    street_id_counter = 0
    street_names = {}
    for i, (id, parent_id, node1, node2, distance, geom, tags) in enumerate( osmdb.edges() ):
        
        if reporter and i%(n_edges//100+1)==0: reporter.write( "%d/%d edges loaded\n"%(i, n_edges))
        
        # insert end vertices of edge to graph
        vertex1_label = "osm-%s"%node1
        vertex2_label = "osm-%s"%node2
        g.add_vertex( vertex1_label )
        g.add_vertex( vertex2_label )
        
        if node1 == "57808625":
            print (id, parent_id, node1, node2, distance, geom, tags)
            exit()
        
        # Find rise/fall of edge, if profiledb is given
        rise=0
        fall=0
        if profiledb:
            profile = profiledb.get( id )
            if profile:
                rise, fall = profile_rise_fall( profile )
                
        # create ID for the way's street
        street_name = tags.get("name")
        if street_name is None:
            street_id_counter += 1
            street_id = street_id_counter
        else:
            if street_name not in street_names:
                street_id_counter += 1
                street_names[street_name] = street_id_counter
            street_id = street_names[street_name]
        
        # Create edges to be inserted into graph
        s1 = Street( id, distance, rise, fall )
        s2 = Street( id, distance, fall, rise )
        s1.way = street_id
        s2.way = street_id
        
        # See if the way's highway tag is penalized with a 'slog' value; if so, set it in the edges
        slog = slogs.get( tags.get("highway") )
        if slog:
            s1.slog = s2.slog = slog
        
        # Add the forward edge and the return edge if the edge is not oneway
        g.add_edge( vertex1_label, vertex2_label, s1 )
        oneway = tags.get("oneway")
        if oneway != "true" and oneway != "yes":
            g.add_edge( vertex2_label, vertex1_label, s2 )
        
def load_transit_street_links_to_graph( g, osmdb, gtfsdb, reporter=None ):
    n = gtfsdb.count_stops()
    for i, (stop_id, stop_name, stop_lat, stop_lon) in enumerate( gtfsdb.stops() ):
        if reporter and i%(n//200+1)==0: reporter.write( "%d/%d stops linked\n"%(i, n))
        
        osm_id, osm_lat, osm_lon, osm_dist = osmdb.nearest_node( stop_lat, stop_lon )
         
        if osm_id:
            g.add_edge( "sta-%s"%stop_id, "osm-%s"%osm_id, Link( ) )
            g.add_edge( "osm-%s"%osm_id, "sta-%s"%stop_id, Link( ) )


