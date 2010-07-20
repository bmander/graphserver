from servable import Servable
from graphserver.graphdb import GraphDatabase
import cgi
from graphserver.core import State, WalkOptions
import time
import sys

def string_spt_vertex(vertex, level=0):
    ret = ["  "*level+str(vertex)]
    
    for edge in vertex.outgoing:
        ret.append( "  "*(level+1)+"%s"%(edge) )
        ret.append( string_spt_vertex( edge.to_v, level+1 ) )
    
    return "\n".join(ret)

class GraphCrawler(Servable):
    def __init__(self, graphdb_filename):
        self.graphdb = GraphDatabase( graphdb_filename )
    
    def vertices(self, like=None):
        if like:
            return "\n".join( ["<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><br>"%(vl[0], vl[0]) 
                               for vl in self.graphdb.execute("SELECT label from vertices where label like ? order by label", (like,)) ])
        else:
            return "\n".join( ["<a href=\"/vertex?label=&quot;%s&quot;\">%s</a><br>"%(vl[0], vl[0]) 
                               for vl in self.graphdb.execute("SELECT label from vertices order by label") ])
    vertices.mime = "text/html"
    
    def vertex(self, label, currtime=None, hill_reluctance=1.5, walking_speed=0.85):
        currtime = currtime or int(time.time())
        
        ret = []
        ret.append( "<h1>%s</h1>"%label )
        
        wo = WalkOptions()
        ret.append( "<h3>walk options</h3>" )
        ret.append( "<li>transfer_penalty: %s</li>"%wo.transfer_penalty )
        ret.append( "<li>turn_penalty: %s</li>"%wo.turn_penalty )
        ret.append( "<li>walking_speed: %s</li>"%wo.walking_speed )
        ret.append( "<li>walking_reluctance: %s</li>"%wo.walking_reluctance )
        ret.append( "<li>uphill_slowness: %s</li>"%wo.uphill_slowness )
        ret.append( "<li>downhill_fastness: %s</li>"%wo.downhill_fastness )
        ret.append( "<li>hill_reluctance: %s</li>"%wo.hill_reluctance )
        ret.append( "<li>max_walk: %s</li>"%wo.max_walk )
        ret.append( "<li>walking_overage: %s</li>"%wo.walking_overage )
        
        
        ret.append( "<h3>incoming from:</h3>" )
        for i, (vertex1, vertex2, edgetype) in enumerate( self.graphdb.all_incoming( label ) ):
            s1 = State(1,int(currtime))
            wo = WalkOptions()
            wo.hill_reluctance=hill_reluctance
            wo.walking_speed=walking_speed
            s0 = edgetype.walk_back( s1, wo )
            
            if s0:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;&currtime=%d\">%s@%d</a>"%(vertex1, s0.time, vertex1, s1.time)
            else:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a>"%(vertex1, vertex1)
            
            ret.append( "%s<br><pre>&nbsp;&nbsp;&nbsp;via %s (<a href=\"/incoming?label=&quot;%s&quot;&edgenum=%d\">details</a>)</pre>"%(toterm, cgi.escape(repr(edgetype)), vertex2, i) )
            
            if s0:
                ret.append( "<pre>&nbsp;&nbsp;&nbsp;%s</pre>"%cgi.escape(str(s0)) )
            
            
        ret.append( "<h3>outgoing to:</h3>" )
        for i, (vertex1, vertex2, edgetype) in enumerate( self.graphdb.all_outgoing( label ) ):
            s0 = State(1,int(currtime))
            wo = WalkOptions()
            wo.hill_reluctance=hill_reluctance
            wo.walking_speed=walking_speed
            s1 = edgetype.walk( s0, wo )
            
            if s1:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;&currtime=%d\">%s@%d</a>"%(vertex2, s1.time, vertex2, s1.time)
            else:
                toterm = "<a href=\"/vertex?label=&quot;%s&quot;\">%s</a>"%(vertex2, vertex2)
            
            ret.append( "%s<br><pre>&nbsp;&nbsp;&nbsp;via %s (<a href=\"/outgoing?label=&quot;%s&quot;&edgenum=%d\">details</a>)</pre>"%(toterm, cgi.escape(repr(edgetype)), vertex1, i) )
            
            if s1:
                ret.append( "<pre>&nbsp;&nbsp;&nbsp;%s</pre>"%cgi.escape(str(s1)) )
        
        wo.destroy()
        
        return "".join(ret)
    vertex.mime = "text/html"
    
    def outgoing(self, label, edgenum):
        all_outgoing = list( self.graphdb.all_outgoing( label ) )
        
        fromv, tov, edge = all_outgoing[edgenum]
        
        return edge.expound()
        
    def incoming(self, label, edgenum):
        all_incoming = list( self.graphdb.all_incoming( label ) )
        
        fromv, tov, edge = all_incoming[edgenum]
        
        return edge.expound()
    
    def str(self):
        return str(self.graphdb)

def main():
    from sys import argv
    usage = "python graphcrawler.py graphdb_filename [port]"
    if len(argv)<2:
      print usage
      exit()

    graphdb_filename = argv[1]
    if len(argv) == 3:
        port = int(argv[2])
    else: port = 8081
    gc = GraphCrawler(graphdb_filename)
    print "serving on port %d" % port
    gc.run_test_server(port=port)
            

if __name__ == '__main__':
    from sys import argv
    usage = "python graphcrawler.py graphdb_filename"
    if len(argv)<2:
      print usage
      exit()

    graphdb_filename = argv[1]

    gc = GraphCrawler(graphdb_filename)
    gc.run_test_server(8081)
