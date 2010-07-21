import unittest
from graphserver.core import *

class TestCH( unittest.TestCase ):
    def test_basic(self):
        ch = ContractionHierarchy()
        assert ch.soul
        
        assert ch.upgraph.soul
        assert ch.downgraph.soul

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCH)
    unittest.TextTestRunner(verbosity=2).run(suite)
