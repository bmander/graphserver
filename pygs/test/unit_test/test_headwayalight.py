import unittest
from graphserver.core import *

class TestHeadwayAlight(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "hwtrip1", 0, 1000, 100)
        
        assert ha.calendar.soul == sc.soul
        assert ha.timezone.soul == tz.soul
        
        assert ha.agency == 0
        assert ha.int_service_id == 0
        
        assert ha.trip_id == "hwtrip1"
        
        assert ha.start_time == 0
        assert ha.end_time == 1000
        assert ha.headway_secs == 100
        
        ha.destroy()
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        # 200 after end of headway
        s0 = State(1,1200)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 1000
        assert s1.weight == 201
        
        # at very end of the headway
        s0 = State(1,1000)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 1000
        assert s1.weight == 1
        
        # in the middle of headway period
        s0 = State(1, 500)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 500
        assert s1.weight == 1
        
        # at the very beginning of the headway period
        s0 = State(1, 200)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 200
        assert s1.weight == 1
        
        # before beginning of headway period
        s0 = State(1, 199)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1 == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        ha = HeadwayAlight("WKDY", sc, tz, 0, "tr1", 200, 1000, 50)
        
        s0 = State(1,0)
        s1 = ha.walk(s0, WalkOptions())
        assert s1.trip_id == None
        
    def test_headwayalight_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        ha = HeadwayAlight( "WKDY", sc, tz, 0, "owl", 23*3600, 26*3600, 100 )
        
        # just past the end
        s0 = State(1, 26*3600+100)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 101
        assert s1.service_period(0).service_ids == [1]
        
        # right at the end
        s0 = State(1, 26*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        # in the middle, over midnight
        s0 = State(1, 25*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        # in the middle, at midnight
        s0 = State(1, 24*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        #before midnight, at the beginning
        s0 = State(1, 23*3600 )
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1.time == 23*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600-1)
        s1 = ha.walk_back(s0,WalkOptions())
        assert s1 == None
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadwayAlight)
    unittest.TextTestRunner(verbosity=2).run(suite)