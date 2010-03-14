import unittest
from graphserver.core import *
from graphserver import util
import pickle

class TestTimezonePeriod(unittest.TestCase):
    def test_basic(self):
        tzp = TimezonePeriod(0, 100, -10)
        
        assert tzp
        assert tzp.begin_time == 0
        assert tzp.end_time == 100
        assert tzp.utc_offset == -10
        
    def test_dict(self):
        tzp = TimezonePeriod(3, 7, -11)
        
        assert tzp.__getstate__() == (3, 7, -11)
        
        ss = pickle.dumps( tzp )
        laz = pickle.loads( ss )
        assert laz.begin_time == 3
        assert laz.end_time == 7
        assert laz.utc_offset == -11
        
    def test_time_since_midnight(self):
        tzp = TimezonePeriod(0, 24*3600*256, -8*3600)
        
        assert tzp.time_since_midnight( 8*3600 ) == 0
        
        summer_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,6,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,9,1,0,0,0, "America/Los_Angeles" ),
                                     -7*3600 )
                                     
        assert summer_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert summer_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
        winter_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,1,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,4,1,0,0,0, "America/Los_Angeles" ),
                                     -8*3600 )
                                     
        assert winter_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert winter_tzp.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTimezonePeriod)
    unittest.TextTestRunner(verbosity=2).run(suite)