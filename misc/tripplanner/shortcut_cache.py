from graphserver.core import ContractionHierarchy, Combination
from graphserver.ext.osm.osmdb import OSMDB, pack_coords, unpack_coords
from graphserver.graphdb import GraphDatabase
from glineenc import encode_pairs
from graphserver.ext.osm.profiledb import ProfileDB
from profile import Profile, cons

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

def reincarnate_ch(basename):
    chdowndb = GraphDatabase( basename+".down.gdb" )
    chupdb = GraphDatabase( basename+".up.gdb" )
    
    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()
    
    return ContractionHierarchy(upgg, downgg)
    
def unpack_streets(ep):
    if ep.__class__ == Combination:
        return ep.unpack()
    else:
        return [ep]
        
def get_street_geom( osmdb, street ):
    id, parent_id, node1, node2, distance, geom, tags = osmdb.edge( street.name )
    
    if street.reverse_of_source:
        geom.reverse()
        
    return geom
    
def get_street_profile( profiledb, street ):
    profile_seg = profiledb.get( street.name )
    
    if street.reverse_of_source:
        profile_seg.reverse()
        
    return profile_seg
    
def get_ep_profile( profiledb, edgepayload ):
    combiner = Profile()
    
    streets = unpack_streets( edgepayload )
    for street in streets:
        combiner.add( get_street_profile(profiledb, street) )

    return combiner.concat() #reduce( lambda x,y:x+y, profile )
    
def get_ep_geom( osmdb, edgepayload ):
    streets = unpack_streets( edgepayload )
    geoms = [get_street_geom(osmdb, street) for street in streets]
    return reduce( lambda x,y:x+y, geoms )

def get_turn_narrative( osmdb, street1, street2, running_totals ):
    #street1length = edgerec1[4]
    #running_totals[0] = running_totals[0]+street1length
    #running_totals[1] = running_totals[1]+street1length
    
    if street1.way == street2.way:
        return None
        
    edgerec2 = osmdb.edge( street2.name )
    edgerec1 = osmdb.edge( street1.name )
    
    #name1 = edgerec1[6].get( "name", "nameless" )
    name2 = edgerec2[6].get( "name", "nameless" )
    
    geom1 = edgerec1[5]
    geom2 = edgerec2[5]
    if street1.reverse_of_source:
        geom1.reverse()
    if street2.reverse_of_source:
        geom2.reverse()
    p1, p2 = geom1[-2:]
    p3, p4 = geom2[:2]
    
    turn_type = turn_narrative( p1, p2, p3, p4 )
    
    ret = (turn_type, name2, running_totals[0], running_totals[1], 0, p2)
    #running_totals[0] = 0
    return ret
        
def get_full_route_narrative( osmdb, edgepayloads ):
    streets = []
    for ep in edgepayloads:
        streets.extend( unpack_streets( ep ) )
        
    ret = []
    
    #get start of narrative
    rec1 = osmdb.edge( streets[0].name )
    geom1 = rec1[5]
    if streets[0].reverse_of_source :
        p1, p2 = geom1[-1], geom1[-2]
    else:
        p1, p2 = geom1[0], geom1[1]
    streetname = rec1[6].get( "name", "nameless" )
    dfn = description_from_north( p1, p2 )
    
    ret.append( ("start "+dfn, streetname, 0, 0, 0, p1) )
    
    running_totals = [0,0] #distance from last turn, distance from beginning
    
    # get all turns in narrative
    for s1, s2 in cons(streets):
        nn = get_turn_narrative( osmdb, s1, s2, running_totals )
        if nn is not None:
            ret.append( nn )
            
    # get length of the last street, to find the total length
    finalrec = osmdb.edge( streets[-1].name )
    finalroadlength = finalrec[4]
    totallength = running_totals[1]+finalroadlength
            
    return ret, totallength
    
def get_encoded_ep_geom( osmdb, edgepayload ):
    return encode_pairs( [(lat, lon) for lon, lat in get_ep_geom( osmdb, edgepayload )] )

import os
import sqlite3
class ShortcutCache:
    def __init__(self, sqlite_filename, overwrite=False):
        if overwrite:
            if os.path.exists(sqlite_filename):
                os.remove( sqlite_filename )
        elif not os.path.exists(sqlite_filename):
            overwrite = True # force an init of the tables
                
        self.conn = sqlite3.connect(sqlite_filename)
        
        if overwrite:
            self.setup()
            
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE ep_geoms (id TEXT UNIQUE ON CONFLICT IGNORE, geom TEXT, profile TEXT)" )
        self.conn.commit()
        c.close()
        
        self.index()
        
    def index(self):
        c = self.conn.cursor()
        c.execute( "CREATE INDEX ep_geoms_id ON ep_geoms (id)" )
        self.conn.commit()
        c.close()
        
    def execute(self, query, args=None):
        
        c = self.conn.cursor()
        
        if args:
            c.execute( query, args )
        else:
            c.execute( query )
            
        for record in c:
            yield record
        c.close()
    
    def ingest( self, osmdb, profiledb, gg ):
        c = self.conn.cursor()
        
        n = gg.size
        for i, vv in enumerate( gg.vertices ):
            if i%(n/100)==0: print "%d/%d"%(i+1,n)
            
            for ee in vv.outgoing:
                epid, ep = ee.payload.external_id, ee.payload
                geom = get_ep_geom( osmdb, ep )
                profile = get_ep_profile( profiledb, ep )
                
                self.put( epid, geom, profile, c )
                
        self.conn.commit()
        c.close()
    
    def put( self, external_id, geom, profile, c ):
        c.execute( "INSERT INTO ep_geoms (id, geom, profile) VALUES (?, ?, ?)", (external_id, pack_coords( geom ), pack_coords( profile )) )
        
    def get( self, external_id ):
        packed_geom, packed_profile = list(self.execute( "SELECT geom, profile FROM ep_geoms WHERE id=?", (external_id,) ))[0]
        return unpack_coords( packed_geom ), unpack_coords( packed_profile )

import sys

def selftest():
    assert description_from_north( (0,0), (0,1) ) == "north"
    assert description_from_north( (0,0), (1,1) ) == "northeast"
    assert description_from_north( (0,0), (1,0) ) == "east"
    assert description_from_north( (0,0), (1,-1) ) == "southeast"
    assert description_from_north( (0,0), (0,-1) ) == "south"
    assert description_from_north( (0,0), (-1,-1) ) == "southwest"
    assert description_from_north( (0,0), (-1,0) ) == "west"
    assert description_from_north( (0,0), (-1,1) ) == "northwest"
    
if __name__=='__main__':
    #selftest()
    
    print "usage: python shortcut_cache.py basename"
    
    basename = sys.argv[1]
    
    ch = reincarnate_ch( basename )
    osmdb = OSMDB( basename+".osmdb" )
    profiledb = ProfileDB( basename+".profiledb" )
    scc = ShortcutCache( basename+".scc", overwrite=True )
    
    scc.ingest( osmdb, profiledb, ch.upgraph )
    scc.ingest( osmdb, profiledb, ch.downgraph )
        