import unittest
from graphserver.core import *
from random import randint

class TestTripAlight(unittest.TestCase):
    def test_basic(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.int_service_id == 0
        assert al.timezone.soul == tz.soul
        assert al.calendar.soul == sc.soul
        assert al.agency == 0
        assert al.overage == 0
        
        assert al.num_alightings == 0
        
        assert al.type == 10
        assert al.soul
        al.destroy()
        assert al.soul == None
        
    def test_get_alighting_by_trip_id( self ):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        al.add_alighting( "trip1", 0, 0 )
        al.get_alighting_by_trip_id( "trip1" ) == ("trip1", 0, 0)
        assert al.get_alighting_by_trip_id( "bogus" ) == None
        
        al.add_alighting( "trip2", 1, 1 )
        
        assert al.get_alighting_by_trip_id( "trip1" ) == ("trip1", 0, 0 )
        assert al.get_alighting_by_trip_id( "trip2" ) == ("trip2", 1, 1 )
        assert al.get_alighting_by_trip_id( "bogus" ) == None


    def test_overage(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.overage == 0
        
        al.add_alighting( "midnight", 24*3600, 0 )
        
        assert al.overage == 0
        
        al.add_alighting( "nightowl1", 24*3600+1, 0 )
        
        assert al.overage == 1
        
        al.add_alighting( "nightowl2", 24*3600+3600, 0 )
        
        assert al.overage == 3600

    def test_alight_over_midnight(self):
        
        sc = ServiceCalendar()
        sc.add_period(0, 1*3600*24, ['WKDY'])
        sc.add_period(1*3600*24,2*3600*24, ['SAT'])
        tz = Timezone()
        tz.add_period( TimezonePeriod(0,2*3600*24,0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "eleven", 23*3600, 0 )
        al.add_alighting( "midnight", 24*3600, 0 )
        al.add_alighting( "one", 25*3600, 0 )
        al.add_alighting( "two", 26*3600, 0 )
        
        s0 = State(1, 0)
        s1 = al.walk_back(s0,WalkOptions())
        assert s1 == None
        
        s0 = State(1, 23*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [0]
        
        s0 = State(1, 24*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 25*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 25*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600 )
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 1
        assert s1.service_period(0).service_ids == [1]
        
        s0 = State(1, 26*3600+1)
        s1 = al.walk_back(s0,WalkOptions())
        assert s1.time == 26*3600
        assert s1.weight == 2
        assert s1.service_period(0).service_ids == [1]

    def test_add_single_trip(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "morning", 0, 0 )
        
        assert al.num_alightings == 1
        
        assert al.get_alighting( 0 ) == ("morning", 0, 0)
        
        try:
            al.get_alighting( -1 )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 1 )
        except Exception, ex:
            assert str(ex) == "Index 1 out of bounds"

    def test_add_several_in_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "first", 0, 0 )
        
        assert al.num_alightings == 1
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        
        al.add_alighting( "second", 50, 0 )
        assert al.num_alightings == 2
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        al.add_alighting( "third", 150, 0 )
        assert al.num_alightings == 3
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
            
        al.add_alighting( "fourth", 150, 0 )
        assert al.num_alightings == 4
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0) or al.get_alighting( 2 ) == ('fourth', 150, 0)
        assert al.get_alighting( 3 ) == ('third', 150, 0) or al.get_alighting( 3 ) == ('fourth', 150, 0)

    def test_add_several_out_of_order(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
    
        try:
            al.get_alighting( 0 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 0 out of bounds"
    
        al.add_alighting( "fourth", 150, 0 )
        
        assert al.num_alightings == 1
        assert al.get_alighting( 0 ) == ('fourth', 150, 0)
        
        al.add_alighting( "first", 0, 0 )
        assert al.num_alightings == 2
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('fourth', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 2 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 2 out of bounds"

        al.add_alighting( "third", 150, 0 )
        assert al.num_alightings == 3
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('third', 150, 0)
        assert al.get_alighting( 2 ) == ('fourth', 150, 0)
        
        try:
            al.get_alighting( -1 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index -1 out of bounds"
            
        try:
            al.get_alighting( 3 )
            raise Exception( "should have popped error by now" )
        except Exception, ex:
            assert str(ex) == "Index 3 out of bounds"
        
        al.add_alighting( "second", 50, 0 )
        assert al.num_alightings == 4
        
        assert al.get_alighting( 0 ) == ('first', 0, 0)
        assert al.get_alighting( 1 ) == ('second', 50, 0)
        assert al.get_alighting( 2 ) == ('third', 150, 0) or al.get_alighting( 2 ) == ('fourth', 150, 0)
        assert al.get_alighting( 3 ) == ('third', 150, 0) or al.get_alighting( 3 ) == ('fourth', 150, 0)

    def test_add_several_random(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        for i in range(1000):
            al.add_alighting( str(i), randint(0,10000), 0 )
            
        last_arrival = -1
        for i in range(al.num_alightings):
            trip_id, arrival, stop_sequence = al.get_alighting(i)
            assert last_arrival <= arrival
            last_arrival = arrival
            

    
    def test_search_boardings_list_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.search_alightings_list(0) == 0
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.search_alightings_list(5) == 0
        assert al.search_alightings_list(15) == 0
        assert al.search_alightings_list(20) == 1
        

        
    def test_get_last_alighting_index_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting_index(0) == -1
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.get_last_alighting_index(5) == -1
        assert al.get_last_alighting_index(15) == 0
        assert al.get_last_alighting_index(20) == 0
        
    def test_get_last_alighting_single(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting(0) == None
        
        al.add_alighting( "morning", 15, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "morning", 15, 0 )
        assert al.get_last_alighting(20) == ( "morning", 15, 0 )

    def test_get_last_alighting_several(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24, ['WKDY','SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight("WKDY", sc, tz, 0)
        
        assert al.get_last_alighting(0) == None
        
        al.add_alighting( "1", 15, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "1", 15, 0 )
        assert al.get_last_alighting(20) == ( "1", 15, 0 )
        
        al.add_alighting( "2", 25, 0 )
        
        assert al.get_last_alighting(5) == None
        assert al.get_last_alighting(15) == ( "1", 15, 0 )
        assert al.get_last_alighting(20) == ( "1", 15, 0 )
        assert al.get_last_alighting(25) == ( "2", 25, 0 )
        assert al.get_last_alighting(30) == ( "2", 25, 0 )
    

    def test_walk_back(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "1", 50, 0 )
        al.add_alighting( "2", 100, 0 )
        al.add_alighting( "3", 200, 0 )
        
        #wrong day
        s = State(1, 1*3600*24)
        ret = al.walk_back( s,WalkOptions() )
        assert ret == None
        
        s = State(1, 250)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 51
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 248)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 49
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 200)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 200
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 100)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 100
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 50)
        ret = al.walk_back(s,WalkOptions())
        assert ret.time == 50
        assert ret.weight == 1
        assert ret.num_transfers == 1
        assert ret.dist_walked == 0.0
        
        s = State(1, 49)
        ret = al.walk_back(s,WalkOptions())
        assert ret == None
        
    def test_walk(self):
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        al = TripAlight( "WKDY", sc, tz, 0 )
        al.add_alighting( "1", 50, 0 )
        al.add_alighting( "2", 100, 0 )
        al.add_alighting( "3", 200, 0 )
        
        s = State(1,100)
        ret = al.walk( s, WalkOptions() )
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
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        # one alighting - one second before midnight
        al.add_alighting( "1", 86400-1, 0 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # it should be one second after the last alighting 
        s1 = al.walk_back( s0, WalkOptions() )
        self.assertEquals( s1.time, 86399 )
        
    def test_check_today(self):
        
        # the service calendar has two weekdays, back to back
        sc = ServiceCalendar()
        sc.add_period( 0, 3600*24, ["WKDY"] )
        sc.add_period( 3600*24, 2*3600*24, ["WKDY"] )
        
        # the timezone lasts for two days and has no offset
        # this is just boilerplate
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 2*3600*24, 0) )
        
        # tripboard runs on weekdays for agency 0
        al = TripAlight( "WKDY", sc, tz, 0 )
        
        # one boarding - noon
        al.add_alighting( "1", 43200, 1 )
        
        # our starting state is midnight between the two days
        s0 = State(1, 86400)
        
        # this should put us in noon the previous day
        s1 = al.walk_back( s0, WalkOptions() )
        
        self.assertEquals( s1.time, 43200 )
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestTripAlight)
    unittest.TextTestRunner(verbosity=2).run(suite)
