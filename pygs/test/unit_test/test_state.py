from graphserver.core import *
import unittest

class TestState(unittest.TestCase):
    def test_basic(self):
        s = State(1,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge == None
        assert s.num_agencies == 1
        assert s.service_period(0) == None
        assert s.trip_id == None
        assert s.stop_sequence == -1
        
    def test_basic_multiple_calendars(self):
        s = State(2,0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge == None
        assert s.num_agencies == 2
        assert s.service_period(0) == None
        assert s.service_period(1) == None
        assert s.stop_sequence == -1

    def test_set_cal(self):
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        
        try:
            s.set_calendar_day(1, cal)
            assert False #should have failed by now
        except:
            pass
        
        s.set_service_period(0, sp)
        
        spout = s.service_period(0)
        
        assert spout.begin_time == 0
        assert spout.end_time == 86400
        assert spout.service_ids == [1,2]
        
    def test_destroy(self):
        s = State(1)
        
        s.destroy() #did we segfault?
        
        try:
            print s.time
            assert False #should have popped exception by now
        except:
            pass
        
        try:
            s.destroy()
            assert False
        except:
            pass
        
    def test_clone(self):
        
        s = State(1,0)
        sp = ServicePeriod(0, 1*3600*24, [1,2])
        s.set_service_period(0,sp)
        
        s2 = s.clone()
        
        s.clone()
        
        assert s2.time == 0
        assert s2.weight == 0
        assert s2.dist_walked == 0
        assert s2.num_transfers == 0
        assert s2.prev_edge == None
        assert s2.num_agencies == 1
        assert s2.service_period(0).to_xml() == "<ServicePeriod begin_time='0' end_time='86400' service_ids='1,2'/>"
        assert s2.stop_sequence == -1
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestState)
    unittest.TextTestRunner(verbosity=2).run(suite)