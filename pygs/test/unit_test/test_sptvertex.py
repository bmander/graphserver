import unittest
from graphserver.core import *

class TestSPTVertex(unittest.TestCase):
    def test_basic(self):
        v=SPTVertex("home")
        assert v

    def test_init_hop(self):
        v = SPTVertex( "A" )
	assert v.hop == 0

	v = SPTVertex( "B", 1 )
	assert v.hop == 1
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        v=SPTVertex("home")
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        v=SPTVertex("home")
        print v.label
        assert v.label == "home"
    
    def test_incoming(self):
        v=SPTVertex("home")
        assert v.incoming == []
        assert v.degree_in == 0
        
    def test_outgoing(self):
        v=SPTVertex("home")
        assert v.outgoing == []
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        v = SPTVertex("home")
        assert v.to_xml() == "<SPTVertex degree_out='0' degree_in='0' label='home'/>"


if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestSPTVertex)
    unittest.TextTestRunner(verbosity=2).run(suite)
