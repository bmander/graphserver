import unittest
from graphserver.core import *

class TestHeadwayBoard(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "hwtrip1", 0, 1000, 100)
        
        assert hb.calendar.soul == sc.soul
        assert hb.timezone.soul == tz.soul
        
        assert hb.agency == 0
        assert hb.int_service_id == 0
        
        assert hb.trip_id == "hwtrip1"
        
        assert hb.start_time == 0
        assert hb.end_time == 1000
        assert hb.headway_secs == 100
        
        hb.destroy()
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 250
        assert s1.weight == 251
        
        s0 = State(1,200)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 250
        assert s1.weight == 51
        
        s0 = State(1, 500)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 550
        assert s1.weight == 51
        
        s0 = State(1, 1000)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 1050
        assert s1.weight == 51
        
        s0 = State(1, 1001)
        s1 = hb.walk(s0,WalkOptions())
        assert s1 == None
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        hb = HeadwayBoard("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = hb.walk(s0, WalkOptions())
        s2 = hb.walk_back(s1, WalkOptions())
        assert s2.trip_id == None
        
    def test_tripboard_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        hb = HeadwayBoard( "WKDY", sc, tz, 0, "owl", 23*3600, 26*3600, 100 )
        
        s0 = State(1, 0)
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 82901
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 25*3600+100
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = hb.walk(s0,WalkOptions())
        assert s1.time == 26*3600+100
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = hb.walk(s0,WalkOptions())
        assert s1 == None
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadwayBoard)
    unittest.TextTestRunner(verbosity=2).run(suite)