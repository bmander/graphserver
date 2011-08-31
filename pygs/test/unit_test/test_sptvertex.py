import unittest
from graphserver.core import *

class TestSPTVertex(unittest.TestCase):
    def test_basic(self):
        gg = Graph()
        spt = ShortestPathTree()
        vv = Vertex(gg, "home")
        v=SPTVertex( spt, vv )

	assert v.mirror.soul == vv.soul
        assert v

    def test_init_hop(self):
        gg = Graph()
        spt = ShortestPathTree()
        v = SPTVertex( spt, Vertex(gg, "A") )
	assert v.hop == 0

        v = SPTVertex( spt, Vertex(gg, "B"), 1 )
	assert v.hop == 1
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        gg = Graph()
        spt = ShortestPathTree()
        v=SPTVertex( spt, Vertex(gg, "home") )
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        gg = Graph()
        spt = ShortestPathTree()
        v=SPTVertex( spt, Vertex(gg, "home") )
        self.assertEqual( v.mirror.label , "home" )
    
    def test_incoming(self):
        gg = Graph()
        spt = ShortestPathTree()
        v=SPTVertex( spt, Vertex(gg, "home") )

        # a blank sptvertex has a MAX_UINT32 set for the parent index
        self.assertEqual( libgs.sptvGetParent( v.soul ) , 4294967295 )
        
    def test_outgoing(self):
        gg = Graph()
        spt = ShortestPathTree()
        v=SPTVertex( spt, Vertex(gg, "home") )
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        gg = Graph()
        spt = ShortestPathTree()
        v = SPTVertex( spt, Vertex(gg, "home") )
        self.assertEqual( str(v) , "<SPTVertex degree_out=0 mirror.label=home>" )


if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestSPTVertex)
    unittest.TextTestRunner(verbosity=2).run(suite)
