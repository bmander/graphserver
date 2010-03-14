import unittest
from graphserver.core import *
from graphserver import util
import pickle

class TestTimezone(unittest.TestCase):
    def test_basic(self):
        tz = Timezone()
        
        assert tz
        assert tz.head == None
        
    def test_add_timezone(self):
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 100, -8*3600) )
        
        period = tz.head
        assert period.begin_time == 0
        assert period.end_time == 100
        assert period.utc_offset == -8*3600
        
    def test_period_of(self):
        tz = Timezone()
        tzp = TimezonePeriod(0, 100, -8*3600)
        tz.add_period( tzp )
        
        assert tz.period_of(-1) == None
        
        tzpprime = tz.period_of(0)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(50)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(100)
        assert tzpprime.soul == tzp.soul
        
        tzpprime = tz.period_of(101)
        assert tzpprime == None
    
    def test_utc_offset(self):
        tz = Timezone()
        tzp = TimezonePeriod(0, 100, -8*3600)
        tz.add_period( tzp )
        
        try:
            tz.utc_offset( -1 )
            raise Exception("never make it this far")
        except Exception, ex:
            assert str(ex) == "-1 lands within no timezone period"
            
        assert tz.utc_offset(0) == -8*3600
        assert tz.utc_offset(50) == -8*3600
        assert tz.utc_offset(100) == -8*3600
        
        try:
            tz.utc_offset( 101 )
            raise Exception("never make it this far")
        except Exception, ex:
            assert str(ex) == "101 lands within no timezone period"
            
    def test_add_multiple(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(100, 199, -7*3600)
        p3 = TimezonePeriod(200, 299, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        assert tz.head.soul == p1.soul
        assert tz.head.next_period.soul == p2.soul
        assert tz.head.next_period.next_period.soul == p3.soul
        
        assert tz.period_of(-1) == None
        assert tz.period_of(0).soul == p1.soul
        assert tz.period_of(99).soul == p1.soul
        assert tz.period_of(100).soul == p2.soul
        assert tz.period_of(199).soul == p2.soul
        assert tz.period_of(200).soul == p3.soul
        assert tz.period_of(299).soul == p3.soul
        assert tz.period_of(300) == None
        
    def test_add_multiple_gaps_and_out_of_order(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p2 )
        tz.add_period( p1 )
        tz.add_period( p3 )
        
        assert tz.period_of(-1) == None
        assert tz.period_of(0).soul == p1.soul
        assert tz.period_of(99).soul == p1.soul
        assert tz.period_of(100) == None
        assert tz.period_of(150) == None
        assert tz.period_of(200).soul == p2.soul
        assert tz.period_of(300) == None
        assert tz.period_of(550).soul == p3.soul
        assert tz.period_of(600) == None
        
    def test_utc_offset_with_gaps(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        try:
            tz.utc_offset(-1)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "-1 lands within no timezone period"
            
        assert tz.utc_offset(0) == -8*3600
        assert tz.utc_offset(99) == -8*3600
        
        try:
            tz.utc_offset(150)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "150 lands within no timezone period"
            
        assert tz.utc_offset(550) == -8*3600
        
        try:
            tz.utc_offset(600)
            raise Exception( "next make it this far" )
        except Exception, ex:
            assert str(ex) == "600 lands within no timezone period"
            
    def test_generate(self):
        
        tz = Timezone.generate("America/Los_Angeles")
        
        assert tz.utc_offset(1219863600) == -7*3600 #august 27, 2008, noon America/Los_Angeles
        assert tz.utc_offset(1199217600) == -8*3600 #january 1, 2008, noon America/Los_Angeles
        
        print tz.utc_offset(1205056799) == -8*3600 #second before DST
        print tz.utc_offset(1205056800) == -7*3600 #second after DST
        
    def test_pickle(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 99, -8*3600)
        p2 = TimezonePeriod(200, 299, -7*3600)
        p3 = TimezonePeriod(500, 599, -8*3600)
        tz.add_period( p1 )
        tz.add_period( p2 )
        tz.add_period( p3 )
        
        assert tz.__getstate__() == [(0, 99, -28800), (200, 299, -25200), (500, 599, -28800)]
        
        ss = pickle.dumps( tz )
        laz = pickle.loads( ss )
        assert laz.period_of( 50 ).__getstate__() == (0, 99, -8*3600)
        assert laz.period_of( 250 ).__getstate__() == (200, 299, -7*3600)
        assert laz.period_of( 550 ).__getstate__() == (500, 599, -8*3600)
        
    def test_time_since_midnight(self):
        tz = Timezone()
        p1 = TimezonePeriod(0, 24*3600*256, -8*3600)
        tz.add_period( p1 )
        
        assert tz.time_since_midnight( 8*3600 ) == 0
        
        tz = Timezone()
        summer_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,6,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,9,1,0,0,0, "America/Los_Angeles" ),
                                     -7*3600 )
        tz.add_period( summer_tzp )
                                     
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 7, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
        tz = Timezone()
        winter_tzp = TimezonePeriod( util.TimeHelpers.localtime_to_unix( 2008,1,1,0,0,0, "America/Los_Angeles" ),
                                     util.TimeHelpers.localtime_to_unix( 2008,4,1,0,0,0, "America/Los_Angeles" ),
                                     -8*3600 )
        tz.add_period( winter_tzp )
                                     
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2,1,0,0,0,"America/Los_Angeles" ) ) == 0
        assert tz.time_since_midnight( util.TimeHelpers.localtime_to_unix( 2008, 2, 2, 2, 0, 0, "America/Los_Angeles" ) ) == 3600*2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTimezone)
    unittest.TextTestRunner(verbosity=2).run(suite)
    