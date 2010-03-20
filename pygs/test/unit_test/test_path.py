from graphserver.core import Vertex, Edge, Link, Street, Path
import unittest
from graphserver.gsdll import lgs
from ctypes import addressof

class TestPathCreate(unittest.TestCase):
    def test_path_new(self):
        """Create a path object without crashing"""
        path = Path( Vertex("A") )
        
        self.assertTrue( path )
        
    def test_path_empty(self):
        """Path is empty right after first created"""
        pp = Path( Vertex("A") )
        
        self.assertEqual( pp.num_elements, 0 )
        
class TestPathSize(unittest.TestCase):
    def setUp(self):
        self.aa = Vertex("AA")
        self.path = Path( self.aa )
        
    def test_zero(self):
        """getSize returns zero on an empty path"""
        self.assertEquals( self.path.num_elements, 0 )
    
    def test_one(self):
        """getSize returns one after one entry"""
        
        bb = Vertex("BB")
        ee = Edge(self.aa, bb, Link())
        
        self.path.addSegment( bb, ee )
        
        self.assertEqual( self.path.num_elements, 1 )
        
    def test_ten(self):
        """getSize returns ten after ten entries"""
        
        for i in range(10):
            aa = Vertex("AA")
            bb = Vertex("BB")
            payload = Link()
            self.path.addSegment( bb, Edge(aa, bb, payload) )
            
        self.assertEquals( self.path.num_elements, 10 )
        
class TestAddAndGetSegments(unittest.TestCase):
    def setUp(self):
        self.aa = Vertex("A")
        self.bb = Vertex("B")
        self.ep = Link()
        self.path = Path(self.aa)
        
    def test_none(self):
        """behave appropriately when asking for an out-of-bounds index"""
        
        # test out of bounds values
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getVertex, 1 )
        self.assertRaises( IndexError, self.path.getVertex, 10 )
        
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        self.assertRaises( IndexError, self.path.getEdge, 0 )
        self.assertRaises( IndexError, self.path.getEdge, 1 )
        self.assertRaises( IndexError, self.path.getEdge, 10 )
        
        # if you don't add any segments, there's still a single vertex in the path
        self.assertEquals( self.path.getVertex( 0 ).soul, self.aa.soul )
        
    def test_one(self):
        """get a vertex, edge after adding a single segment"""
        
        ee = Edge(self.aa, self.bb, self.ep)
        self.path.addSegment( self.bb, ee )
        
        # out of bounds
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        
        # vertices in bounds
        self.assertEqual( self.path.getVertex(0).soul, self.aa.soul )
        self.assertEqual( self.path.getVertex(1).soul, self.bb.soul )
        
        # edges in bounds
        self.assertEqual( self.path.getEdge(0).soul, ee.soul )
        
        # out of bounds again
        self.assertRaises( IndexError, self.path.getVertex, 2 )
        self.assertRaises( IndexError, self.path.getEdge, 1 )
        
    def test_two(self):
        """get a vertex, edge after adding two segments"""
        
        ee1 = Edge(self.aa, self.bb, Link())
        ee2 = Edge(self.bb, self.aa, Link())
        self.path.addSegment( self.bb, ee1 )
        self.path.addSegment( self.aa, ee2 )
        
        # out of bounds
        self.assertRaises( IndexError, self.path.getVertex, -1 )
        self.assertRaises( IndexError, self.path.getEdge, -1 )
        
        # vertices in bounds
        self.assertEqual( self.path.getVertex(0).soul, self.aa.soul )
        self.assertEqual( self.path.getVertex(1).soul, self.bb.soul )
        self.assertEqual( self.path.getVertex(2).soul, self.aa.soul )
        
        # edges in bounds
        self.assertEqual( self.path.getEdge(0).soul, ee1.soul )
        self.assertEqual( self.path.getEdge(1).soul, ee2.soul )
        
        # out of bounds again
        self.assertRaises( IndexError, self.path.getVertex, 3 )
        self.assertRaises( IndexError, self.path.getEdge, 2 )
        
    def test_expand(self):
        """vertices gettable after resizing"""
        
        # the path length right before a vector expansion
        pathlen = 50
        
        # make a bunch of fake segments
        segments = []
        for i in range(pathlen):
            vv = Vertex(str(i))
            ee = Edge( vv, vv, Link() )
            segments.append( (vv, ee) )
        
        # add those segments to the path
        for vv, ee in segments:
            self.path.addSegment( vv, ee ) 
            
        # check that they're alright
        # check the odd-duck vertex
        self.assertEqual( self.path.getVertex(0).label, "A" )
        
        # check the bunch of fake segments added
        for i in range(1, pathlen+1):
            self.assertEqual( i-1, int(self.path.getVertex(i).label) )
            
        #
        # getting towards the real test - add a segment after the vectors have
        # been expanded
        #
        
        # add it
        vv = Vertex("B")
        ee = Edge(vv, vv, Link())
        self.path.addSegment( vv, ee )
        
        # get it
        self.assertEqual( self.path.getVertex( 51 ).label, "B" )
        
        
if __name__ == '__main__':

    unittest.main()