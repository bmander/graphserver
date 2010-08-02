import unittest
from graphserver.util import TimeHelpers

class TestUtil(unittest.TestCase): 
    
    def test_basic(self):
	assert TimeHelpers.localtime_to_unix(2008,10,12,6,0,0,"Europe/Paris") == 1223784000
	assert str(TimeHelpers.unix_to_localtime(1199181360, "America/New_York")) == "2008-01-01 04:56:00-05:00"
	assert TimeHelpers.unixtime_to_daytimes(1219834260, "America/Los_Angeles") == (13860, 100260, 186660)
	assert str(TimeHelpers.unix_to_localtime(1221459000, "America/Chicago")) == "2008-09-15 01:10:00-05:00" 
	assert TimeHelpers.unixtime_to_daytimes(1230354000, "America/Chicago") == (82800, 169200, 255600)
	assert TimeHelpers.unix_time(2008,8,27,12,0,0,-7*3600) == 1219863600
	assert TimeHelpers.localtime_to_unix(2008,8,27,12,0,0,"America/Los_Angeles") == 1219863600
	assert str(TimeHelpers.unix_to_localtime(1219863600, "America/Los_Angeles")) == "2008-08-27 12:00:00-07:00"

if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestUtil)
    unittest.TextTestRunner(verbosity=2).run(suite)
