import unittest
from graphserver.core import *
from random import randint

class TestTripBoard(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.int_service_id == 0
        assert tb.timezone.soul == tz.soul
        assert tb.calendar.soul == sc.soul
        assert tb.agency == 0
        assert tb.overage == -1
        
        assert tb.num_boardings == 0
        
        assert tb.type==8
        assert tb.soul
        tb.destroy()
        try:
            print tb
            raise Exception( "should have failed by now" )
        except:
            pass
            
    def test_get_boarding_by_trip_id(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        tb.add_boarding( "trip1", 0, 0 )
        
        assert tb.get_boarding_by_trip_id( "trip1" ) == ("trip1", 0, 0)
        assert tb.get_boarding_by_trip_id( "bogus" ) == None
        
        tb.add_boarding( "trip2", 1, 1 )
        
        assert tb.get_boarding_by_trip_id( "trip1" ) == ("trip1", 0, 0 )
        assert tb.get_boarding_by_trip_id( "trip2" ) == ("trip2", 1, 1 )
        assert tb.get_boarding_by_trip_id( "bogus" ) == None
        
            
    def test_overage(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.overage == -1
        
        tb.add_boarding( "midnight", 24*3600, 0 )
        
        assert tb.overage == 0
        
        tb.add_boarding( "nightowl1", 24*3600+1, 0 )
        
        assert tb.overage == 1
        
        tb.add_boarding( "nightowl2", 24*3600+3600, 0 )
        
        assert tb.overage == 3600
        
    def test_tripboard_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "eleven", 23*3600, 0 )
        tb.add_boarding( "midnight", 24*3600, 0 )
        tb.add_boarding( "one", 25*3600, 0 )
        tb.add_boarding( "two", 26*3600, 0 )
        
        s0 = State(1, 0)
        s1 = tb.walk(s0,WalkOptions())
        self.assertEqual( s1.weight , 82801 )
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 23*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = tb.walk(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = tb.walk(s0,WalkOptions())
        print s1
        self.assertEqual( s1 , None )
        
        
    def test_tripboard_over_midnight_without_hope(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        sc.add_period(2*3600*24,3*3600*24, ['SUN'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,3*3600*24,0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "eleven", 23*3600, 0 )
        tb.add_boarding( "midnight", 24*3600, 0 )
        tb.add_boarding( "one", 25*3600, 0 )
        tb.add_boarding( "two", 26*3600, 0 )
        
        s0 = State(1,3*3600*24) #midnight sunday
        s1 = tb.walk(s0,WalkOptions())
        assert s1 == None
            
    def test_add_single_trip(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "morning", 0, 0 )
        
        assert tb.num_boardings == 1
        
        assert tb.get_boarding( 0 ) == ("morning", 0, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 1 out of bounds"
            
    def test_add_several_in_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "first", 0, 0 )
        
        assert tb.num_boardings == 1
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        
        tb.add_boarding( "second", 50, 0 )
        assert tb.num_boardings == 2
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        tb.add_boarding( "third", 150, 0 )
        assert tb.num_boardings == 3
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
            
        tb.add_boarding( "fourth", 150, 0 )
        assert tb.num_boardings == 4
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0) or tb.get_boarding( 2 ) == ('fourth', 150, 0)
        assert tb.get_boarding( 3 ) == ('third', 150, 0) or tb.get_boarding( 3 ) == ('fourth', 150, 0)
            
    def test_add_several_out_of_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
    
        try:
            tb.get_boarding( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        tb.add_boarding( "fourth", 150, 0 )
        
        assert tb.num_boardings == 1
        assert tb.get_boarding( 0 ) == ('fourth', 150, 0)
        
        tb.add_boarding( "first", 0, 0 )
        assert tb.num_boardings == 2
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('fourth', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        tb.add_boarding( "third", 150, 0 )
        assert tb.num_boardings == 3
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('third', 150, 0)
        assert tb.get_boarding( 2 ) == ('fourth', 150, 0)
        
        try:
            tb.get_boarding( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            tb.get_boarding( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
        
        tb.add_boarding( "second", 50, 0 )
        assert tb.num_boardings == 4
        
        assert tb.get_boarding( 0 ) == ('first', 0, 0)
        assert tb.get_boarding( 1 ) == ('second', 50, 0)
        assert tb.get_boarding( 2 ) == ('third', 150, 0) or tb.get_boarding( 2 ) == ('fourth', 150, 0)
        assert tb.get_boarding( 3 ) == ('third', 150, 0) or tb.get_boarding( 3 ) == ('fourth', 150, 0)
        
    def test_add_several_random(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        for i in range(1000):
            tb.add_boarding( str(i), randint(0,10000), 0 )
            
        last_depart = -1
        for i in range(tb.num_boardings):
            trip_id, depart, stop_sequence = tb.get_boarding(i)
            assert last_depart <= depart
            last_depart = depart
    
    def test_search_boardings_list_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.search_boardings_list(0) == 0
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.search_boardings_list(5) == 0
        assert tb.search_boardings_list(15) == 0
        assert tb.search_boardings_list(20) == 1
        
    def test_get_next_boarding_index_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding_index(0) == -1
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.get_next_boarding_index(5) == 0
        assert tb.get_next_boarding_index(15) == 0
        assert tb.get_next_boarding_index(20) == -1
        
    def test_get_next_boarding_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding(0) == None
        
        tb.add_boarding( "morning", 15, 0 )
        
        assert tb.get_next_boarding(5) == ( "morning", 15, 0 )
        assert tb.get_next_boarding(15) == ( "morning", 15, 0 )
        assert tb.get_next_boarding(20) == None
        
    def test_get_next_boarding_several(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard("WKDY", sc, tz, 0)
        
        assert tb.get_next_boarding(0) == None
        
        tb.add_boarding( "1", 15, 0 )
        
        assert tb.get_next_boarding(5) == ( "1", 15, 0 )
        assert tb.get_next_boarding(15) == ( "1", 15, 0 )
        assert tb.get_next_boarding(20) == None
        
        tb.add_boarding( "2", 25, 0 )
        
        assert tb.get_next_boarding(5) == ( "1", 15, 0 )
        assert tb.get_next_boarding(15) == ( "1", 15, 0 )
        assert tb.get_next_boarding(20) == ( "2", 25, 0 )
        assert tb.get_next_boarding(25) == ( "2", 25, 0 )
        assert tb.get_next_boarding(30) == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "1", 50, 0 )
        tb.add_boarding( "2", 100, 0 )
        tb.add_boarding( "3", 200, 0 )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = tb.walk( s,WalkOptions() )
        assert ret == None
        
        s = State(1, 0)
        ret = tb.walk(s,WalkOptions())
        self.assertEqual( ret.time , 50 )
        self.assertEqual( ret.weight , 51 )
        self.assertEqual( ret.num_transfers , 1 )
        self.assertEqual( ret.dist_walked , 0.0 )
        
        s = State(1, 2)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 49
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 50)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 100)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 100
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 200)
        ret = tb.walk(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 201)
        ret = tb.walk(s,WalkOptions())
        assert ret == None
        
    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        tb = TripBoard( "WKDY", sc, tz, 0 )
        tb.add_boarding( "1", 50, 0 )
        tb.add_boarding( "2", 100, 0 )
        tb.add_boarding( "3", 200, 0 )
        
        s = State(1,100)
        ret = tb.walk_back( s, WalkOptions() )
        assert ret.time == 100
        assert ret.weight == 0
        
    def test_check_yesterday(self):
        """check the previous day for viable departures"""
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 2*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        tb = TripBoard( "WKDY", sc, tz, 0 )
        
        # one boarding - one second after midnight
        tb.add_boarding( "1", 86400+1, 0 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be one second until the next boarding
        s1 = tb.walk( s0, WalkOptions() )
        self.assertEquals( s1.time, 86401 )
        
    def test_check_today(self):
        """given a schedule that runs two consecutive days, find a departure
           given a state on midnight between the two days"""
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        tb = TripBoard( "WKDY", sc, tz, 0 )
        
        # one boarding - pretty early in the morning
        tb.add_boarding( "21SFO1", 26340, 1 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be early morning on the second day
        s1 = tb.walk( s0, WalkOptions() )
        
        self.assertEquals( s1.time, 26340+86400 )
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTripBoard)
    unittest.TextTestRunner(verbosity=2).run(suite)