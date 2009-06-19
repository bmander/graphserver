import csv
import sqlite3
import sys
import os
from zipfile import ZipFile
from codecs import iterdecode
import datetime

class UTF8TextFile(object):
    def __init__(self, fp):
        self.fp = fp
        
    def next(self):
        return self.fp.next().encode( "ascii", "backslashreplace" )
        
    def __iter__(self):
        return self

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])
        
def parse_gtfs_time(timestr):
    return (lambda x:int(x[0])*3600+int(x[1])*60+int(x[2]))(timestr.split(":")) #oh yes I did
    
def parse_gtfs_date(datestr):
    return (int(datestr[0:4]), int(datestr[4:6]), int(datestr[6:8]))

def create_table(cc, gtfs_basename, header):
    # Create stoptimes table
    sqlite_field_definitions = ["%s %s"%(field_name, field_type if field_type else "TEXT") for field_name, field_type, field_converter in header]
    cc.execute("create table %s (%s)"%(gtfs_basename,",".join(sqlite_field_definitions)))

def load_gtfs_table_to_sqlite(fp, gtfs_basename, cc, header=None):
    """header is iterable of (fieldname, fieldtype, processing_function). For example, (("stop_sequence", "INTEGER", int),). 
    "TEXT" is default fieldtype. Default processing_function is lambda x:x"""
    
    ur = UTF8TextFile( fp )
    rd = csv.reader( ur )

    # create map of field locations in gtfs header to field locations as specified by the table definition
    gtfs_header = next(rd)
    gtfs_field_indices = dict(zip(gtfs_header, range(len(gtfs_header))))
    
    field_name_locations = [gtfs_field_indices[field_name] if field_name in gtfs_field_indices else None for field_name, field_type, field_converter in header]
    field_converters = [field_definition[2] for field_definition in header]
    field_operator = list(zip(field_name_locations, field_converters))

    # populate stoptimes table
    insert_template = 'insert into %s (%s) values (%s)'%(gtfs_basename,",".join([x[0] for x in header]), ",".join(["?"]*len(header)))
    print( insert_template )
    for i, line in enumerate(rd):
        #print( i%50, line )
        if i%5000==0: print(i)
               
        # carry on quietly if there's a blank line in the csv
        if line == []:
            continue
        
        _line = []
        for i, converter in field_operator:
            if i is not None:
                if converter:
                    _line.append( converter(line[i]) )
                else:
                    _line.append( line[i] )
            else:
                _line.append( None )
                
        cc.execute(insert_template, _line)
        
class Pattern:
    def __init__(self, pattern_id, stop_ids, layovers, crossings):
        self.pattern_id = pattern_id
        self.stop_ids = stop_ids
        self.layovers = layovers
        self.crossings = crossings
    
    @property
    def signature(self):
        return (tuple(self.stops), tuple(self.crossings), tuple(self.layovers))

class TripBundle:
    def __init__(self, gtfsdb, pattern):
        self.gtfsdb = gtfsdb
        self.pattern = pattern
        self.trip_ids = []
        
    def add_trip(self, trip_id):
        self.trip_ids.append( trip_id )
        
    def stop_time_bundle( self, stop_sequence, service_id ):
        c = self.gtfsdb.conn.cursor()
        
        query = """
SELECT stop_times.* FROM stop_times, trips 
  WHERE stop_times.trip_id = trips.trip_id 
        AND trips.trip_id IN (%s) 
        AND trips.service_id = ? 
        AND stop_times.stop_sequence = ? 
  ORDER BY departure_time"""%(",".join(["'%s'"%x for x in self.trip_ids]))
      
        c.execute(query, (service_id,stop_sequence))
        
        return list(c)
        
    def stop_time_bundles( self, service_id ):
        i = 1
        while True:
            yld = self.stop_time_bundle( i, service_id )
            if len(yld)==0:
                break
            else:
                yield yld
            
            i += 1
            
    def __repr__(self):
        return "<TripBundle n_trips: %d n_stops: %d>"%(len(self.trip_ids), len(self.pattern_signature[0]))

class GTFSDatabase:
    TRIPS_DEF = ("trips", (("route_id",   None, None),
                           ("trip_id",    None, None),
                           ("service_id", None, None),
                           ("shape_id", None, None)))
    ROUTES_DEF = ("routes", (("route_id", None, None),
                             ("route_short_name", None, None),
                             ("route_long_name", None, None)) )
    STOP_TIMES_DEF = ("stop_times", (("trip_id", None, None), 
                                     ("arrival_time", "INTEGER", parse_gtfs_time),
                                     ("departure_time", "INTEGER", parse_gtfs_time),
                                     ("stop_id", None, None),
                                     ("stop_sequence", "INTEGER", None),
                                     ("shape_dist_traveled", "FLOAT", None)))
    STOPS_DEF = ("stops", (("stop_id", None, None),
                           ("stop_name", None, None),
                           ("stop_lat", "FLOAT", None),
                           ("stop_lon", "FLOAT", None)) )
    CALENDAR_DEF = ("calendar", (("service_id", None, None),
                                 ("monday", "INTEGER", None),
                                 ("tuesday", "INTEGER", None),
                                 ("wednesday", "INTEGER", None),
                                 ("thursday", "INTEGER", None),
                                 ("friday", "INTEGER", None),
                                 ("saturday", "INTEGER", None),
                                 ("sunday", "INTEGER", None),
                                 ("start_date", None, None),
                                 ("end_date", None, None)) )
    CAL_DATES_DEF = ("calendar_dates", (("service_id", None, None),
                                        ("date", None, None),
                                        ("exception_type", "INTEGER", None)) )
    AGENCY_DEF = ("agency", (("agency_id", None, None),
                             ("agency_name", None, None),
                             ("agency_url", None, None),
                             ("agency_timezone", None, None)) )
                             
    FREQUENCIES_DEF = ("frequencies", (("trip_id", None, None),
                                       ("start_time", "INTEGER", parse_gtfs_time),
                                       ("end_time", "INTEGER", parse_gtfs_time),
                                       ("headway_secs", "INTEGER", None)) )
    CONNECTIONS_DEF = ("connections", (("stop_id1", None, None),
                                       ("stop_id2", None, None),
                                       ("type", None, None),
                                       ("distance", "INTEGER", None)))
    SHAPES_DEF = ("shapes", (("shape_id", None, None),
                               ("shape_pt_lat", "FLOAT", None),
                               ("shape_pt_lon", "FLOAT", None),
                               ("shape_pt_sequence", "INTEGER", None),
                               ("shape_dist_traveled", "FLOAT", None)))
    
    GTFS_DEF = (TRIPS_DEF, 
                STOP_TIMES_DEF, 
                STOPS_DEF, 
                CALENDAR_DEF, 
                CAL_DATES_DEF, 
                AGENCY_DEF, 
                FREQUENCIES_DEF, 
                ROUTES_DEF, 
                CONNECTIONS_DEF,
                SHAPES_DEF)
    
    def __init__(self, sqlite_filename, overwrite=False):
        if overwrite:
            try:
                os.remove(sqlite_filename)
            except:
                pass
        
        self.conn = sqlite3.connect( sqlite_filename )

    def load_gtfs(self, gtfs_filename, reporter=None):
        c = self.conn.cursor()

        zf = ZipFile( gtfs_filename )

        for tablename, table_def in self.GTFS_DEF:
            if reporter: reporter.write( "creating table %s\n"%tablename )
            create_table( c, tablename, table_def )
            if reporter: reporter.write( "loading table %s\n"%tablename )
            
            try:
                trips_file = iterdecode( zf.open(tablename+".txt"), "utf-8" )
                load_gtfs_table_to_sqlite(trips_file, tablename, c, table_def)
            except KeyError:
                if reporter: reporter.write( "NOTICE: GTFS feed has no file %s.txt, cannot load\n"%tablename )
    
        self._create_indices(c)
        self.conn.commit()
        c.close()

    def _create_indices(self, c):
        
        c.execute( "CREATE INDEX stop_times_trip_id ON stop_times (trip_id)" )
        c.execute( "CREATE INDEX trips_trip_id ON trips (trip_id)" )
        c.execute( "CREATE INDEX stops_stop_lat ON stops (stop_lat)" )
        c.execute( "CREATE INDEX stops_stop_lon ON stops (stop_lon)" )

    def stops(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT * FROM stops" )
        ret = list(c)
        
        c.close()
        return ret
        
    def stop(self, stop_id):
        c = self.conn.cursor()
        c.execute( "SELECT * FROM stops WHERE stop_id = ?", (stop_id,) )
        ret = next(c)
        c.close()
        return ret
        
    def count_stops(self):
        c = self.conn.cursor()
        c.execute( "SELECT count(*) FROM stops" )
        
        ret = next(c)[0]
        c.close()
        return ret

    def compile_trip_bundles(self, reporter=None):
        
        c = self.conn.cursor()

        patterns = {}
        bundles = {}

        c.execute( "SELECT count(*) FROM trips" )
        n_trips = next(c)[0]

        c.execute( "SELECT trip_id FROM trips" )
        for i, (trip_id,) in enumerate(c):
            if reporter and i%(n_trips//50)==0: reporter.write( "%d/%d trips grouped by %d patterns\n"%(i,n_trips,len(bundles)))
            
            d = self.conn.cursor()
            d.execute( "SELECT trip_id, arrival_time, departure_time, stop_id FROM stop_times WHERE trip_id=? ORDER BY stop_sequence", (trip_id,) )
            
            stop_times = list(d)
            
            stop_ids = [stop_id for trip_id, arrival_time, departure_time, stop_id in stop_times]
            layovers = [departure_time-arrival_time for trip_id, arrival_time, departure_time, stop_id in stop_times]
            crossings = [arrival_time2 - departure_time1 for (trip_id1, arrival_time1, departure_time1, stop_id1),
                                                             (trip_id2, arrival_time2, departure_time2, stop_id2) in cons(stop_times)]
            pattern_signature = (tuple(stop_ids), tuple(layovers), tuple(crossings))
            
            if pattern_signature not in patterns:
                pattern = Pattern( len(patterns), stop_ids, layovers, crossings )
                patterns[pattern_signature] = pattern
            else:
                pattern = patterns[pattern_signature]
                
            if pattern not in bundles:
                bundles[pattern] = TripBundle( self, pattern )
            
            bundles[pattern].add_trip( trip_id )
            
            #if i==10:
            #    break

        c.close()
        
        return bundles.values()
        
    def nearby_stops(self, lat, lng, range):
        c = self.conn.cursor()
        
        c.execute( "SELECT * FROM stops WHERE stop_lat BETWEEN ? AND ? AND stop_lon BETWEEN ? And ?", (lat-range, lat+range, lng-range, lng+range) )
        
        for row in c:
            yield row

    def extent(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT min(stop_lon), min(stop_lat), max(stop_lon), max(stop_lat) FROM stops" )
        
        ret = next(c)
        c.close()
        return ret
        
    def execute(self, query, args=None):
        
        c = self.conn.cursor()
        
        if args:
            c.execute( query, args )
        else:
            c.execute( query )
            
        for record in c:
            yield record
        c.close()
        
    def agency_timezone_name(self, agency_id_or_name=None):

        if agency_id_or_name is None:
            agency_timezone_name = list(self.execute( "SELECT agency_timezone FROM agency LIMIT 1" ))
        else:
            agency_timezone_name = list(self.execute( "SELECT agency_timezone FROM agency WHERE agency_id=? OR agency_name=?", (agency_id_or_name,agency_id_or_name) ))
        
        return agency_timezone_name[0][0]
        
    def day_bounds(self):
        daymin = list( self.execute("select min(departure_time) from stop_times") )[0][0]
        daymax = list( self.execute("select max(arrival_time) from stop_times") )[0][0]
        
        return (daymin, daymax)
        
    def date_range(self):
        start_date, end_date = list( self.execute("select min(start_date), max(end_date) from calendar") )[0]
        
        start_date = start_date or "99999999" #sorted greater than any date
        end_date = end_date or "00000000" #sorted earlier than any date
        
        first_exception_date, last_exception_date = list( self.execute("select min(date), max(date) from calendar_dates WHERE exception_type=1") )[0]
          
        first_exception_date = first_exception_date or "99999999"
        last_exceptoin_date = last_exception_date or "00000000"
        
        start_date = min(start_date, first_exception_date)
        end_date = max(end_date, last_exception_date )

        return datetime.date( *parse_gtfs_date(start_date) ), datetime.date( *parse_gtfs_date(end_date) )
    
    DOWS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    DOW_INDEX = dict(zip(range(len(DOWS)),DOWS))
    
    def service_periods(self, datetime):
        # Get the gtfs date range. If the datetime is out of the range, no service periods are in effect
        start_date, end_date = self.date_range()
        if datetime < start_date or datetime > end_date:
            return []
        
        # Use the day-of-week name to query for all service periods that run on that day
        dow_name = self.DOW_INDEX[datetime.weekday()]
        sids = set( [x[0] for x in self.execute( "SELECT * FROM calendar WHERE %s=1"%dow_name )] )
            
        # For each exception on the given datetime, add or remove service_id to the accumulating list
        datetimestr = datetime.strftime( "%Y%m%d" )
        for exception_sid, exception_type in self.execute( "select service_id, exception_type from calendar_dates WHERE date = ?", (datetimestr,) ):
            if exception_type == 1:
                sids.add( exception_sid )
            elif exception_type == 2:
                if exception_sid in sids:
                    sids.remove( exception_sid )
                
        return list(sids)
        
    def service_ids(self):
        query = "SELECT DISTINCT service_id FROM (SELECT service_id FROM calendar UNION SELECT service_id FROM calendar_dates)"
        
        return [x[0] for x in self.execute( query )]
    
    def shape(self, shape_id):
        query = "SELECT shape_pt_lon, shape_pt_lat, shape_dist_traveled from shapes where shape_id = %s order by shape_pt_sequence" % shape_id
        
        return list(self.execute( query ))
    
    def shape_between(self, trip_id, stop1, stop2):
        query = """SELECT t.shape_id, st.shape_dist_traveled, st.stop_id, st.stop_sequence
                     FROM trips t 
                     JOIN stop_times st ON st.trip_id = t.trip_id 
                     WHERE t.trip_id = %s and (st.stop_id = '%s' or st.stop_id = '%s')
                     ORDER BY stop_sequence""" % (trip_id, stop1, stop2)
        
        distances = []
        shape_id = None
        started = None
        for x in self.execute( query ):
            if not started and x[2] == stop1:
                shape_id = x[0]
                started = True            
                distances.append(x[1])
            
            if started and stop2 == x[2]:
                distances.append(x[1])
                break
            
        if not shape_id:
            return None
        
        t_min = min(distances)
        t_max = max(distances)
        
        shape = []
        last = None
        total_traveled = 0
        for pt in self.shape(shape_id):
            dist_traveled = pt[2]
            if dist_traveled > t_min and dist_traveled < t_max: 
                if len(shape) == 0 and total_traveled != 0 and t_min != 0 and dist_traveled - total_traveled != 0:
                    # interpolate first node:
                    percent_along = (dist_traveled - t_min) / (dist_traveled - total_traveled)
                    shape.append((last[0] + (pt[0] - last[0])*percent_along,
                                  last[1] + (pt[1] - last[1])*percent_along))
                else:                    
                    shape.append(last)
                    last = (pt[0],pt[1])
            elif dist_traveled > t_max:
                # calculate the differnce and interpolate
                percent_along = (dist_traveled - t_max) / (dist_traveled - total_traveled)
                shape.append((last[0] + (pt[0] - last[0])*percent_along,
                              last[1] + (pt[1] - last[1])*percent_along))
                return shape
            else:
                last = (pt[0],pt[1])
            total_traveled = dist_traveled
        
        return shape

def main_inspect_gtfsdb():
    from sys import argv
    
    if len(argv) < 2:
        print "usage: python gtfsdb.py gtfsdb_filename [query]"
        exit()
    
    gtfsdb_filename = argv[1]
    gtfsdb = GTFSDatabase( gtfsdb_filename )
    
    if len(argv) == 2:
        for table_name, fields in gtfsdb.GTFS_DEF:
            print "Table: %s"%table_name
            for field_name, field_type, field_converter in fields:
                print "\t%s %s"%(field_type, field_name)
        exit()
    
    query = argv[2]
    for record in gtfsdb.execute( query ):
        print record
    
    #for stop_id, stop_name, stop_lat, stop_lon in gtfsdb.stops():
    #    print( stop_lat, stop_lon )
    #    gtfsdb.nearby_stops( stop_lat, stop_lon, 0.05 )
    #    break
    
    #bundles = gtfsdb.compile_trip_bundles()
    #for bundle in bundles:
    #    for departure_set in bundle.iter_departures("WKDY"):
    #        print( departure_set )
    #    
    #    #print( len(bundle.trip_ids) )
    #    sys.stdout.flush()

    pass

def main_build_gtfsdb():
    if len(sys.argv) < 3:
        print "Converts GTFS file to GTFS-DB, which is super handy\nusage: python process_gtfs.py gtfs_filename, gtfsdb_filename"
        exit()
    
    gtfsdb_filename = sys.argv[2]
    gtfs_filename = sys.argv[1]
 
    gtfsdb = GTFSDatabase( gtfsdb_filename, overwrite=True )
    gtfsdb.load_gtfs( gtfs_filename, reporter=sys.stdout )


if __name__=='__main__': main_inspect_gtfsdb()
