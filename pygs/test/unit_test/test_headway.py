from graphserver.core import *
import unittest

class TestHeadway(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 0, 1*3600*24, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        assert headway.begin_time == 0
        assert headway.end_time == 1*3600*24
        assert headway.wait_period == 60
        assert headway.transit == 120
        assert headway.trip_id == "HEADWAY"
        assert headway.calendar.soul == sc.soul
        assert headway.timezone.soul == tz.soul
        assert headway.agency == 0
        assert headway.int_service_id == 0
        assert headway.service_id == "WKDY"
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 3600, 2*3600, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = headway.walk( s,WalkOptions() )
        assert ret == None
        
        #before headway
        s = State(1, 0)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 3720
        assert ret.weight == 3720
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #right at beginning of headway
        s = State(1, 3600)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 3720
        assert ret.weight == 120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #in the middle of the headway
        s = State(1, 4000)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 4000+60+120
        assert ret.weight == 60+120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #the last second of the headway
        s = State(1, 2*3600)
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 2*3600+60+120
        assert ret.weight == 60+120
        assert ret.num_transfers == 1
        assert ret.prev_edge.type == 7
        
        #no-transfer
        s = State(1, 4000)
        s.prev_edge = headway = Headway( 3600, 2*3600, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        ret = headway.walk( s,WalkOptions() )
        assert ret.time == 4000+120
        assert ret.weight == 120
        assert ret.num_transfers == 0
        assert ret.prev_edge.type == 7
        assert ret.prev_edge.trip_id == "HEADWAY"
        
    def test_getstate(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        headway = Headway( 0, 1*3600*24, 60, 120, "HEADWAY", sc, tz, 0, "WKDY" )
        
        assert headway.__getstate__() == (0, 1*3600*24, 60, 120, "HEADWAY", sc.soul, tz.soul, 0, "WKDY")
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestHeadway)
    unittest.TextTestRunner(verbosity=2).run(suite)
    