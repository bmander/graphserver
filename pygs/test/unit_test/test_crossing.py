import unittest
from graphserver.core import *

class TestCrossing(unittest.TestCase):
    
    def test_basic(self):
        
        cr = Crossing()
        
        assert cr
        assert cr.soul
        assert cr.size == 0
        assert cr.get_crossing_time( "1" ) == None
        assert cr.get_crossing( 0 ) == None
        
    def test_add_crossing(self):
        cr = Crossing()
        
        cr.add_crossing_time( "1", 10 )
        
        assert cr.size == 1
        assert cr.get_crossing_time( "1" ) == 10
        assert cr.get_crossing( 0 ) == ("1", 10)
        
        cr.add_crossing_time( "2", 20 )
        cr.add_crossing_time( "3", 30 )
        
        assert cr.size == 3
        assert cr.get_crossing_time( "1" ) == 10
        assert cr.get_crossing_time( "2" ) == 20
        
        assert cr.get_crossing( 0 ) == ('1', 10)
        assert cr.get_crossing( 1 ) == ('2', 20)
        assert cr.get_crossing( 2 ) == ('3', 30)
        
    def test_pickle_and_reconstitute(self):
        cr = Crossing()
        
        cr.add_crossing_time( "1", 10 )
        cr.add_crossing_time( "2", 20 )
        cr.add_crossing_time( "3", 30 )
        
        state = cr.__getstate__()
        
        cr2 = Crossing.reconstitute(state, None)
        
        assert cr2.size==3
        assert cr.get_crossing( 0 ) == ('1', 10)
        assert cr.get_crossing( 1 ) == ('2', 20)
        assert cr.get_crossing( 2 ) == ('3', 30)
        
    def test_walk(self):
        
        cr = Crossing()
        cr.add_crossing_time("1", 10)
        
        s = State(1, 0)
        ret = cr.walk(s,WalkOptions())
        
        # state has no trip_id, shouldn't evaluate at all
        assert ret == None
        
        s.dangerous_set_trip_id( "1" )
        s1 = cr.walk(s,WalkOptions())
        assert s1.time == 10
        assert s1.weight == 10
        
    def test_walk_back(self):
        
        cr = Crossing()
        cr.add_crossing_time("1", 10)
        
        s = State(1, 10)
        ret = cr.walk_back(s, WalkOptions())
        assert ret == None
        
        s.dangerous_set_trip_id( "1" )
        s1 = cr.walk_back(s, WalkOptions())
        assert s1.time == 0
        assert s1.weight == 10
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestCrossing)
    unittest.TextTestRunner(verbosity=2).run(suite)