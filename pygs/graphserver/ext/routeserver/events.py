from graphserver.util import TimeHelpers
import graphserver.core
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.ext.osm.osmdb import OSMDB
try:
    import json
except ImportError:
    import simplejson as json

class NarrativeEvent:
    def __init__(self, what, where, when, geom):
        self.what = what
        self.where = where
        self.when = when
        self.geom = geom
        
    def to_jsonable(self):
        return  {'what':self.what,
                 'where':self.where,
                 'when':self.when,
                 'geom':self.geom}

class BoardEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
    
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.TripBoard)
    
    def __call__(self, vertex1, edge, vertex2, context):
        
        event_time = vertex2.state.time
        trip_id = vertex2.state.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = "-".join([str(x) for x in list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0]])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class DescribeCrossingAtAlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        # if the stop_sequence is the same before and after the TripAlight was crossed, it means the algorithm crossed in the forward
        # direction - because the stop_sequence doesn't get set on a forward alight. If this is true then this is the appropriate time
        # to describe the transit trip that led to this alighting
        return edge is not None \
               and isinstance(edge.payload, graphserver.core.TripAlight) \
               and vertex1.state.stop_sequence == vertex2.state.stop_sequence
        
    def __call__(self, vertex1, edge, vertex2, context):
        
        stop_sequence_of_boarding = vertex1.state.stop_sequence
        trip_id = vertex1.state.trip_id
        alighting_trip_id, alighting_time, alighting_stop_sequences = edge.payload.get_alighting_by_trip_id( trip_id )
        
        what = "Ride trip %s from stop_seq %s to stop_seq %s"%(trip_id, vertex1.state.stop_sequence, alighting_stop_sequences)
        where = None
        when = None
        geom = self.gtfsdb.shape_between( trip_id, vertex1.state.stop_sequence, alighting_stop_sequences )
        return NarrativeEvent(what, where, when, geom)

class AlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.TripAlight)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex1.state.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class HeadwayBoardEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayBoard)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex2.state.time
        trip_id = vertex2.state.trip_id
        stop_id = vertex1.label.split("-")[-1]
        
        route_desc = "-".join(list( self.gtfsdb.execute( "SELECT routes.route_short_name, routes.route_long_name FROM routes, trips WHERE routes.route_id=trips.route_id AND trip_id=?", (trip_id,) ) )[0])
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Board the %s"%route_desc
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class HeadwayAlightEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.HeadwayAlight)
        
    def __call__(self, vertex1, edge, vertex2, context):
        event_time = vertex1.state.time
        stop_id = vertex2.label.split("-")[-1]
        
        stop_desc = list( self.gtfsdb.execute( "SELECT stop_name FROM stops WHERE stop_id = ?", (stop_id,) ) )[0][0]
        lat, lon = list( self.gtfsdb.execute( "SELECT stop_lat, stop_lon FROM stops WHERE stop_id = ?", (stop_id,) ) )[0]
        
        what = "Alight"
        where = stop_desc
        when = "about %s"%str(TimeHelpers.unix_to_localtime( event_time, self.timezone_name ))
        geom = (lon,lat)
        return NarrativeEvent(what, where, when, geom)

class StreetEvent:
    def __init__(self, osmdb_filename, timezone_name="America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Street)
    
    def __call__(self, vertex1, edge, vertex2, context):
        # adds to the variable set up by the StreetStartEvent
        geometry_chunk = self.osmdb.edge( edge.payload.name )[5]
      
        if edge.payload.reverse_of_source:
	    context['streetgeom'].extend( reversed( geometry_chunk ) )
	else:
	    context['streetgeom'].extend( geometry_chunk )
            
        context['sumlength'] += edge.payload.length
        context['sumrise'] += edge.payload.rise
        context['sumfall'] += edge.payload.fall
        
        return None
        
class CrossingEvent:
    def __init__(self, gtfsdb_filename, timezone_name="America/Los_Angeles"):
        self.gtfsdb = GTFSDatabase( gtfsdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(vertex1, edge, vertex2):
        return edge is not None and isinstance(edge.payload, graphserver.core.Crossing)
        
    def __call__(self, v1, e, v2, context):
        trip_id = v1.state.trip_id
        return (str(v1.state), str(e), str(v2.state))

from math import asin, acos, degrees

def mag(vec):
    return sum([a**2 for a in vec])**0.5
 
def vector_angle( p1, p2, p3, p4 ):
    a = ((p2[0]-p1[0]),(p2[1]-p1[1]))
    b = ((p4[0]-p3[0]),(p4[1]-p3[1]))
    
    a_cross_b = a[0]*b[1] - a[1]*b[0]
    a_dot_b = a[0]*b[0] + a[1]*b[1]
    
    sin_theta = a_cross_b/(mag(a)*mag(b))
    cos_theta = a_dot_b/(mag(a)*mag(b))
    
    # if the dot product is positive, the turn is forward, else, backwards
    if a_dot_b >= 0:
        return -degrees(asin(sin_theta))
    else:
        # if the cross product is negative, the turn is to the right, else, left
        if a_cross_b <= 0:
            return degrees(acos(cos_theta))
        else:
            return -degrees(acos(cos_theta))
            
def angle_from_north( p3, p4 ):
    p1 = [0,0]
    p2 = [0,1]
    
    return vector_angle( p1, p2, p3, p4 )
    
def description_from_north( p3, p4 ):
    afn = angle_from_north( p3, p4 )
    if afn > -22.5 and afn <= 22.5:
        return "north"
    if afn > 22.5 and afn <= 67.5:
        return "northeast"
    if afn > 67.5 and afn <= 112.5:
        return "east"
    if afn > 112.5 and afn <= 157.5:
        return "southeast"
    if afn > 157.5:
        return "south"
        
    if afn < -22.5 and afn >= -67.5:
        return "northwest"
    if afn < -67.5 and afn >= -112.5:
        return "west"
    if afn < -112.5 and afn >= -157.5:
        return "southwest"
    if afn < -157.5:
        return "south"
            
def test_vector_angle():
    assert vector_angle( (0,0), (0,1), (0,1), (0,2) ) == 0.0
    assert round(vector_angle( (0,0), (0,1), (0,1), (5,10) ),4) == 29.0546
    assert vector_angle( (0,0), (0,1), (0,1), (1,1)) == 90
    assert round(vector_angle( (0,0), (0,1), (0,1), (1,0.95) ),4) == 92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (0,0) ) == 180
    assert round(vector_angle( (0,0), (0,1), (0,1), (-1, 0.95) ),4) == -92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (-1, 1) ) == -90
    assert round( vector_angle( (0,0), (0,1), (0,1), (-5,10) ), 4 ) == -29.0546
 
def turn_narrative( p1, p2, p3, p4 ):
    angle = vector_angle( p1, p2, p3, p4 )
    turn_mag = abs(angle)
    
    if turn_mag < 7:
        return "continue"
    elif turn_mag < 20:
        verb = "slight"
    elif turn_mag < 120:
        verb = ""
    else:
        verb = "sharp"
        
    if angle > 0:
        direction = "right"
    else:
        direction = "left"
        
    return ("%s %s"%(verb, direction)).strip()
        
class StreetStartEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge1 is None or not isinstance(edge1.payload, graphserver.core.Street)) and \
               (edge2 and isinstance(edge2.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):
        context['streetgeom'] = []
        context['sumlength'] = 0
        context['sumrise'] = 0
        context['sumfall'] = 0
        context['lastturntime'] = vertex.state.time
        
        osm_way2 = edge2.payload.name.split("-")[0]
        street_name2 = self.osmdb.way( osm_way2 ).tags.get('name', "unnamed")
        
        osm_id = vertex.label.split("-")[1]
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        osm_edge2 = self.osmdb.edge( edge2.payload.name )
        osm_edge2_startnode = osm_edge2[2]
        osm_edge2_geom = osm_edge2[5]
        if osm_id != osm_edge2_startnode:
            osm_edge2_geom.reverse()
        startseg = osm_edge2_geom[:2]
        direction = description_from_north( startseg[0], startseg[1] )
        
        what = "start walking"
        where = "on %s facing %s"%(street_name2, direction)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = [osm_node_lon, osm_node_lat]
        return NarrativeEvent(what,where,when,geom)
        
class StreetEndEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge1 is not a street and edge2 is
        return (edge2 is None or not isinstance(edge2.payload, graphserver.core.Street)) and \
               (edge1 and isinstance(edge1.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):
        osm_way1 = edge1.payload.name.split("-")[0]
        street_name1 = self.osmdb.way( osm_way1 ).tags.get('name', "unnamed")
        
        osm_id = vertex.label.split("-")[1]
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        average_speed = context['sumlength']/(vertex.state.time-context['lastturntime']) if vertex.state.time-context['lastturntime']>0 else 100000000
        what = "arrive walking after %dm, %0.1f rise, %0.1f fall (%0.1fm/s)"%(context['sumlength'], context['sumrise'], context['sumfall'], average_speed)
        where = "on %s"%(street_name1)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = [osm_node_lon, osm_node_lat]
        return NarrativeEvent(what,where,when,geom)
        
class GeomAtStreetEndEvent:
    def __init__(self, timezone_name = "America/Los_Angeles"):
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        # if edge2 is not a street and edge1 is
        return (edge2 is None or not isinstance(edge2.payload, graphserver.core.Street)) and \
               (edge1 and isinstance(edge1.payload, graphserver.core.Street))
    
    def __call__(self, edge1, vertex, edge2, context):        
        what = "walk a bunch"
        where = None
        when = None
        geom = context['streetgeom']
        return NarrativeEvent(what,where,when,geom)
        
class StreetTurnEvent:
    def __init__(self, osmdb_filename, timezone_name = "America/Los_Angeles"):
        self.osmdb = OSMDB( osmdb_filename )
        self.timezone_name = timezone_name
        
    @staticmethod
    def applies_to(edge1, vertex, edge2):
        return edge1 and edge2 and isinstance(edge1.payload, graphserver.core.Street) and isinstance(edge2.payload, graphserver.core.Street) \
               and edge1.payload.way != edge2.payload.way
    
    def __call__(self, edge1, vertex, edge2, context):
        
        osm_id = vertex.label.split("-")[1]
        
        # figure out which direction to turn
        osm_way_id1 = edge1.payload.name.split("-")[0]
        osm_way_id2 = edge2.payload.name.split("-")[0]
        
        osm_edge1 = self.osmdb.edge( edge1.payload.name )
        osm_edge2 = self.osmdb.edge( edge2.payload.name )
        
        osm_edge1_endnode = osm_edge1[3]
        osm_edge2_startnode = osm_edge2[2]
        
        osm_edge1_geom = osm_edge1[5]
        osm_edge2_geom = osm_edge2[5]
        
        if osm_id != osm_edge1_endnode:
            osm_edge1_geom.reverse()
             
        if osm_id != osm_edge2_startnode:
            osm_edge2_geom.reverse()
            
        endseg = osm_edge1_geom[-2:]
        startseg = osm_edge2_geom[:2]
        
        direction = turn_narrative( endseg[0], endseg[1], startseg[0], startseg[1] )
                
        street_name1 = self.osmdb.way( osm_way_id1 ).tags.get("name", "unnamed")
        street_name2 = self.osmdb.way( osm_way_id2 ).tags.get("name", "unnamed")
        
        osm_node_id, osm_node_tags, osm_node_lat, osm_node_lon, osm_node_refcount = self.osmdb.node( osm_id )
        
        average_speed = context['sumlength']/(vertex.state.time-context['lastturntime']) if vertex.state.time-context['lastturntime']>0 else 100000000
        what = "%s onto %s after %dm, %0.1fm rise, %0.1fm fall (%0.1fm/s)"%(direction, street_name2, context['sumlength'], context['sumrise'], context['sumfall'], average_speed)
        where = "%s & %s"%(street_name1, street_name2)
        when = "about %s"%str(TimeHelpers.unix_to_localtime( vertex.state.time, self.timezone_name ))
        geom = (osm_node_lon, osm_node_lat)
        
        context['sumlength'] = 0
        context['sumrise'] = 0
        context['sumfall'] = 0
        context['lastturntime'] = vertex.state.time
        return NarrativeEvent(what,where,when,geom)
    
class AllVertexEvent:
    def __init__(self):
        pass
        
    @staticmethod
    def applies_to(e1, v, e2):
        return True
        
    def __call__(self, e1, v, e2, context):
        return NarrativeEvent("vertex", str(e1), str(v), str(e2))
        
class AllEdgeEvent:
    def __init__(self):
        pass
        
    @staticmethod
    def applies_to(v1, e, v2):
        return True
        
    def __call__(self, v1, e, v2, context):
        return NarrativeEvent("edge", str(v1), str(e), str(v2))
