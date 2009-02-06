from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State
import time

class GraphCrawler(Servable):
    def __init__(self, graphdb_filename):
        self.graphdb = GraphDatabase( graphdb_filename )
    
    def vertices(self):
        return "\n".join( ["<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><br>"%(vertex_label, vertex_label) for vertex_label in sorted( self.graphdb.all_vertex_labels() ) ])
    vertices.mime = "text/html"
    
    def vertex(self, label, currtime=None):
        currtime = currtime or int(time.time())
        
        ret = []
        ret.append( "<h1>%s</h1>"%label )
        
        ret.append( "<h3>incoming from:</h3>" )
        for vertex1, vertex2, edgetype in self.graphdb.all_incoming( label ):
            ret.append( "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><pre>&nbsp;&nbsp;&nbsp;%s</pre>"%(vertex1, vertex1, cgi.escape(repr(edgetype))) )
        ret.append( "<h3>outgoing to:</h3>" )
        for i, (vertex1, vertex2, edgetype) in enumerate( self.graphdb.all_outgoing( label ) ):
            s0 = State(1,int(currtime))
            s1 = edgetype.walk( s0 )
            
            if s1:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;&currtime=%d\">%s@%d</a>"%(vertex2, s1.time, vertex2, s1.time)
            else:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a>"%(vertex2, vertex2)
            
            ret.append( "%s<br><pre>&nbsp;&nbsp;&nbsp;via %s (<a href=\"/outgoing?label=&quot;%s&quot;&edgenum=%d\">details</a>)</pre>"%(toterm, cgi.escape(repr(edgetype)), vertex1, i) )
            
            if s1:
                ret.append( "<pre>&nbsp;&nbsp;&nbsp;%s</pre>"%cgi.escape(str(s1)) )
                
        return "".join(ret)
    vertex.mime = "text/html"
    
    def outgoing(self, label, edgenum):
        all_outgoing = list( self.graphdb.all_outgoing( label ) )
        
        fromv, tov, edge = all_outgoing[edgenum]
        
        return edge.expound()
    
    def str(self):
        return str(self.graphdb)
        
if __name__ == '__main__':
    # a fine example node for bart: "ASBY" @ 1233172800
    # for trimet: "10071" @ 1233172800
    
    GDB_FILENAME = "../package_graph/bartheadway.db"
    GDB_FILENAME = "/home/brandon/urbanmapping/transit_routing/router/data/bart.gdb"
    
    gc = GraphCrawler(GDB_FILENAME)
    gc.run_test_server()