from graphserver.core import *
import unittest
import time

class TestShortestPathTree(unittest.TestCase):
    def setUp(self):
        self.gg = Graph()
        self.A = self.gg.add_vertex( "A" )
        self.B = self.gg.add_vertex( "B" )
        self.a = self.gg.add_edge( "A", "B", Street("a", 10) )

        self.spt = self.gg.shortest_path_tree( "A", "B", State(0) )

    def test_path_retro_basic(self):
        """ShortestPathTree.path_retro works on a trivial graph"""
        
        vertices, edges = self.spt.path_retro( "B" )

        #self.assertEqual( vertices[0].mirror.label , self.B.label )
        #self.assertEqual( vertices[1].mirror.label , self.A.label )
        #self.assertEqual( edges[0].payload.name , self.a.payload.name )
        
    def test_basic(self):
        spt = ShortestPathTree()
        assert spt
        
        spt.destroy()
        
    def test_empty_graph(self):
        spt = ShortestPathTree()
        assert spt.vertices == []
        
        spt.destroy()
        
    def test_add_vertex(self):
        spt = ShortestPathTree()
        v = spt.add_vertex( Vertex("home") )
        assert v.mirror.label == "home"
        
        spt.destroy()
        
    def test_remove_vertex(self):
        spt = ShortestPathTree()
        spt.add_vertex( Vertex("A") )
        spt.get_vertex( "A" ).mirror.label == "A"
        spt.remove_vertex( "A" )
        assert spt.get_vertex( "A" ) == None
        
        spt.add_vertex( Vertex("A") )
        spt.add_vertex( Vertex("B") )
        pl = Street( "AB", 1 )
        spt.set_parent( "A", "B", pl )
        spt.remove_vertex( "A" )
        assert pl.name == "AB"
        assert spt.get_vertex( "A" ) == None
        assert spt.get_vertex( "B" ).mirror.label == "B"
        
    def test_double_add_vertex(self):
        spt = ShortestPathTree()
        v = spt.add_vertex( Vertex("double") )
        assert v.mirror.label == "double"
        assert spt.size == 1
        v = spt.add_vertex( Vertex("double") )
        assert spt.size == 1
        assert v.mirror.label == "double"
        
        spt.destroy()
        
    def test_get_vertex(self):
        spt = ShortestPathTree()
        
        spt.add_vertex( Vertex("home") )
        v = spt.get_vertex("home")
        assert v.mirror.label == "home"
        v = spt.get_vertex("bogus")
        assert v == None
        
        spt.destroy()
        
    def test_add_edge(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.set_parent("home", "work", s)

        assert e
        self.assertEqual( e.from_v.mirror.label, fromv.mirror.label )
        self.assertEqual( e.to_v.mirror.label, tov.mirror.label )
        self.assertEqual( str(e), "<SPTEdge 'home' -> 'work' via <Street name='helloworld' length='1.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/>>" )
        
        spt.destroy()
    
    def test_add_edge_effects_vertices(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.set_parent("home", "work", s)
        
        assert fromv.degree_out==1
        
        spt.destroy()
    
    def test_vertices(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        
        assert spt.vertices
        assert len(spt.vertices)==2
        assert spt.vertices[0].mirror.label == 'home'
        
        spt.destroy()

        
    def test_add_link(self):
        spt = ShortestPathTree()
        
        fromv = spt.add_vertex( Vertex("home") )
        tov = spt.add_vertex( Vertex("work") )
        s = Street( "helloworld", 1 )
        e = spt.set_parent("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = spt.set_parent("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
        spt.destroy()
        
    def test_edgeclass(self):
        spt = ShortestPathTree()
        spt.add_vertex( Vertex("A") )
        spt.add_vertex( Vertex("B") )
        spt.set_parent( "A", "B", Street("AB", 1) )
        
        vv = spt.get_vertex( "A" )
        assert vv.__class__ == SPTVertex

        print vv.outgoing(spt)

        assert vv.outgoing(spt)[0].__class__ == SPTEdge
        assert vv.outgoing(spt)[0].to_v.__class__ == SPTVertex
if __name__ == '__main__':
    unittest.main()
