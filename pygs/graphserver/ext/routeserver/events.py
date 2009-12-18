from graphserver.util import TimeHelpers
import graphserver.core
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB


class BoardEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
    
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.TripBoard)
    
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
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Alight)
        
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
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayBoard)
        
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
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayAlight)
        
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
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Street)
    
    def __call__(self, vertex1, edge, vertex2):
        what = "walk %s meters"%edge.payload.length
        return (what,None,None)
        
class StreetStartEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge1 is None or not isinstance(edge1.payload, graphserver.core.Street)) and \
               (edge2 and isinstance(edge2.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2):
        osm_way2 = edge2.payload.name.split("-")[0]
        street_name2 = self.osmdb.way( osm_way2 ).tags['name']
        
        what = "start"
        where = "on %s facing DIRECTION"%(street_name2)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.payload.time, self.timezone_name ))
        return (what,where,when)
        
class StreetEndEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge2 is None or not isinstance(edge2.payload, graphserver.core.Street)) and \
               (edge1 and isinstance(edge1.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2):
        osm_way1 = edge2.payload.name.split("-")[0]
        street_name1 = self.osmdb.way( osm_way2 ).tags['name']
        
        what = "end"
        where = "on %s facing DIRECTION"%(street_name1)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.payload.time, self.timezone_name ))
        return (what,where,when)
        
class StreetTurnEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        return edge1 and edge2 and isinstance(edge1.payload, graphserver.core.Street) and isinstance(edge2.payload, graphserver.core.Street) \
               and edge1.payload.way != edge2.payload.way
    
    def __call__(self, edge1, vertex, edge2):
        osm_way1 = edge1.payload.name.split("-")[0]
        osm_way2 = edge2.payload.name.split("-")[0]
        
        street_name1 = self.osmdb.way( osm_way1 ).tags['name']
        street_name2 = self.osmdb.way( osm_way2 ).tags['name']
        
        what = "turn DIRECTION onto %s"%(street_name2)
        where = "%s & %s"%(street_name1, street_name2)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.payload.time, self.timezone_name ))
        return (what,where,when)
    