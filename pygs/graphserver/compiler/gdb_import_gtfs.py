from graphserver.core import State, Graph, TripBoard, HeadwayBoard, HeadwayAlight, Crossing, TripAlight, Link, ServiceCalendar, Timezone, TimezonePeriod, Street
from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
import sys
import pytz
from tools import service_calendar_from_timezone

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def bundle_to_boardalight_edges(agency_namespace, bundle, service_id, sc, tz):
    """takes a bundle and yields a bunch of edges"""
    
    stop_time_bundles = bundle.stop_time_bundles(service_id)
    
    n_trips = len(bundle.trip_ids)
        
    # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
    if len(stop_time_bundles)<2:
        return
        
    # If there are no stop_times in a bundle on this service day, there is nothing to load
    if n_trips==0:
        return
        
    print "inserting %d trips with %d stop_time bundles on service_id '%s'"%(len(stop_time_bundles[0]),len(stop_time_bundles),service_id)

    #add board edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[:-1]):
        
        trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        if arrival_time != departure_time:
            patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart"%(agency_namespace,bundle.pattern.pattern_id,i,service_id)
            
            # construct the board/alight/dwell triangle for this patternstop
            patternstop_arrival_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(agency_namespace,bundle.pattern.pattern_id,i,service_id)
            
            dwell_crossing = Crossing()
            for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
                dwell_crossing.add_crossing_time( trip_id, departure_time-arrival_time )
            
	    yield (patternstop_arrival_vx_name, 
                   patternstop_vx_name,
                   dwell_crossing)
            
        else:
            patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(agency_namespace,bundle.pattern.pattern_id,i,service_id)
        
        b = TripBoard(service_id, sc, tz, 0)
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            b.add_boarding( trip_id, departure_time, stop_sequence )
            
        yield ( "sta-%s"%stop_id, patternstop_vx_name, b )
        
    #add alight edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[1:]):

        trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        if arrival_time != departure_time:
            patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
        else:
            patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
        
        al = TripAlight(service_id, sc, tz, 0)
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            al.add_alighting( trip_id.encode('ascii'), arrival_time, stop_sequence )
            
        yield ( patternstop_vx_name, "sta-%s"%stop_id, al )
    
    # add crossing edges
    for i, (from_stop_time_bundle, to_stop_time_bundle) in enumerate(cons(stop_time_bundles)):
        
        trip_id, from_arrival_time, from_departure_time, stop_id, stop_sequence, stop_dist_traveled = from_stop_time_bundle[0]
        trip_id, to_arrival_time, to_departure_time, stop_id, stop_sequence, stop_dist_traveled = to_stop_time_bundle[0]
        
        if from_arrival_time!=from_departure_time:
            from_patternstop_vx_name = "psv-%s-%03d-%03d-%s-depart"%(agency_namespace,bundle.pattern.pattern_id,i,service_id)
        else:
            from_patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(agency_namespace,bundle.pattern.pattern_id,i,service_id)
            
        if to_arrival_time!=to_departure_time:
            to_patternstop_vx_name = "psv-%s-%03d-%03d-%s-arrive"%(agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
        else:
            to_patternstop_vx_name = "psv-%s-%03d-%03d-%s"%(agency_namespace,bundle.pattern.pattern_id,i+1,service_id)
        
        crossing = Crossing()
        for i in range( len( from_stop_time_bundle ) ):
            trip_id, from_arrival_time, from_departure_time, stop_id, stop_sequence, stop_dist_traveled = from_stop_time_bundle[i]
            trip_id, to_arrival_time, to_departure_time, stop_id, stop_sequence, stop_dist_traveled = to_stop_time_bundle[i]
            crossing.add_crossing_time( trip_id, (to_arrival_time-from_departure_time) )
        
        yield ( from_patternstop_vx_name, 
                to_patternstop_vx_name, 
                crossing )

def gtfsdb_to_scheduled_edges(agency_namespace, gtfsdb, agency_id=None, maxtrips=None, reporter=sys.stdout):

    # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
    timezone_name = gtfsdb.agency_timezone_name(agency_id)
    gs_tz = Timezone.generate( timezone_name )
    print "constructing service calendar for timezone '%s'"%timezone_name
    sc = service_calendar_from_timezone(gtfsdb, timezone_name )
    
    # compile trip bundles from gtfsdb
    if reporter: reporter.write( "Compiling trip bundles...\n" )
    bundles = gtfsdb.compile_trip_bundles(maxtrips=maxtrips, reporter=reporter)
    
    # load bundles to graph
    if reporter: reporter.write( "Loading trip bundles into graph...\n" )
    n_bundles = len(bundles)
    for i, bundle in enumerate(bundles):
        if reporter: reporter.write( "%d/%d loading %s\n"%(i+1, n_bundles, bundle) )
        
        for service_id in [x.encode("ascii") for x in gtfsdb.service_ids()]:
	    for fromv_label, tov_label, edge in bundle_to_boardalight_edges(agency_namespace, bundle, service_id, sc, gs_tz):
	        yield fromv_label, tov_label, edge

def gtfsdb_to_headway_edges(agency_namespace, gtfsdb, agency_id=None, maxtrips=None, reporter=sys.stdout):

    # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
    timezone_name = gtfsdb.agency_timezone_name(agency_id)
    gs_tz = Timezone.generate( timezone_name )
    print "constructing service calendar for timezone '%s'"%timezone_name
    sc = service_calendar_from_timezone(gtfsdb, timezone_name )

    # load headways
    if reporter: reporter.write( "Loading headways trips to graph...\n" )
    for trip_id, start_time, end_time, headway_secs in gtfsdb.execute( "SELECT * FROM frequencies" ):
        service_id = list(gtfsdb.execute( "SELECT service_id FROM trips WHERE trip_id=?", (trip_id,) ))[0][0]
        service_id = service_id.encode('utf-8')
        
        hb = HeadwayBoard( service_id, sc, gs_tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
        ha = HeadwayAlight( service_id, sc, gs_tz, 0, trip_id.encode('utf-8'), start_time, end_time, headway_secs )
        
        stoptimes = list(gtfsdb.execute( "SELECT * FROM stop_times WHERE trip_id=? ORDER BY stop_sequence", (trip_id,)) )
        
        #add board edges
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[:-1]:
            yield ( "sta-%s"%stop_id, "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), hb )
            
        #add alight edges
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[1:]:
            yield ( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), "sta-%s"%stop_id, ha )
        
        #add crossing edges
        for (trip_id1, arrival_time1, departure_time1, stop_id1, stop_sequence1, stop_dist_traveled1), (trip_id2, arrival_time2, departure_time2, stop_id2, stop_sequence2,stop_dist_traveled2) in cons(stoptimes):
            cr = Crossing()
            cr.add_crossing_time( trip_id1, (arrival_time2-departure_time1) )
            yield ( "hwv-%s-%s-%s"%(agency_namespace,stop_id1, trip_id1), "hwv-%s-%s-%s"%(agency_namespace,stop_id2, trip_id2), cr )

def gtfsdb_to_connection_edges(gtfsdb, reporter=sys.stdout):
            
    # load connections
    if reporter: reporter.write( "Loading connections to graph...\n" )
    for stop_id1, stop_id2, conn_type, distance in gtfsdb.execute( "SELECT * FROM connections" ):
        yield ( "sta-%s"%stop_id1, "sta-%s"%stop_id2, Street( conn_type, distance ) )
        yield ( "sta-%s"%stop_id2, "sta-%s"%stop_id1, Street( conn_type, distance ) )


def gtfsdb_to_edges(agency_namespace, gtfsdb, agency_id=None, maxtrips=None, reporter=sys.stdout):
    for edge_tuple in gtfsdb_to_scheduled_edges(agency_namespace, gtfsdb, agency_id, maxtrips, reporter):
        yield edge_tuple

    for edge_tuple in gtfsdb_to_headway_edges(agency_namespace, gtfsdb, agency_id, maxtrips, reporter):
        yield edge_tuple 

    for edge_tuple in gtfsdb_to_connection_edges( gtfsdb, reporter ):
        yield edge_tuple

def gdb_load_gtfsdb(gdb, agency_namespace, gtfsdb, cursor, agency_id=None, maxtrips=None, reporter=sys.stdout):

    for fromv_label, tov_label, edge in gtfsdb_to_edges( agency_namespace, gtfsdb, agency_id, maxtrips, reporter ):
        gdb.add_vertex( fromv_label )
	gdb.add_vertex( tov_label )
	gdb.add_edge( fromv_label, tov_label, edge )
        
def main():
    usage = """usage: python gdb_import_gtfs.py [options] <graphdb_filename> <gtfsdb_filename> [<agency_id>]"""
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--namespace", dest="namespace", default="0",
                      help="agency namespace")
    parser.add_option("-m", "--maxtrips", dest="maxtrips", default=None, help="maximum number of trips to load")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        parser.print_help()
        exit(-1)
    
    graphdb_filename = args[0]
    gtfsdb_filename  = args[1]
    agency_id        = args[2] if len(args)==3 else None
    
    print "importing from gtfsdb '%s' into graphdb '%s'"%(gtfsdb_filename, graphdb_filename)
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    gdb = GraphDatabase( graphdb_filename, overwrite=False )
    
    maxtrips = int(options.maxtrips) if options.maxtrips else None
    gdb_load_gtfsdb( gdb, options.namespace, gtfsdb, gdb.get_cursor(), agency_id, maxtrips=maxtrips)
    gdb.commit()
    
    print "done"

if __name__ == '__main__':
    main()
