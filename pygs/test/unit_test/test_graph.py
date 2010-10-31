import unittest
from graphserver.core import *
import time


class TestGraph(unittest.TestCase):
    
    def test_basic(self):
        g = Graph()
        assert g
        
        g.destroy()
        
    def test_empty_graph(self):
        g = Graph()
        assert g.vertices == []
        
        g.destroy()
        
    def test_add_vertex(self):
        g = Graph()
        v = g.add_vertex("home")
        assert v.label == "home"
        
        g.destroy()
        
    def test_remove_vertex(self):
        g = Graph()
        g.add_vertex( "A" )
        g.get_vertex( "A" ).label == "A"
        g.remove_vertex( "A" )
        assert g.get_vertex( "A" ) == None
        
    def test_double_add_vertex(self):
        g = Graph()
        v = g.add_vertex("double")
        assert v.label == "double"
        assert g.size == 1
        v = g.add_vertex("double")
        assert g.size == 1
        assert v.label == "double"
        
        g.destroy()
        
    def test_get_vertex(self):
        g = Graph()
        
        g.add_vertex("home")
        v = g.get_vertex("home")
        assert v.label == "home"
        v = g.get_vertex("bogus")
        assert v == None
        
        g.destroy()
        
    def test_add_edge(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        assert e
        assert e.from_v.label == "home"
        assert e.to_v.label == "work"
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/></Edge>"
        
        g.destroy()
    
    def test_add_edge_effects_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert fromv.degree_out==1
        assert tov.degree_in==1
        
        g.destroy()
    
    def test_vertices(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        assert g.vertices
        assert len(g.vertices)==2
        assert g.vertices[0].label == 'home'
        
        g.destroy()
    
    def test_shortest_path_tree(self):
        g = Graph()
        
        # add two vertices, home and work
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        # add two street edges, one going in each direction
        g.add_edge("home", "work", Street( "helloworld", 10 ))
        g.add_edge("work", "home", Street("backwards",10) )
        
        # get the shortest path tree
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("home").state.weight==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        self.assertTrue( spt.get_vertex("work").state.weight > 0 )
        
        spt.destroy()
        g.destroy()
        
    def test_bogus_origin(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        self.assertRaises(Exception, g.shortest_path_tree, "bogus", "work", State(g.numagencies,0), WalkOptions())
        
        self.assertRaises(Exception, g.shortest_path_tree_retro, "home", "bogus", State(g.numagencies,0), WalkOptions())
        
    def test_spt_retro(self):
        
        g = Graph()
        
        # add two vertices
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        # hook them to each other
        g.add_edge("home", "work", Street( "helloworld", 100 ))
        g.add_edge("work", "home", Street("backwards",100 ) )
        
        # find the path from work to home to arrive at work at 100
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,100), WalkOptions())
        
        assert spt
        assert spt.__class__ == ShortestPathTree
        self.assertEqual( spt.get_vertex("home").degree_out , 0 )
        self.assertEqual( spt.get_vertex("home").degree_in , 1 )
        self.assertTrue( spt.get_vertex("home").state.weight > 0 )
        self.assertEqual( spt.get_vertex("work").degree_in , 0 )
        self.assertEqual( spt.get_vertex("work").degree_out , 1 )
        self.assertEqual( spt.get_vertex("work").state.weight , 0 )
        
        spt.destroy()
        g.destroy()
        
    def test_spt_retro_chain(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        
        g.add_edge( "A", "B", Street( "AB", 1 ) )
        g.add_edge( "B", "C", Street( "BC", 1 ) )
        g.add_edge( "C", "D", Street( "CD", 1 ) )
        
        spt = g.shortest_path_tree_retro( "A", "D", State(g.numagencies,1000), WalkOptions() )
        
        assert spt.get_vertex( "A" ).state.time
        
        spt.destroy()
        
        
    def test_shortst_path_tree_link(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("work").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
        spt.destroy()
        g.destroy()
        
    def test_spt_link_retro(self):
        g = Graph()
        
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("work").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
        
    def test_walk_longstreet(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 24000 )
        e = g.add_edge("home", "work", s)
        
        wo = WalkOptions()
        sprime = e.walk(State(g.numagencies,0), wo)
        
        self.assertTrue( sprime.time > 0 )
        self.assertTrue( sprime.weight > 0 )
        self.assertEqual( sprime.dist_walked, 24000.0 )
        self.assertEqual( sprime.num_transfers, 0 )
        
        wo.destroy()

        g.destroy()
        
    def xtestx_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies,0))
        
        assert spt.get_vertex("home").degree_out == 1
        
        spt.destroy()
        g.destroy()
            
    def test_shortest_path_tree_retro(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(g.numagencies,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
        
        spt.destroy()
        g.destroy()
    
    def test_shortest_path(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(g.numagencies), WalkOptions())
        sp = spt.path("work")
        
        assert sp
        
    def xtestx_shortest_path_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State(g.numagencies))
        
        assert sp
        
    def test_add_link(self):
        g = Graph()
        
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = g.add_edge("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
        g.destroy()
        
    def test_basic(self):
        g = Graph()
        
        g.add_vertex( "A" )
        g.add_vertex( "B" )
        g.add_vertex( "C" )
        g.add_vertex( "D" )
        g.add_vertex( "E" )
        g.add_edge( "A", "B", Street("atob", 10) )
        g.add_edge( "A", "C", Street("atoc", 10) )
        g.add_edge( "C", "D", Street("ctod", 10) )
        g.add_edge( "B", "D", Street("btod", 10) )
        g.add_edge( "D", "E", Street("btoe", 10) )
        
        wo = WalkOptions()
        wo.walking_speed = 1
        spt = g.shortest_path_tree( "A", None, State(1,0), wo )

    def test_hop_limit(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_vertex( "D" )
        gg.add_vertex( "E" )
        gg.add_edge( "A", "B", Street( "AB", 1 ) )
        gg.add_edge( "B", "C", Street( "BC", 1 ) )
        gg.add_edge( "C", "D", Street( "CD", 1 ) )
        gg.add_edge( "D", "E", Street( "DE", 1 ) )
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions() )
        assert spt.get_vertex( "E" ).state.weight == 0
        spt.destroy()
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions(), hoplimit=1 )
        assert spt.get_vertex("A") != None
        assert spt.get_vertex("B") != None
        assert spt.get_vertex("C") == None
        assert spt.get_vertex("D") == None
        assert spt.get_vertex("E") == None
        
        spt = gg.shortest_path_tree( "A", "E", State(0,0), WalkOptions(), hoplimit=3 )
        assert spt.get_vertex("A") != None
        assert spt.get_vertex("B") != None
        assert spt.get_vertex("C") != None
        assert spt.get_vertex("D") != None
        assert spt.get_vertex("E") == None
        
    def test_traverse(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        gg.add_vertex( "C" )
        gg.add_edge( "A", "B", Street("AB", 1) )
        gg.add_edge( "A", "C", Street("AC", 1) )
        
        vv = gg.get_vertex( "A" )
        assert [ee.payload.name for ee in vv.outgoing] == ["AC", "AB"]
            
    def test_ch(self):
        gg = Graph()
        gg.add_vertex( "A" )
        gg.add_vertex( "B" )
        ab = gg.add_edge( "A", "B", Street( "AB", 1 ) )
        ba = gg.add_edge( "B", "A", Street( "BA", 1 ) )
        
        absoul = gg.get_vertex("A").outgoing[0].payload.soul
        basoul = gg.get_vertex("B").outgoing[0].payload.soul
        
        ch = gg.get_contraction_hierarchies( WalkOptions() )
        
        assert ch.upgraph.get_vertex("A").outgoing[0].payload.soul == absoul
        assert ch.downgraph.get_vertex("B").outgoing[0].payload.soul == basoul

if __name__ == '__main__':    
    unittest.main()
