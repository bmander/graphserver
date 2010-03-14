from graphserver.core import *
import unittest
import pickle

class TestServicePeriod(unittest.TestCase):
    def test_service_period(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        assert(c.begin_time == 0)
        assert(c.end_time == 1*3600*24)
        assert(len(c.service_ids) == 2)
        assert(c.service_ids == [1,2])
        
    def test_fast_forward_rewind(self):
        cc = ServiceCalendar()
        cc.add_period( 0, 100, ["A","B"] )
        cc.add_period( 101, 200, ["C","D"] )
        cc.add_period( 201, 300, ["E","F"] )
        
        hh = cc.head
        ff = hh.fast_forward()
        assert ff.begin_time==201
        pp = ff.rewind()
        assert pp.begin_time==0
        
    def test_midnight_datum(self):
        c = ServicePeriod( 0, 1*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 500, 1000, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 0
        
        c = ServicePeriod( 1*3600*24, 2*3600*24, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        assert c.datum_midnight(timezone_offset=3600) == 82800
        
        c = ServicePeriod( 1*3600*24+50, 1*3600*24+60, [1])
        
        assert c.datum_midnight(timezone_offset=0) == 86400
        assert c.datum_midnight(timezone_offset=-3600) == 3600
        
    def test_normalize_time(self):
        c = ServicePeriod(0, 1*3600*24, [1,2])
        
        assert c.normalize_time( 0, 0 ) == 0
        assert c.normalize_time( 0, 100 ) == 100
        
    def test_pickle(self):
        cc = ServicePeriod(0, 100, [1,2,3,4,5])
        
        ss = pickle.dumps( cc )
        laz = pickle.loads( ss )
        
        assert laz.__getstate__() == cc.__getstate__()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestServicePeriod)
    unittest.TextTestRunner(verbosity=2).run(suite)