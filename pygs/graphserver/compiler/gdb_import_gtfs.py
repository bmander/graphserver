from graphserver.core import State, Graph, TripBoard, HeadwayBoard, HeadwayAlight, Crossing, Alight, Link, ServiceCalendar, Timezone, TimezonePeriod, Street
from optparse import OptionParser
from graphserver.graphdb import GraphDatabase
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
import sys
from tools import gtfsdb_to_service_calendar

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def gdb_boardalight_load_bundle(gdb, agency_namespace, bundle, service_id, sc, tz, cursor):
    
    stop_time_bundles = bundle.stop_time_bundles(service_id)
    
    n_trips = len(bundle.trip_ids)    
    
    # If there's less than two stations on this trip bundle, the trip bundle doesn't actually span two places
    if len(stop_time_bundles)<2:
        return
        
    # If there are no stop_times in a bundle on this service day, there is nothing to load
    if n_trips==0:
        return
        
    print "inserting %d trips with %d stop_time bundles on service_id '%s'"%(len(stop_time_bundles[0]),len(stop_time_bundles),service_id)
    #print bundle.pattern.stop_ids

    #add board edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[:-1]):
        
        trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        if arrival_time != departure_time:
            patternstop_vx_name = "psv-%s-%03d-%03d-depart"%(agency_namespace,bundle.pattern.pattern_id,i)
            
            # construct the board/alight/dwell triangle for this patternstop
            patternstop_arrival_vx_name = "psv-%s-%03d-%03d-arrive"%(agency_namespace,bundle.pattern.pattern_id,i)
            gdb.add_vertex( patternstop_arrival_vx_name, cursor )
            gdb.add_edge( patternstop_arrival_vx_name, 
                          patternstop_vx_name,
                          Crossing( (departure_time-arrival_time) ), 
                          cursor )
            
        else:
            patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i)
        
        gdb.add_vertex( patternstop_vx_name, cursor )
        
        b = TripBoard(service_id, sc, tz, 0)
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            b.add_boarding( trip_id, departure_time )
            
        gdb.add_edge( "sta-%s"%stop_id, patternstop_vx_name, b, cursor )
        
    #add alight edges
    for i, stop_time_bundle in enumerate(stop_time_bundles[1:]):

        trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled = stop_time_bundle[0]
        
        if arrival_time != departure_time:
            patternstop_vx_name = "psv-%s-%03d-%03d-arrive"%(agency_namespace,bundle.pattern.pattern_id,i+1)
        else:
            patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i+1)
            
        gdb.add_vertex( patternstop_vx_name, cursor )
        
        al = Alight(service_id, sc, tz, 0)
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stop_time_bundle:
            al.add_alighting( trip_id.encode('ascii'), arrival_time )
            
        gdb.add_edge( patternstop_vx_name, "sta-%s"%stop_id, al, cursor )
    
    # add crossing edges
    for i, (from_stop_time_bundle, to_stop_time_bundle) in enumerate(cons(stop_time_bundles)):
        
        trip_id, from_arrival_time, from_departure_time, stop_id, stop_sequence, stop_dist_traveled = from_stop_time_bundle[0]
        trip_id, to_arrival_time, to_departure_time, stop_id, stop_sequence, stop_dist_traveled = to_stop_time_bundle[0]
        
        if from_arrival_time!=from_departure_time:
            from_patternstop_vx_name = "psv-%s-%03d-%03d-depart"%(agency_namespace,bundle.pattern.pattern_id,i)
        else:
            from_patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i)
            
        if to_arrival_time!=to_departure_time:
            to_patternstop_vx_name = "psv-%s-%03d-%03d-arrive"%(agency_namespace,bundle.pattern.pattern_id,i+1)
        else:
            to_patternstop_vx_name = "psv-%s-%03d-%03d"%(agency_namespace,bundle.pattern.pattern_id,i+1)
            
        gdb.add_edge( from_patternstop_vx_name, 
                      to_patternstop_vx_name, 
                      Crossing( (to_arrival_time-from_departure_time) ), 
                      cursor )
                      
    gdb.commit()

def gdb_load_gtfsdb_to_boardalight(gdb, agency_namespace, gtfsdb, agency_id, cursor, maxtrips=None, reporter=sys.stdout):

    # get graphserver.core.Timezone and graphserver.core.ServiceCalendars from gtfsdb for agency with given agency_id
    tz = Timezone.generate(gtfsdb.agency_timezone_name( agency_id ))
    sc = gtfsdb_to_service_calendar(gtfsdb, agency_id )

    # enter station vertices
    for stop_id, stop_name, stop_lat, stop_lon in gtfsdb.stops():
        station_vertex_label = "sta-%s"%stop_id
        reporter.write("adding station vertex '%s'\n"%station_vertex_label)
        gdb.add_vertex( station_vertex_label )
    
    # compile trip bundles from gtfsdb
    if reporter: reporter.write( "Compiling trip bundles...\n" )
    bundles = gtfsdb.compile_trip_bundles(maxtrips=maxtrips, reporter=reporter)

    # load bundles to graph
    if reporter: reporter.write( "Loading trip bundles into graph...\n" )
    n_bundles = len(bundles)
    for i, bundle in enumerate(bundles):
        if reporter: reporter.write( "%d/%d loading %s\n"%(i, n_bundles, bundle) )
        
        for service_id in [x.encode("ascii") for x in gtfsdb.service_ids()]:
            gdb_boardalight_load_bundle(gdb, agency_namespace, bundle, service_id, sc, tz, cursor)
            
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
            gdb.add_vertex( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id) )
            gdb.add_edge( "sta-%s"%stop_id, "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), hb )
            
        #add alight edges
        for trip_id, arrival_time, departure_time, stop_id, stop_sequence, stop_dist_traveled in stoptimes[1:]:
            gdb.add_vertex( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id) )
            gdb.add_edge( "hwv-%s-%s-%s"%(agency_namespace,stop_id, trip_id), "sta-%s"%stop_id, ha )
        
        #add crossing edges
        for (trip_id1, arrival_time1, departure_time1, stop_id1, stop_sequence1, stop_dist_traveled1), (trip_id2, arrival_time2, departure_time2, stop_id2, stop_sequence2,stop_dist_traveled2) in cons(stoptimes):
            gdb.add_edge( "hwv-%s-%s-%s"%(agency_namespace,stop_id1, trip_id1), "hwv-%s-%s-%s"%(agency_namespace,stop_id2, trip_id2), Crossing(arrival_time2-departure_time1) )
            
    # load connections
    if reporter: reporter.write( "Loading connections to graph...\n" )
    for stop_id1, stop_id2, conn_type, distance in gtfsdb.execute( "SELECT * FROM connections" ):
        gdb.add_edge( "sta-%s"%stop_id1, "sta-%s"%stop_id2, Street( conn_type, distance ) )
        gdb.add_edge( "sta-%s"%stop_id2, "sta-%s"%stop_id1, Street( conn_type, distance ) )
        
def main():
    usage = """usage: python gdb_import_gtfs.py [options] <graphdb_filename> <gtfsdb_filename> <agency_id>"""
    parser = OptionParser(usage=usage)
    parser.add_option("-n", "--namespace", dest="namespace", default="0",
                      help="agency namespace")
    parser.add_option("-m", "--maxtrips", dest="maxtrips", default=None, help="maximum number of trips to load")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 3:
        parser.print_help()
        exit(-1)
    
    graphdb_filename = args[0]
    gtfsdb_filename  = args[1]
    agency_id        = args[2]
    
    print "importing agency '%s' from gtfsdb '%s' into graphdb '%s'"%(agency_id, gtfsdb_filename, graphdb_filename)
    
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    gdb = GraphDatabase( graphdb_filename, overwrite=False )
    
    maxtrips = int(options.maxtrips) if options.maxtrips else None
    gdb_load_gtfsdb_to_boardalight(gdb, options.namespace, gtfsdb, agency_id, gdb.get_cursor(), maxtrips=maxtrips)
    gdb.commit()
    
    print "done"

if __name__ == '__main__':
    main()