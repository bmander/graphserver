import sqlite3
try:
    from osm.osm import OSM
except ImportError:
    from osm import OSM
import os
import json
import sys

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

class WayRecord:
    def __init__(self, id, tags, nds, geom):
        self.id = id
        
        if type(tags)==unicode:
            self.tags_str = tags
            self.tags_cache = None
        else:
            self.tags_cache = tags
            self.tags_str = None
            
        if type(nds)==unicode:
            self.nds_str = nds
            self.nds_cache = None
        else:
            self.nds_cache = nds
            self.nds_str = None
            
        if type(geom)==unicode:
            self.geom_str = geom
            self.geom_cache = None
        else:
            self.geom_cache = geom
            self.geom_str = None
        
    @property
    def tags(self):
        self.tags_cache = self.tags_cache or json.loads(self.tags_str)
        return self.tags_cache
        
    @property
    def nds(self):
        self.nds_cache = self.nds_cache or json.loads(self.nds_str)
        return self.nds_cache
        
    @property
    def geom(self):
        self.geom_cache = self.geom_cache or json.loads(self.geom_str)
        return self.geom_cache
        
    def split(self, subseg_num, split_node_point, split_node_id):
        geom = self.geom
        nds = self.nds
        
        geom1 = geom[:subseg_num+1]
        nds1 = nds[:subseg_num+1]
        
        geom2 = geom[subseg_num+1:]
        nds2 = nds[subseg_num+1:]
                
        if list(split_node_point) == list(geom[subseg_num]):
            if len(nds)==2:
                return (None,None)
            
            geom2 = [geom[subseg_num]]+geom2
            nds2 = [nds[subseg_num]]+nds2
        elif list(split_node_point) == list(geom[subseg_num+1]):
            if len(nds)==2:
                return (None,None)
            
            geom1.append( geom[subseg_num+1] )
            nds1.append( nds[subseg_num+1] )
        else:
            geom1 = geom1 + [split_node_point]
            nds1 = nds1 + [split_node_id]
            geom2 = [split_node_point] + geom2
            nds2 = [split_node_id] + nds2
        
        if len(nds1)<2 or len(nds2)<2:
            return (None, None)
        
        wr1 = WayRecord(self.id+"0", self.tags or self.tags_str, nds1, geom1)
        wr2 = WayRecord(self.id+"1", self.tags or self.tags_str, nds2, geom2)
        
        return (wr1,wr2)
        
    @property
    def bbox(self):
        l = float('inf')
        b = float('inf')
        r = -float('inf')
        t = -float('inf')
        
        for x,y in self.geom:
            l = min(l,x)
            b = min(b,y)
            r = max(r,x)
            t = max(t,y)
            
        return (l,b,r,t)
        
    def __repr__(self):
        return "<WayRecord id='%s'>"%self.id

class OSMDB:
    def __init__(self, dbname,overwrite=False):
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if overwrite:
            self.setup()
        
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE nodes (id TEXT, tags TEXT, lat FLOAT, lon FLOAT)" )
        c.execute( "CREATE TABLE ways (id TEXT, tags TEXT, nds TEXT, geom TEST, left FLOAT, bottom FLOAT, right FLOAT, top FLOAT)" )
        c.execute( "CREATE INDEX nodes_id ON nodes (id)" )
        c.execute( "CREATE INDEX nodes_lon ON nodes (lon)" )
        c.execute( "CREATE INDEX nodes_lat ON nodes (lat)" )
        c.execute( "CREATE INDEX ways_id ON ways (id)" )
        c.execute( "CREATE INDEX ways_bbox ON ways(left, bottom, right, top)" )
        self.conn.commit()
        c.close()
        
    def populate(self, osm_obj, accept=lambda tags: True, reporter=None):
        c = self.conn.cursor()
        
        touched_nodes = set()
        
        n_ways = len(osm_obj.ways)
        if reporter: reporter.write( "Populating %d ways...\n"%n_ways)
        for i, way in enumerate( osm_obj.ways.values() ):
            if reporter and i%(n_ways//100+1)==0: reporter.write( "%s/%s ways\n"%(i,n_ways))
            
            if accept(way.tags):
                touched_nodes.add( way.nd_ids[0] )
                touched_nodes.add( way.nd_ids[-1] )
            
                l,b,r,t = way.bbox
                c.execute("INSERT INTO ways VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (way.id, json.dumps(way.tags), json.dumps(way.nd_ids), json.dumps( way.geom ), l, b, r, t))
        
        n_nodes = len(osm_obj.nodes)
        if reporter: reporter.write( "Populating %d nodes..."%n_nodes)
        for i, node in enumerate( osm_obj.nodes.values() ):
            if reporter and i%(n_nodes//100+1)==0: reporter.write( "%s/%s nodes\n"%(i,n_nodes))
            
            if node.id in touched_nodes:
                c.execute("INSERT INTO nodes VALUES (?, ?, ?, ?)", ( node.id, json.dumps(node.tags), node.lat, node.lon ) )
        
        self.conn.commit()
        c.close()
        
    def nodes(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT * FROM nodes" )
        
        for node_row in c:
            yield node_row
            
        c.close()
        
    def node(self, id):
        c = self.conn.cursor()
        
        c.execute( "SELECT * FROM nodes WHERE id = ?", (id,) )
        
        try:
            ret = next(c)
        except StopIteration as e:
            c.close()
            raise Exception( "Database does not have node with id '%s'"%id )
            
        c.close()
        return ret
    
    def nearest_node(self, lat, lon, range=0.005):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, lat, lon FROM nodes WHERE lat > ? AND lat < ? AND lon > ? AND lon < ?", (lat-range, lat+range, lon-range, lon+range) )
        
        dists = [(nid, nlat, nlon, ((nlat-lat)**2+(nlon-lon)**2)**0.5) for nid, nlat, nlon in c]
            
        if len(dists)==0:
            return (None, None, None, None)
            
        return min( dists, key = lambda x:x[3] )

    def nearest_of( self, lat, lon, nodes ):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, lat, lon FROM nodes WHERE id IN (%s)"%",".join([str(x) for x in nodes]) )
        
        dists = [(nid, nlat, nlon, ((nlat-lat)**2+(nlon-lon)**2)**0.5) for nid, nlat, nlon in c]
            
        if len(dists)==0:
            return (None, None, None, None)
            
        return min( dists, key = lambda x:x[3] )

    def nearby_ways(self, lat, lon, range=0.005):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, tags, nds, geom FROM ways WHERE left <= ? AND right >= ? and bottom <= ? and top >= ?", (lon+range, lon-range, lat+range, lat-range) )
        
        for id, tags, nds, geom in c:
            yield WayRecord(id, tags, nds, geom)
        
        c.close()
        
    def way(self, id):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, tags, nds, geom FROM ways WHERE id = ?", (id,) )
        
        id, tags_str, nds_str, geom_str = next(c)
        ret = WayRecord(id, tags_str, nds_str, geom_str)
        c.close()
        
        return ret
        
    def way_nds(self, id):
        c = self.conn.cursor()
        c.execute( "SELECT nds FROM ways WHERE id = ?", (id,) )
        
        (nds_str,) = next(c)
        c.close()
        
        return json.loads( nds_str )
        
    def ways(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, tags, nds, geom FROM ways" )
        
        for id, tags_str, nds_str, geom_str in c:
            yield WayRecord( id, tags_str, nds_str, geom_str )
            
        c.close()
        
    def count_ways(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT count(*) FROM ways" )
        ret = next(c)[0]
        
        c.close()
        
        return ret
        
    def nearest_way( self, x,y, range=0.001, accept_tags=lambda tags:True ):
        """returns (way_id, subsegment_num, subsegment_splitpoint, point, distance_from_point)"""
        
        lineup = []
        
        for way in self.nearby_ways( y, x, range=0.001 ):
            if accept_tags(way.tags):
                subsegment_num, subsegment_splitpoint, point, distance_from_point = closest_point_on_linestring( way.geom, (x, y) )
                lineup.append( (way, subsegment_num, subsegment_splitpoint, point, distance_from_point) )
        
        if len(lineup)==0:
            return (None, None, None, None, None)
        return min( lineup, key=lambda x:x[4] )
        
    def delete_way(self, id):
        c = self.conn.cursor()
        
        c.execute("DELETE FROM ways WHERE id = ?", (id,))
        
        c.close()
        
    def insert_way_record(self, way_rec):
        c = self.conn.cursor()
        
        l,b,r,t = way_rec.bbox
        c.execute("INSERT INTO ways VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (way_rec.id, way_rec.tags_str or json.dumps(way_rec.tags), way_rec.nds_str or json.dumps(way_rec.nds), way_rec.geom_str or json.dumps( way_rec.geom ), l, b, r, t))
        
        c.close()
        
    def insert_node(self, id, tags, lat, lon):
        c = self.conn.cursor()
        
        c.execute( "INSERT INTO nodes VALUES (?, ?, ?, ?)", (id, json.dumps(tags), lat, lon) )
        
        c.close()
        
    def bounds(self):
        c = self.conn.cursor()
        c.execute( "SELECT min(left), min(bottom), max(right), max(top) FROM ways" )
        
        ret = next(c)
        c.close()
        return ret

def mag(vec):
    return sum([x**2 for x in vec])**0.5
    
def vector_div( vec, scal ):
    return tuple([x/scal for x in vec])
        
def vector_mult( vec, scal ):
    return tuple([x*scal for x in vec])
        
def vector_diff( vec1, vec2 ):
    return [a-b for a,b in zip(vec1, vec2)]
        
def vector_sum( vec1, vec2 ):
    return [a+b for a,b in zip(vec1, vec2)]
        
def dot_product( vec1, vec2 ):
    return sum( [a*b for a, b in zip(vec1, vec2)] )
    
def closest_point(p1, p2, s):
    """closest point on line segment (p1,p2) to s; could be an endpoint or midspan"""
    
    #if the line is a single point, the closest point is the only point
    if p1==p2:
        return (0,p1)
    
    seg_vector = vector_diff(p2,p1)
    seg_mag = mag(seg_vector)
    #print( "seg_vector, length", seg_vector, seg_mag )
    seg_unit = vector_div( seg_vector, seg_mag )
    stop_vector = vector_diff(s,p1)
    #print( "stop_vector", stop_vector )
    
    #scalar projection of A onto B = (A dot B)/|B| = A dot unit(B)
    sp = dot_product( stop_vector, seg_unit )
    
    #print( "scalar projection", sp )
    
    if sp < 0:
        #closest point is startpoint
        #print( "startpoint" )
        return (0, p1)
    elif sp > seg_mag:
        #closest point is endpoint
        #print( "endpoint" )
        return (1, p2)
    else:
        #closest point is midspan
        #print( "midpoint" )
        return (sp/seg_mag, vector_sum(p1,vector_mult( seg_unit, sp )))
        
def closest_point_on_linestring(linestring, s):
    """returns (subsegment_num, subsegment_splitpoint, point, distance_from_point)"""
    
    def closest_iter():
        for i, (p1,p2) in enumerate( cons(linestring) ):
            div, closest = closest_point( p1,p2,s )
            dist_to_closest = mag(vector_diff(s,closest))
            
            yield (i, div, closest, dist_to_closest)
            
    return min(closest_iter(), key=lambda x:x[3])

def test_wayrecord():
    wr = WayRecord( "1", {'highway':'bumpkis'}, ['1','2','3'], [(0,0),(5,5),(8,8)] )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']
    assert wr.geom == [(0,0),(5,5),(8,8)]
    
    wr = WayRecord( "1", "{\"highway\":\"bumpkis\"}", "[\"1\",\"2\",\"3\"]", "[[0,0],[5,5],[8,8]]" )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']
    assert wr.geom == [[0,0],[5,5],[8,8]]
    
    wr1, wr2 = wr.split( 0, (15,15), "extra" )
    assert wr1.tags == {'highway': 'bumpkis'}
    assert wr1.nds == ['1', 'extra'] 
    assert wr1.geom == [[0, 0], (15, 15)] 
    assert wr2.tags == {'highway': 'bumpkis'} 
    assert wr2.nds == ['extra', '2', '3']
    assert wr2.geom == [(15, 15), [5, 5], [8, 8]]
    
    wr1, wr2 = wr.split( 0, [5,5], "extra" )
    assert( wr1.nds == ['1', '2'] )
    assert( wr1.geom == [[0, 0], [5, 5]] )
    assert( wr2.nds == ['2', '3'] )
    assert( wr2.geom == [[5, 5], [8, 8]] )
    
    wr1, wr2 = wr.split( 1, [5,5], "extra" )
    assert( wr1.nds == ['1', '2'])
    assert( wr1.geom == [[0, 0], [5, 5]] )
    assert( wr2.nds == ['2', '3'])
    assert( wr2.geom == [[5, 5], [8, 8]])
    
    wr1, wr2 = wr.split( 0, [0,0], "extra" )
    assert( (wr1, wr2) == (None, None) )
    
    wr = WayRecord( "1", {'highway':'bumpkis'}, ['1','2'], [(0,0),(5,5)] )
    wr1, wr2 = wr.split(0, (5,5), "extra")
    assert( (wr1, wr2) == (None,None) )

def osm_to_osmdb(osm_filename, osmdb_filename):
    osmdb = OSMDB( osmdb_filename, overwrite=True )
    fp = open( osm_filename )
    lp = OSM( fp )
    osmdb.populate( lp, accept=lambda tags: 'highway' in tags, reporter=sys.stdout )
    fp.close()

if __name__=='__main__':

    #osmdb = OSMDB( "portland.sqlite" )
    #osmdb.node( "osmsplit10739" )

    #test_wayrecord()
    osm_to_osmdb("bartarea.osm", "bartarea.sqlite")
    
    #print( osmdb.nearest_node( 45.517471999999998, -122.667694 ) )

    #y = 45.5235
    #x = -122.658673
    #closest_way = nearest_way( osmdb, x, y )
    #print( closest_way[0] )
    #print( osmdb.way( closest_way[0] ) )
    
    #c = osmdb.conn.cursor()
    #c.execute("SELECT * FROM nodes")
    #for row in c:
    #    print( row )
        

    #for way in lp.ways.values():
    #    print( way )
    #    print( way.geom )
    #    print( way.bbox )
    #    for nd in way.nds:
    #        print( nd )

