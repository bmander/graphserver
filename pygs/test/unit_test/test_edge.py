import unittest
from graphserver.core import *

class TestEdge(unittest.TestCase):
    def test_basic(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        assert e1.enabled == True
        
        e1.enabled = False
        assert e1.enabled == False
        
    def test_walk(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        assert e1.walk( State(0,0), wo ) is not None
        assert e1.walk( State(0,0), wo ).weight == 10
        
    def test_disable(self):
        v1 = Vertex( "A" )
        v2 = Vertex( "B" )
        e1 = Edge( v1, v2, Street( "atob", 10.0 ) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
    
        assert e1.walk( State(0,0), wo ) is not None
        assert e1.walk( State(0,0), wo ).weight == 10
        
        e1.enabled = False
        
        assert e1.walk( State(0,0), WalkOptions() ) == None
        
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        heavy = Street( "Heavy", 100 )
        light = Street( "Light", 1 )
        gg.add_edge( "A", "B", heavy )
        gg.add_edge( "A", "B", light )
        
        assert gg.shortest_path_tree( "A", "B", State(0,0), WalkOptions() ).path("B")[1][0].payload.name == "Light"
        
        lightedge = gg.get_vertex("A").outgoing[0]
        lightedge.enabled = False
        
        assert gg.shortest_path_tree( "A", "B", State(0,0), WalkOptions() ).path("B")[1][0].payload.name == "Heavy"
        
    def test_disable_vertex(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_vertex( "D" )
        gg.add_edge( "A", "B", Street( "atob", 1 ) )
        gg.add_edge( "B", "D", Street( "btod", 1 ) )
        gg.add_edge( "A", "C", Street( "atoc", 1 ) )
        gg.add_edge( "C", "D", Street( "ctod", 1 ) )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == True
            
        gg.set_vertex_enabled( "B", False )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == False
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == False
            
        for edge in gg.get_vertex("C").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("C").incoming:
            assert edge.enabled == True
            
        gg.set_vertex_enabled( "B", True )
        
        for edge in gg.get_vertex("B").outgoing:
            assert edge.enabled == True
        for edge in gg.get_vertex("B").incoming:
            assert edge.enabled == True
            
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestEdge)
    unittest.TextTestRunner(verbosity=2).run(suite)
