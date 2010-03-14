import unittest
from graphserver.core import *

class TestGraph(unittest.TestCase):
    
    def test_basic(self):
        """initialize blank graph object"""
        g = Graph()
        assert g
        
        g.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestGraph)
    unittest.TextTestRunner(verbosity=2).run(suite)