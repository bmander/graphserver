import unittest
from graphserver.core import *

class TestCH( unittest.TestCase ):
    def test_basic(self):
        gup = Graph()
        gdown = Graph()
        
        ch = ContractionHierarchy(gup, gdown)
        assert ch.soul
        
        assert ch.upgraph.soul == gup.soul
        assert ch.downgraph.soul == gdown.soul

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCH)
    unittest.TextTestRunner(verbosity=2).run(suite)
