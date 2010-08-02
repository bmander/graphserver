import transitfeed
import sys, os, subprocess
sys.path = ['..'] + sys.path
from graphserver.core import Graph, Street, ServicePeriod, ServiceCalendar, State, Wait, WalkOptions
import graphserver.ext.gtfs
import time
from calendar import timegm
from datetime import datetime
import pytz

RESOURCE_DIR=os.path.dirname(os.path.abspath(__file__))

def find_resource(s):
    return os.path.join(RESOURCE_DIR, s)

#NON-DST DATES
#weekday
t1 = (timegm((2008,7,9,3,50,0))+7*3600) #1215600600; Wed 2008-7-9 03:50:00 PDT-0700, right before first train in system
t2 = (timegm((2008,7,9,23,15,0))+7*3600) #1215670500; Wed 2008-7-9 11:15:00pm PDT-0700
t3 = (timegm((2008,7,10,2,36,0))+7*3600) #Thu 2008-7-10 2:36:00 PDT-0800, right after last train in system

#saturday
t4 = (timegm((2008,7,5,3,49,0))+7*3600) #Sat 2008-7-5 03:50:00 PDT-0700, right before first train in system
t5 = (timegm((2008,7,5,23,15,0))+7*3600) #Sat 2008-7-5 11:15:00 PDT-0700
t6 = (timegm((2008,7,6,2,36,0))+7*3600) #Sun 2008-7-6 2:36:00 PDT-0700, right after last train in system

#sunday
t7 = (timegm((2008,7,6,3,49,0))+7*3600) #Sun 2008-7-6 03:50:00 PDT-0700, right before first train in system
t8 = (timegm((2008,7,6,23,15,0))+7*3600) #Sun 2008-7-6 11:15:00 PDT-0700
t9 = (timegm((2008,7,7,2,36,0))+7*3600) #Mon 2008-7-7 2:36:00 PDT-0700, right after last train in system

#DST DATES
#weekday
t10 = (timegm((2008,1,9,3,50,0))+8*3600) #Wed 2008-1-9 03:50:00 PST-0800, right before first train in system
t11 = (timegm((2008,1,9,23,15,0))+8*3600) #Wed 2008-1-9 11:15:00 PST-0800
t12 = (timegm((2008,1,10,2,36,0))+8*3600) #Thu 2008-1-10 2:36:00 PST-0800, right after last train in system

def get_answers(vertex, time):
    """Returns the trip_ids for every outgoing triphopschedule from this vertex at this time. This is the functioon
       used to generate the "answers" lists in the test below"""
    
    answersout = []
    for i in vertex.outgoing:
        th = i.payload.collapse( State(1, time) )
        if th is None:
            answersout.append( None )
        else:
            answersout.append( th.trip_id )
    answersout

import unittest
class GTFSTestCase(unittest.TestCase):
    
    def test_load_sample(self):
        g = TestGTFS()
        wo = WalkOptions()
        g.load_gtfs( find_resource("sample-feed.zip"))
        
        def leads_to(x, y):
            vs = [ edge.to_v.label for edge in g.get_vertex(x).outgoing ]
            assert vs == list(y), "%s vs %s" % (vs, list(y))
        
        # check that the graph is layed out like we'd expect
        leads_to( "gtfsEMSI", ('gtfsDADAN',) )
        leads_to( "gtfsBEATTY_AIRPORT", ('gtfsAMV', 'gtfsBULLFROG') )
        leads_to( "gtfsNADAV", ('gtfsDADAN', 'gtfsNANAA') )
        leads_to( 'gtfsBULLFROG', ('gtfsBEATTY_AIRPORT', 'gtfsFUR_CREEK_RES') )
        leads_to( 'gtfsAMV', ('gtfsBEATTY_AIRPORT',) )
        leads_to( 'gtfsNANAA', ('gtfsNADAV', 'gtfsSTAGECOACH' ) )
        leads_to( 'gtfsDADAN', ('gtfsNADAV', 'gtfsEMSI' ) )
        leads_to( 'gtfsSTAGECOACH', ('gtfsBEATTY_AIRPORT', 'gtfsNANAA') )
        leads_to( 'gtfsFUR_CREEK_RES', ('gtfsBULLFROG',) )
        
        s = State(1,1219842000) #6 am august 27, 2008, America/Los_Angeles
        
        # walk one edge
        edge_to_airport = g.get_vertex("gtfsSTAGECOACH").outgoing[0]
        sprime = edge_to_airport.walk(s, wo)
        assert sprime.time == 1219843200
        assert sprime.weight == 1200
        
        # find a sample route
        spt = g.shortest_path_tree( "gtfsSTAGECOACH", None, s )
        vertices, edges = spt.path("gtfsBULLFROG")
        assert spt.get_vertex("gtfsBULLFROG").payload.time == 1219849800 #8:10 am wed august 27, 2008, America/Los_Angeles
        assert [v.label for v in vertices] == ['gtfsSTAGECOACH', 'gtfsBEATTY_AIRPORT', 'gtfsBULLFROG']
            
        s = State(1,1202911200) #6am feb 13, 2008, America/Los_Angeles
        edge_to_airport = g.get_vertex("gtfsSTAGECOACH").outgoing[0]
        sprime = edge_to_airport.walk(s, wo)
        assert sprime.time == 1202912400
        assert sprime.weight == 1200
        
        spt = g.shortest_path_tree( "gtfsSTAGECOACH", None, s )
        vertices, edges = spt.path("gtfsBULLFROG")
        assert spt.get_vertex("gtfsBULLFROG").payload.time == 1202919000 #8:10 am feb 13, 2008, America/Los_Angeles
        assert [v.label for v in vertices] == ['gtfsSTAGECOACH', 'gtfsBEATTY_AIRPORT', 'gtfsBULLFROG']
        
        
    def test_parse_date(self):
        assert graphserver.ext.gtfs.load_gtfs.parse_date("20080827") == (2008,8,27)
        
    def test_get_service_ids(self):
        sched = transitfeed.Loader(find_resource("google_transit.zip")).Load()
        
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, "20080827") == [u'M-FSAT', u'WKDY']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, "20080906" ) == [u'M-FSAT', u'SAT']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, "20080907" ) == [u'SUN', u'SUNAB']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, "20081225" ) == [u'SUN', u'SUNAB']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, datetime(2008,8,27)) == [u'M-FSAT', u'WKDY']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, datetime(2008,9,6)) == [u'M-FSAT', u'SAT']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, datetime(2008,9,7)) == [u'SUN', u'SUNAB']
        assert graphserver.ext.gtfs.load_gtfs.get_service_ids(sched, datetime(2008,12,25)) == [u'SUN', u'SUNAB']
        
    def test_timezone_from_agency(self):
        sched = transitfeed.Loader(find_resource("google_transit.zip")).Load()
        
        assert graphserver.ext.gtfs.load_gtfs.timezone_from_agency(sched, "BART") == pytz.timezone("America/Los_Angeles")
        assert graphserver.ext.gtfs.load_gtfs.timezone_from_agency(sched, "AirBART") == pytz.timezone("America/Los_Angeles")
    
    def test_day_bounds_from_sched(self):
        sched = transitfeed.Loader(find_resource("google_transit.zip")).Load()
        
        assert graphserver.ext.gtfs.load_gtfs.day_bounds_from_sched(sched) == (13860, 92100)
        
    def test_schedule_to_service_calendar(self):
        sched = transitfeed.Loader(find_resource("google_transit.zip")).Load()
        
        sc = graphserver.ext.gtfs.load_gtfs.schedule_to_service_calendar(sched, "BART")
        
        sp = sc.period_of_or_after( 1219863600 )#noon august 27 2008, America/Los_Angeles
        assert sp.service_ids == [0,1]
        assert sp.begin_time == 1219834260
        assert sp.end_time == 1219912500
        
        sp = sc.period_of_or_after( 1220727600 ) #noon september 6 2008, America/Los_Angeles
        assert sp.service_ids == [0, 2]
        
        sp = sc.period_of_or_after( 1220814000 )
        assert sp.service_ids == [3, 4]
        
class TestBART(unittest.TestCase):
    def test_bart(self):
        wo = WalkOptions()
        g = TestGTFS()
        g.load_gtfs(find_resource("google_transit.zip"))
        
        # just a basic sanity test
        s1 = State(g.numagencies, 1219863720)
        s2 = g.get_vertex("gtfsMONT").outgoing[1].walk(s1, wo)
        assert s2.time == 1219864320
        
        #e = Engine(g)
        #e.run_test_server()
        
class TestBART_DAG(unittest.TestCase):
    def test_bart_dag(self):
        g = TestGTFS()
        g.load_gtfs_dag(find_resource("google_transit.zip"), "America/Los_Angeles")
        
        #e = Engine(g)
        #e.run_test_server()
        
        #this works
        s1 = State(2, 1219863240)
        # http://localhost:8080/shortest_path?from_v=%2219TH@42840%22&to_v=%22ASBY@43200%22&time=1219863240
        spt = g.shortest_path_tree( "19TH@42840", None, s1 )
        assert spt.get_vertex("ASBY@43200").payload.time == 1219863600
        # http://localhost:8080/shortest_path?from_v=%22gtfs19TH%22&to_v=%22gtfsASBY%22&time=1219863240
        spt = g.shortest_path_tree( "19TH", None, s1 )
        assert spt.get_vertex("ASBY").payload.time == 1219863600
        # http://localhost:8080/shortest_path?from_v=%22gtfsFRMT%22&to_v=%22gtfsMLBR%22&time=1219863240
        assert spt.get_vertex("MLBR").payload.time == 1219866720

if __name__=='__main__':
    tl = unittest.TestLoader()
    
    testables = [\
                 GTFSTestCase,
                 TestBART,
                 TestBART_DAG
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)
