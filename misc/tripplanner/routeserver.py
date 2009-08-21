from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions, ContractionHierarchy
import time
import sys
import graphserver
from graphserver.util import TimeHelpers
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.osm.profiledb import ProfileDB
try:
  import json
except ImportError:
  import simplejson as json
from math import asin, acos, degrees
import settings
from glineenc import encode_pairs

def reincarnate_ch(basename):
    chdowndb = GraphDatabase( basename+".down.gdb" )
    chupdb = GraphDatabase( basename+".up.gdb" )
    
    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()
    
    return ContractionHierarchy(upgg, downgg)

def mag(vec):
    return sum([a**2 for a in vec])**0.5
        
def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

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
        
    return "%s %s"%(verb, direction)
    
def test_vector_angle():
    assert vector_angle( (0,0), (0,1), (0,1), (0,2) ) == 0.0
    assert round(vector_angle( (0,0), (0,1), (0,1), (5,10) ),4) == 29.0546
    assert vector_angle( (0,0), (0,1), (0,1), (1,1)) == 90
    assert round(vector_angle( (0,0), (0,1), (0,1), (1,0.95) ),4) == 92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (0,0) ) == 180
    assert round(vector_angle( (0,0), (0,1), (0,1), (-1, 0.95) ),4) == -92.8624
    assert vector_angle( (0,0), (0,1), (0,1), (-1, 1) ) == -90
    assert round( vector_angle( (0,0), (0,1), (0,1), (-5,10) ), 4 ) == -29.0546

def compress(ary, ratio):
    yield ary[0]
    for i in range(1, len(ary)-1, ratio):
        yield ary[i]
    yield ary[-1]

class Profile(object):
    def __init__(self):
        self.segs = []
        
    def add(self, seg):
        self.segs.append( seg )
        
    def concat(self, npoints=None):
        ret = []
        s = 0
        for seg in self.segs:
            s0, e0 = seg[0]
            ret.append( (s, e0) )
            for (s0, e0), (s1, e1) in cons(seg):
                s += abs(s1-s0)
                ret.append( (s, e1) )
                
        if npoints is not None:
            compression = int(len(ret)/float(npoints))
            if compression <= 1:
                return ret
            
            return list(compress(ret,compression))
                
        return ret

class RouteServer(Servable):
    def __init__(self, ch_basename, osmdb_filename, profiledb_filename):
        graphdb = GraphDatabase( graphdb_filename )
        self.osmdb = OSMDB( osmdb_filename )
        self.profiledb = ProfileDB( profiledb_filename )
        self.ch = reincarnate_ch( ch_basename )
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    vertices.mime = "text/plain"

    def path(self, lat1, lng1, lat2, lng2, transfer_penalty=0, walking_speed=1.0, hill_reluctance=20,jsoncallback=None):
        
        t0 = time.time()
        origin = "osm-%s"%self.osmdb.nearest_node( lat1, lng1 )[0]
        dest = "osm-%s"%self.osmdb.nearest_node( lat2, lng2 )[0]
        endpoint_find_time = time.time()-t0
        
        print origin, dest
        
        t0  = time.time()
        wo = WalkOptions()
        #wo.transfer_penalty=transfer_penalty
        #wo.walking_speed=walking_speed
        wo.walking_speed=4
        wo.walking_overage = 0
        wo.hill_reluctance = 20
        wo.turn_penalty = 15 
        
        edgepayloads = self.ch.shortest_path( origin, dest, State(1,0), wo )
        
        wo.destroy()
        
        route_find_time = time.time()-t0
        
        t0 = time.time()
        names = []
        geoms = []
        profile = Profile()
        last_road_name = None
        last_road = None
        dist_since_last_turn = 0
        elev_since_last_turn = 0
        total_dist = 0
        total_elev = 0
        edge_lookup_time = 0
        profile_lookup_time = 0
        geoms_build_time = 0
        narrative_build_time = 0
        sum_desc_time = 0
        for edgepayload in edgepayloads:
            sdt0 = time.time()
            
            el0 = time.time()
            id, parent_id, node1, node2, distance, geom, tags = self.osmdb.edge( edgepayload.name )
            edge_lookup_time += (time.time()-el0)
            
            if edgepayload.reverse_of_source:
                geom.reverse()
            
            gg0 = time.time()
            geoms.extend( geom )
            turn_point = geom[0]
            geoms_build_time += (time.time()-gg0)
            
            pp0 = time.time()
            profile_seg = self.profiledb.get( edgepayload.name )
            if profile_seg:
              if edgepayload.reverse_of_source:
                  profile.add( list(reversed(profile_seg)) )
              else:
                  profile.add( profile_seg )
            profile_lookup_time += (time.time()-pp0)
                    
            nn0 = time.time()
            name = tags.get('name', 'nameless')
            if name != last_road_name:
                
                if last_road:
                    last_road_geom = last_road[5]
                    p1, p2 = last_road_geom[-2], last_road_geom[-1] 
                    p3, p4 = geom[0], geom[1]
                    
                    narrative = turn_narrative( p1, p2, p3, p4 )
                else:
                    narrative = "begin"
                names.append( ( narrative,                     # left, hard left, &c.
                                name,                          # street name
                                round(dist_since_last_turn,2), # distance since last turn (in meters)
                                round(total_dist,2),           # total distance so far (in meters)
                                round(elev_since_last_turn,2), # elevation gain since last turn (in meters)
                                turn_point) )                  # geographical point of turn
                dist_since_last_turn = edgepayload.length
                elev_since_last_turn = edgepayload.rise
            else:
                dist_since_last_turn += edgepayload.length
                elev_since_last_turn += edgepayload.rise
                
            total_dist += edgepayload.length
            total_elev += edgepayload.rise
            narrative_build_time = (time.time()-nn0)
            
            last_road_name = name
            last_road = (id, parent_id, node1, node2, distance, geom, tags)
            
            sum_desc_time += (time.time()-sdt0)
        route_desc_time = time.time()-t0

        ret = json.dumps( (names, 
                           encode_pairs( [(lat, lon) for lon, lat in geoms] ), 
                           profile.concat(300),
                           { 'route_find_time':route_find_time,
                             'route_desc_time':route_desc_time,
                             'endpoint_find_time':endpoint_find_time,
                             'edge_lookup_time':edge_lookup_time,
                             'profile_lookup_time':profile_lookup_time,
                             'geoms_build_time':geoms_build_time,
                             'narrative_build_time':narrative_build_time,
                             'sum_desc_time':sum_desc_time},
                           { 'total_dist':total_dist,
                             'total_elev':total_elev}) )
        if jsoncallback:
            return "%s(%s)"%(jsoncallback,ret)
        else:
            return ret

    """
    def path_raw(self, origin, dest, currtime):
        
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree( origin, dest, State(1,currtime), wo )
        wo.destroy()
        
        vertices, edges = spt.path( dest )
        
        ret = "\n".join([str(x) for x in vertices]) + "\n\n" + "\n".join([str(x) for x in edges])

        spt.destroy()
        
        return ret
    """
        
    def bounds(self, jsoncallback=None):
        ret = json.dumps( self.osmdb.bounds() )
        if jsoncallback:
            return "%s(%s)"%(jsoncallback,ret)
        else:
            return ret

def self_test():
    test_vector_angle()

import sys
if __name__ == '__main__':
    
    self_test()
    
    usage = "python routeserver.py ch_basename osmdb_filename profiledb_filename"
    
    if len(sys.argv) < 3:
        print usage
        exit()
        
    graphdb_filename = sys.argv[1]
    osmdb_filename = sys.argv[2]
    profiledb_filename = sys.argv[3]
    
    gc = RouteServer(graphdb_filename, osmdb_filename, profiledb_filename)
    gc.run_test_server(settings.PORT)
