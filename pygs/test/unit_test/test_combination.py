import unittest
from graphserver.core import *

class TestCombination(unittest.TestCase):
    def test_basic(self):
        s1 = Street( "A", 1 )
        c0 = Combination( 1 )
        c0.add( s1 )
        
        assert c0.__class__ == Combination
        assert c0.get( -1 ) == None
        assert c0.get( 0 ).__class__ == Street
        assert c0.get( 1 ) == None
        
        assert c0.walk( State(0,0), WalkOptions() ).weight == 0
        
        s2 = Street( "B", 2 )
        c1 = Combination( 2 )
        c1.add( s1 )
        c1.add( s2 )
        
        assert c1.__class__ == Combination
        assert c1.get( -1 ) == None
        assert c1.get( 0 ).__class__ == Street
        assert c1.get( 0 ).name == "A"
        assert c1.get( 1 ).__class__ == Street
        assert c1.get( 1 ).name == "B"
        assert c1.get( 2 ) == None
        
        assert c1.walk( State(0,0), WalkOptions() ).weight == 0
        assert c1.walk_back( State(0, 100), WalkOptions() ).weight == 0
        
        s3 = Street( "C", 3 )
        
        c2 = Combination( 3 )
        c2.add( s1 )
        c2.add( s2 )
        c2.add( s3 )
        
        assert c2.walk( State(0,0), WalkOptions() ).weight == 0
        assert c2.walk_back( State(0,100), WalkOptions() ).weight == 0
        
        c3 = Combination( 2 )
        c3.add( c1 )
        c3.add( s3 )
        
        assert c3.walk( State(0,0), WalkOptions() ).weight == 0
        assert c3.walk_back( State(0,100), WalkOptions() ).weight == 0
        
        s1.destroy()
        s2.destroy()
        s3.destroy()
        c1.destroy()
        c2.destroy()
        

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCombination)
    unittest.TextTestRunner(verbosity=2).run(suite)
