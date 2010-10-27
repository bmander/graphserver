import os
import sqlite3
import cPickle
from graphserver.core import State, Graph, Combination
from graphserver import core
from sys import argv
import sys

class GraphDatabase:
    
    def __init__(self, sqlite_filename, overwrite=False):
        if overwrite:
            if os.path.exists(sqlite_filename):
                os.remove( sqlite_filename )
        elif not os.path.exists(sqlite_filename):
            overwrite = True # force an init of the tables
                
        self.conn = sqlite3.connect(sqlite_filename)
        
        if overwrite:
            self.setup()
            
        self.resources_cache = {}
        self.payloads_cache = {}
        
    def setup(self):
        c = self.conn.cursor()
        c.execute( "CREATE TABLE vertices (label)" )
        c.execute( "CREATE TABLE payloads (id TEXT UNIQUE ON CONFLICT IGNORE, type TEXT, state TEXT)" )
        c.execute( "CREATE TABLE edges (vertex1 TEXT, vertex2 TEXT, epid TEXT)" )
        c.execute( "CREATE TABLE resources (name TEXT UNIQUE ON CONFLICT IGNORE, image TEXT)" )
    
        self.conn.commit()
        c.close()
        
    def put_edge_payload(self, edgepayload, cc):
        
        if edgepayload.__class__ == Combination:
            for component in edgepayload.components:
                self.put_edge_payload( component, cc )
        
        cc.execute( "INSERT INTO payloads VALUES (?, ?, ?)", ( str(edgepayload.soul), cPickle.dumps( edgepayload.__class__ ), cPickle.dumps( edgepayload.__getstate__() ) ) )
        
        return str(edgepayload.soul)
        
    def get_edge_payload(self, id):
        queryresult = list(self.execute( "SELECT id, type, state FROM payloads WHERE id=?", (id,) ))
        if len(queryresult)==0:
            return None
        
        id, type, state = queryresult[0]
        
        if id in self.payloads_cache:
            return self.payloads_cache[id]
        
        typeclass = cPickle.loads( str(type) )
        ret = typeclass.reconstitute( cPickle.loads( str(state) ), self )
        ret.external_id = int(id)
        self.payloads_cache[id] = ret
        return ret
        
    def populate(self, graph, reporter=None):
        c = self.conn.cursor()
        
        n = len(graph.vertices)
	nseg = max(n,100)
        for i, vv in enumerate( graph.vertices ):
            if reporter and i%(nseg//100)==0: reporter.write( "%d/%d vertices dumped\n"%(i,n) )
            
            c.execute( "INSERT INTO vertices VALUES (?)", (vv.label,) )
            for ee in vv.outgoing:
                epid = self.put_edge_payload( ee.payload, c )
                c.execute( "INSERT INTO edges VALUES (?, ?, ?)", (ee.from_v.label, ee.to_v.label, epid) )
                
                if hasattr(ee.payload, "__resources__"):
                    for name, resource in ee.payload.__resources__():
                        self.store( name, resource, c )
        
        self.conn.commit()
        c.close()
        
        self.index()
        
    def get_cursor(self):
        return self.conn.cursor()
    def commit(self):
        self.conn.commit()
        
    def add_vertex(self, vertex_label, outside_c=None):
        c = outside_c or self.conn.cursor()
        
        c.execute( "INSERT INTO vertices VALUES (?)", (vertex_label,) )
        
        if outside_c is None:
            self.conn.commit()
            c.close()
            
    def remove_edge( self, oid, outside_c=None ):
        c = outside_c or self.conn.cursor()
        
        c.execute( "DELETE FROM edges WHERE oid=?", (oid,) )
        
        if outside_c is None:
            self.conn.commit()
            c.close()
        
    def add_edge(self, from_v_label, to_v_label, payload, outside_c=None):
        c = outside_c or self.conn.cursor()
    
        epid = self.put_edge_payload( payload, c )
        c.execute( "INSERT INTO edges VALUES (?, ?, ?)", (from_v_label, to_v_label, epid) )
    
        if hasattr(payload, "__resources__"):
            for name, resource in payload.__resources__():
                self.store( name, resource )
    
        if outside_c is None:
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
        
    def all_vertex_labels(self):
        for vertex_label, in self.execute( "SELECT DISTINCT label FROM (SELECT vertex1 AS label FROM edges UNION SELECT vertex2 AS label FROM edges)" ):
            yield vertex_label
    
    def all_edges(self):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges" ):
            ep = self.get_edge_payload( epid )
            
            yield vertex1, vertex2, ep
    
    def all_outgoing(self, vertex1_label):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges WHERE vertex1=?", (vertex1_label,) ):
            yield vertex1, vertex2, self.get_edge_payload( epid )
    
    def all_incoming(self, vertex2_label):
        for vertex1, vertex2, epid in self.execute( "SELECT vertex1, vertex2, epid FROM edges WHERE vertex2=?", (vertex2_label,) ):
            yield vertex1, vertex2, self.get_edge_payload( epid )
    
            
    def store(self, name, obj, c=None):
        cc = self.conn.cursor() if c is None else c
        resource_count = list(c.execute( "SELECT count(*) FROM resources WHERE name = ?", (name,) ))[0][0]
        if resource_count == 0:
            cc.execute( "INSERT INTO resources VALUES (?, ?)", (name, cPickle.dumps( obj )) )
            if not c: self.conn.commit()
        if not c: cc.close()
        
    def resolve(self, name):
        if name in self.resources_cache:
            return self.resources_cache[name]
        else:
            image = list(self.execute( "SELECT image FROM resources WHERE name = ?", (str(name),) ))[0][0]
            resource = cPickle.loads( str(image) )
            self.resources_cache[name] = resource
            return resource
        
    def resources(self):
        for name, image in self.execute( "SELECT name, image from resources" ):
            yield name, cPickle.loads( str(image) )
            
    def index(self):
        c = self.conn.cursor()
        c.execute( "CREATE INDEX vertices_label ON vertices (label)" )
        c.execute( "CREATE INDEX ep_ids ON payloads (id)" )
        self.conn.commit()
        c.close()
        
    def num_vertices(self):
        return list(self.execute( "SELECT count(*) from vertices" ))[0][0]
        
    def num_edges(self):
        return list(self.execute( "SELECT count(*) from edges" ))[0][0]
        
    def incarnate(self, reporter=sys.stdout):
        g = Graph()
        num_vertices = self.num_vertices()
        
        for i, vertex_label in enumerate( self.all_vertex_labels() ):
            if reporter and i%5000==0: 
                reporter.write("\r%d/%d vertices"%(i,num_vertices) ) 
                reporter.flush()
            g.add_vertex( vertex_label )
        
        if reporter: reporter.write("\rLoaded %d vertices %s\n" % (num_vertices, " "*10))
        
        num_edges = self.num_edges()
        for i, (vertex1, vertex2, edgetype) in enumerate( self.all_edges() ):
            if i%5000==0: 
                reporter.write("\r%d/%d edges"%(i,num_edges) ) 
                reporter.flush()
            g.add_edge( vertex1, vertex2, edgetype )
        if reporter: reporter.write("\rLoaded %d edges %s\n" % (num_edges, " "*10))
        
        return g
        

def main():
    if len(argv) < 2:
        print "usage: python graphdb.py [vertex1, [vertex2]]"
        return
    
    graphdb_filename = argv[1]
    graphdb = GraphDatabase( graphdb_filename )
    
    if len(argv) == 2:
        print "vertices:"
        for vertex_label in sorted( graphdb.all_vertex_labels() ):
            print vertex_label
        print "resources:"
        for name, resource in graphdb.resources():
            print name, resource
        return
    
    vertex1 = argv[2]
    for vertex1, vertex2, edgetype in graphdb.all_outgoing( vertex1 ):
        print "%s -> %s\n\t%s"%(vertex1, vertex2, repr(edgetype))
        
        if len(argv) == 4:
            s0 = State(1,int(argv[3]))
            print "\t"+str(edgetype.walk( s0 ))

if __name__=='__main__':
    main()
