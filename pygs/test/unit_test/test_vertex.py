from graphserver.core import *
import unittest

class TestVertex(unittest.TestCase):
    def test_basic(self):
        """create a vertex"""
        v=Vertex("home")
        assert v
        
    def test_destroy(self): #mostly just check that it doesn't segfault. the stress test will check if it works or not.
        """destroy a vertex"""
        v=Vertex("home")
        v.destroy()
        
        try:
            v.label
            assert False #pop exception by now
        except:
            pass
        
    def test_label(self):
        """set the vertex label"""
        v=Vertex("home")
        assert v.label == "home"
    
    def test_incoming(self):
        """new vertex has no incoming edges"""
        v=Vertex("home")
        assert v.incoming == []
        assert v.degree_in == 0
        
    def test_outgoing(self):
        """new vertex has no outgoing edges"""
        v=Vertex("home")
        assert v.outgoing == []
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        """vertex can output itself to xml"""
        v = Vertex("home")
        assert v.to_xml() == "<Vertex degree_out='0' degree_in='0' label='home'/>"
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestVertex)
    unittest.TextTestRunner(verbosity=2).run(suite)
