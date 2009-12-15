from graphserver.util import TimeHelpers

class BoardEvent:
    def __init__(self, gtfsdb, timezone_name="America/Los_Angeles"):
        self.gtfsdb = gtfsdb
        self.timezone_name = timezone_name
        
    def __call__(self, vertex1, edge, vertex2):
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        print vertex1.payload, edge, vertex2.payload
        
        print "trip_id", trip_id
        
        route_desc = "-".join([str(x) for x in list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0]])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        loc = (lat,lon)
        return (what, where, when, loc)

class AlightEvent:
    def __init__(self, gtfsdb, timezone_name="America/Los_Angeles"):
        self.gtfsdb = gtfsdb
        self.timezone_name = timezone_name
        
    def __call__(self, vertex1, edge, vertex2):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        loc = (lat,lon)
        return (what, where, when, loc)

class HeadwayBoardEvent:
    def __init__(self, gtfsdb, timezone_name="America/Los_Angeles"):
        self.gtfsdb = gtfsdb
        self.timezone_name = timezone_name
        
    def __call__(self, vertex1, edge, vertex2):
        event_time = vertex2.payload.time
        trip_id = vertex2.payload.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = "-".join(list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        loc = (lat,lon)
        return (what, where, when, loc)

class HeadwayAlightEvent:
    def __init__(self, gtfsdb, timezone_name="America/Los_Angeles"):
        self.gtfsdb = gtfsdb
        self.timezone_name = timezone_name
        
    def __call__(self, vertex1, edge, vertex2):
        event_time = vertex1.payload.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        loc = (lat,lon)
        return (what, where, when, loc)

class StreetEvent:
    def __init__(self, timezone_name="America/Los_Angeles"):
        self.timezone_name = timezone_name
    
    def __call__(self, vertex1, edge, vertex2):
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex1.payload.time, self.timezone_name ))
        return ("Walk %s from %s to %s"%(edge.payload.length, vertex1.label, vertex2.label), "", when, None)