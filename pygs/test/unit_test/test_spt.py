from graphserver.core import Graph, Vertex, Edge, Street, State
import unittest

class TestShortestPathTreePathRetroBasic(unittest.TestCase):
    def setUp(self):
        self.gg = Graph()
        self.A = self.gg.add_vertex( "A" )
        self.B = self.gg.add_vertex( "B" )
        self.a = self.gg.add_edge( "A", "B", Street("a", 10) )

        self.spt = self.gg.shortest_path_tree( "A", "B", State(0) )

    def test_path_retro_basic(self):
        """ShortestPathTree.path_retro works on a trivial graph"""
        
        vertices, edges = self.spt.path_retro( "B" )

        self.assertEqual( vertices[0].label , self.B.label )
        self.assertEqual( vertices[1].label , self.A.label )
        self.assertEqual( edges[0].payload.name , self.a.payload.name )
        
if __name__ == '__main__':
    unittest.main()