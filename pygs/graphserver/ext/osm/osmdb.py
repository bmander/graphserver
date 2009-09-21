import sqlite3
import os
try:
    import json
except ImportError:
    import simplejson as json
import sys
import xml.sax
import binascii
from vincenty import vincenty
from struct import pack, unpack
from rtree import Rtree

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def pack_coords(coords):
    return binascii.b2a_base64( "".join([pack( "ff", *coord ) for coord in coords]) )
        
def unpack_coords(str):
    bin = binascii.a2b_base64( str )
    return [unpack( "ff", bin[i:i+8] ) for i in range(0, len(bin), 8)]

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}

    def __repr__(self):
        return "<Node id='%s' (%s, %s) n_tags=%d>"%(self.id, self.lon, self.lat, len(self.tags))
        
class Way:
    def __init__(self, id):
        self.id = id
        self.nd_ids = []
        self.tags = {}
        
    def __repr__(self):
        return "<Way id='%s' n_nds=%d n_tags=%d>"%(self.id, len(self.nd_ids), len(self.tags))

class WayRecord:
    def __init__(self, id, tags, nds):
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
        
    @property
    def tags(self):
        self.tags_cache = self.tags_cache or json.loads(self.tags_str)
        return self.tags_cache
        
    @property
    def nds(self):
        self.nds_cache = self.nds_cache or json.loads(self.nds_str)
        return self.nds_cache
        
    def __repr__(self):
        return "<WayRecord id='%s'>"%self.id

class OSMDB:
    def __init__(self, dbname,overwrite=False,rtree_index=True):
        if overwrite:
            try:
                os.remove( dbname )
            except OSError:
                pass
            
        self.conn = sqlite3.connect(dbname)
        
        if rtree_index:
            self.index = Rtree( dbname )
        else:
            self.index = None
        
        if overwrite:
            self.setup()
        
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE nodes (id TEXT, tags TEXT, lat FLOAT, lon FLOAT, endnode_refs INTEGER DEFAULT 1)" )
        c.execute( "CREATE TABLE ways (id TEXT, tags TEXT, nds TEXT)" )
        self.conn.commit()
        c.close()
        
    def create_indexes(self):
        c = self.conn.cursor()
        c.execute( "CREATE INDEX nodes_id ON nodes (id)" )
        c.execute( "CREATE INDEX nodes_lon ON nodes (lon)" )
        c.execute( "CREATE INDEX nodes_lat ON nodes (lat)" )
        c.execute( "CREATE INDEX ways_id ON ways (id)" )
        self.conn.commit()
        c.close()
        
    def populate(self, osm_filename, accept=lambda tags: True, reporter=None):
        print "importing osm from XML to sqlite database"
        
        c = self.conn.cursor()
        
        self.n_nodes = 0
        self.n_ways = 0
        
        superself = self

        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass

            @classmethod
            def startDocument(self):
                pass

            @classmethod
            def endDocument(self):
                pass

            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'])
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nd_ids.append( attrs['ref'] )

            @classmethod
            def endElement(self,name):
                if name=='node':
                    if superself.n_nodes%5000==0:
                        print "node %d"%superself.n_nodes
                    superself.n_nodes += 1
                    superself.add_node( self.currElem, c )
                elif name=='way':
                    if superself.n_ways%5000==0:
                        print "way %d"%superself.n_ways
                    superself.n_ways += 1
                    superself.add_way( self.currElem, c )

            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(osm_filename, OSMHandler)
        
        self.conn.commit()
        c.close()
        
        print "indexing primary tables...",
        self.create_indexes()
        print "done"
        
    def set_endnode_ref_counts( self ):
        """Populate ways.endnode_refs. Necessary for splitting ways into single-edge sub-ways"""
        
        print "counting end-node references to find way split-points"
        
        c = self.conn.cursor()
        
        endnode_ref_counts = {}
        
        c.execute( "SELECT nds from ways" )
        
        print "...counting"
        for i, (nds_str,) in enumerate(c):
            if i%5000==0:
                print i
                
            nds = json.loads( nds_str )
            for nd in nds:
                endnode_ref_counts[ nd ] = endnode_ref_counts.get( nd, 0 )+1
        
        print "...updating nodes table"
        for i, (node_id, ref_count) in enumerate(endnode_ref_counts.items()):
            if i%5000==0:
                print i
            
            if ref_count > 1:
                c.execute( "UPDATE nodes SET endnode_refs = ? WHERE id=?", (ref_count, node_id) )
            
        self.conn.commit()
        c.close()
    
    def index_endnodes( self ):
        print "indexing endpoint nodes into rtree"
        
        c = self.conn.cursor()
        
        #TODO index endnodes if they're at the end of oneways - which only have one way ref, but are still endnodes
        c.execute( "SELECT id, lat, lon FROM nodes WHERE endnode_refs > 1" )
        
        for id, lat, lon in c:
            self.index.add( int(id), (lon, lat, lon, lat) )
            
        c.close()
    
    def create_and_populate_edges_table( self, tolerant=False ):
        self.set_endnode_ref_counts()
        self.index_endnodes()
        
        print "splitting ways and inserting into edge table"
        
        c = self.conn.cursor()
        
        c.execute( "CREATE TABLE edges (id TEXT, parent_id TEXT, start_nd TEXT, end_nd TEXT, dist FLOAT, geom TEXT)" )
        
        for i, way in enumerate(self.ways()):
            try:
                if i%5000==0:
                    print i
                
                subways = []
                curr_subway = [ way.nds[0] ] # add first node to the current subway
                for nd in way.nds[1:-1]:     # for every internal node of the way
                    curr_subway.append( nd )
                    if self.node(nd)[4] > 1: # node reference count is greater than one, node is shared by two ways
                        subways.append( curr_subway )
                        curr_subway = [ nd ]
                curr_subway.append( way.nds[-1] ) # add the last node to the current subway, and store the subway
                subways.append( curr_subway );
                
                #insert into edge table
                for i, subway in enumerate(subways):
                    coords = [(lambda x:(x[3],x[2]))(self.node(nd)) for nd in subway]
                    packt = pack_coords( coords )
                    dist = sum([vincenty(lat1, lng1, lat2, lng2) for (lng1, lat1), (lng2, lat2) in cons(coords)])
                    c.execute( "INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)", ("%s-%s"%(way.id, i),
                                                                               way.id,
                                                                               subway[0],
                                                                               subway[-1],
                                                                               dist,
                                                                               packt) )
            except IndexError:
                if tolerant:
                    continue
                else:
                    raise
        
        print "indexing edges...",
        c.execute( "CREATE INDEX edges_id ON edges (id)" )
        c.execute( "CREATE INDEX edges_parent_id ON edges (parent_id)" )
        print "done"
        
        self.conn.commit()
        c.close()
        
    def edge(self, id):
        c = self.conn.cursor()
        
        c.execute( "SELECT edges.*, ways.tags FROM edges, ways WHERE ways.id = edges.parent_id AND edges.id = ?", (id,) )
        
        try:
            ret = c.next()
            way_id, parent_id, from_nd, to_nd, dist, geom, tags = ret
            return (way_id, parent_id, from_nd, to_nd, dist, unpack_coords( geom ), json.loads(tags))
        except StopIteration:
            c.close()
            raise IndexError( "Database does not have an edge with id '%s'"%id )
            
        c.close()
        return ret
        
    def edges(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT edges.*, ways.tags FROM edges, ways WHERE ways.id = edges.parent_id" )
        
        for way_id, parent_id, from_nd, to_nd, dist, geom, tags in c:
            yield (way_id, parent_id, from_nd, to_nd, dist, unpack_coords(geom), json.loads(tags))
            
        c.close()
        
        
    def add_way( self, way, curs=None ):
        if curs is None:
            curs = self.conn.cursor()
            close_cursor = True
        else:
            close_cursor = False
            
        curs.execute("INSERT INTO ways (id, tags, nds) VALUES (?, ?, ?)", (way.id, json.dumps(way.tags), json.dumps(way.nd_ids) ))
        
        if close_cursor:
            self.conn.commit()
            curs.close()
            
    def add_node( self, node, curs=None ):
        if curs is None:
            curs = self.conn.cursor()
            close_cursor = True
        else:
            close_cursor = False
            
        curs.execute("INSERT INTO nodes (id, tags, lat, lon) VALUES (?, ?, ?, ?)", ( node.id, json.dumps(node.tags), node.lat, node.lon ) )
        
        if close_cursor:
            self.conn.commit()
            curs.close()
        
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
            ret = c.next()
        except StopIteration:
            c.close()
            raise IndexError( "Database does not have node with id '%s'"%id )
            
        c.close()
        return ret
    
    def nearest_node(self, lat, lon, range=0.005):
        c = self.conn.cursor()
        
        if self.index:
            print "YOUR'RE USING THE INDEX"
            id = self.index.nearest( (lon, lat), 1 )[0]
            print "THE ID IS %d"%id
            c.execute( "SELECT id, lat, lon FROM nodes WHERE id = ?", (id,) )
        else:
            c.execute( "SELECT id, lat, lon FROM nodes WHERE endnode_refs > 1 AND lat > ? AND lat < ? AND lon > ? AND lon < ?", (lat-range, lat+range, lon-range, lon+range) )
        
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
        
    def way(self, id):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, tags, nds FROM ways WHERE id = ?", (id,) )
       
        try: 
          id, tags_str, nds_str = c.next()
          ret = WayRecord(id, tags_str, nds_str)
        except StopIteration:
          raise Exception( "OSMDB has no way with id '%s'"%id )
        finally:
          c.close()
        
        return ret
        
    def way_nds(self, id):
        c = self.conn.cursor()
        c.execute( "SELECT nds FROM ways WHERE id = ?", (id,) )
        
        (nds_str,) = c.next()
        c.close()
        
        return json.loads( nds_str )
        
    def ways(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT id, tags, nds FROM ways" )
        
        for id, tags_str, nds_str in c:
            yield WayRecord( id, tags_str, nds_str )
            
        c.close()
        
    def count_ways(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT count(*) FROM ways" )
        ret = c.next()[0]
        
        c.close()
        
        return ret
        
    def count_edges(self):
        c = self.conn.cursor()
        
        c.execute( "SELECT count(*) FROM edges" )
        ret = c.next()[0]
        
        c.close()
        
        return ret
        
    def delete_way(self, id):
        c = self.conn.cursor()
        
        c.execute("DELETE FROM ways WHERE id = ?", (id,))
        
        c.close()
        
    def bounds(self):
        c = self.conn.cursor()
        c.execute( "SELECT min(lon), min(lat), max(lon), max(lat) FROM nodes" )
        
        ret = c.next()
        c.close()
        return ret
    
    def execute(self,sql,args=None):
        c = self.conn.cursor()
        if args:
            for row in c.execute(sql,args):
                yield row
        else:
            for row in c.execute(sql):
                yield row
        c.close()
    
    def cursor(self):
        return self.conn.cursor()    

def test_wayrecord():
    wr = WayRecord( "1", {'highway':'bumpkis'}, ['1','2','3'] )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']
    
    wr = WayRecord( "1", "{\"highway\":\"bumpkis\"}", "[\"1\",\"2\",\"3\"]" )
    assert wr.id == "1"
    assert wr.tags == {'highway':'bumpkis'}
    assert wr.nds == ['1','2','3']

def osm_to_osmdb(osm_filename, osmdb_filename, tolerant=False):
    osmdb = OSMDB( osmdb_filename, overwrite=True )
    osmdb.populate( osm_filename, accept=lambda tags: 'highway' in tags, reporter=sys.stdout )
    osmdb.create_and_populate_edges_table(tolerant)

def main():
    from sys import argv
    
    usage = "python osmdb.py osm_filename osmdb_filename"
    if len(argv) < 3:
        print usage
        exit()

    osm_filename = argv[1]
    osmdb_filename = argv[2]
    
    tolerant = 'tolerant' in argv
    
    osm_to_osmdb(osm_filename, osmdb_filename, tolerant)

if __name__=='__main__':
    main()
