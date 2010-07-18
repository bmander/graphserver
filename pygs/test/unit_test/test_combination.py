import unittest
from graphserver.core import *

class TestCombination(unittest.TestCase):
    def test_basic(self):
        s1 = Street( "A", 1 )
        s2 = Street( "B", 2 )
        c1 = Combination( s1, s2 )
        
        assert c1.__class__ == Combination
        assert c1.first.__class__ == Street
        assert c1.first.name == "A"
        assert c1.second.__class__ == Street
        assert c1.second.name == "B"
        
        assert s1.walk( State(0,0), WalkOptions() ).weight == 0
        assert s2.walk( State(0,0), WalkOptions() ).weight == 0
        assert c1.walk( State(0,0), WalkOptions() ).weight == 0
        
        assert s1.walk_back( State(0, 100), WalkOptions() ).time == 100
        assert s2.walk_back( State(0, 100), WalkOptions() ).time == 100
        assert c1.walk_back( State(0, 100), WalkOptions() ).time == 100
        
        s1.destroy()
        s2.destroy()
        c1.destroy()

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCombination)
    unittest.TextTestRunner(verbosity=2).run(suite)
