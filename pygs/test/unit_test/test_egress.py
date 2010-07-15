from graphserver.core import *
import unittest

class TestEgress(unittest.TestCase):
    def test_street(self):
        s = Egress("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<Egress name='mystreet' length='1.100000' />"
        
    def test_destroy(self):
        s = Egress("mystreet", 1.1)
        s.destroy()
        
        assert s.soul==None
        
    def test_street_big_length(self):
        s = Egress("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Egress name='longstreet' length='240000.000000' />"
        
    def test_walk(self):
        s = Egress("longstreet", 10)
        wo = WalkOptions()
        wo.walking_reluctance = 1
        after = s.walk(State(0,0),wo)
        wo.destroy()
        self.assertEqual( after.time , 9 )
        self.assertEqual( after.weight , 9 )
        self.assertEqual( after.dist_walked , 10 )
        self.assertEqual( after.prev_edge.__class__ , Egress )
        self.assertEqual( after.prev_edge.name , "longstreet" )
        self.assertEqual( after.num_agencies , 0 )
        
    def test_walk_back(self):
        s = Egress("longstreet", 10)
        
        before = s.walk_back(State(0,100),WalkOptions())
        self.assertEqual( before.time , 100 - (9) )
        self.assertEqual( before.weight , 9 )
        self.assertEqual( before.dist_walked , 10.0 )
        self.assertEqual( before.prev_edge.type , 12 )
        self.assertEqual( before.prev_edge.name , "longstreet" )
        self.assertEqual( before.num_agencies , 0 )
        
    def test_getstate(self):
        s = Egress("longstreet", 2)
        
        assert s.__getstate__() == ('longstreet', 2)
        
    def test_graph(self):
        g = Graph()
        g.add_vertex("E")
        g.add_vertex("S")
        g.add_edge("E", "S", Egress("E2S",10))
        
        spt = g.shortest_path_tree("E", "S", State(0,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("S").state.dist_walked==10

        spt.destroy()
        g.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestEgress)
    unittest.TextTestRunner(verbosity=2).run(suite)
