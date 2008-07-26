
import sys
sys.path.append('..')
from graphserver.core import Graph, Street, CalendarDay, TripHopSchedule, Calendar, State
from graphserver.ext.gtfs import GTFSLoadable
import time
from calendar import timegm

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

class TestGTFS(Graph, GTFSLoadable):
    pass

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

def test_gtfs():
    g = TestGTFS()
    g.load_gtfs("./gtfs")

    v = g.get_vertex("gtfs24TH")

    def check(answers, t0):
        for ths, answer in zip(v.outgoing, answers):
            triphop = ths.payload.collapse( State(1, t0) )
            
            if answer is None:
                assert triphop is None
            else:
                assert str(triphop.trip_id) == str(answer)

    t1answers = (None, None, '01DCM2', '01DC1', None, '01DCM1', '01SFO1', None, None, None, '01PB1', '01ED1', '01F2', None, None, '01R2', None, None, None, None)
    check(t1answers, t1)
        
    t2answers = (None, None, '75DCM2', None, None, None, '90SFO1', None, None, None, '92PB1', '76ED1', None, None, None, None, None, None, None, None)
    check(t2answers, t2)

    t3answers = [None, None, '01DCM2', '01DC1', None, '01DCM1', '01SFO1', None, None, None, '01PB1', '01ED1', '01F2', None, None, '01R2', None, None, None, None]
    check(t3answers, t3)

    t4answers = ['01DCM2SAT', '01PB1SAT', None, None, '01R2SAT', None, None, None, None, '01ED1SAT', None, None, None, None, '01SFO1SAT', None, '01F2SAT', '01DC1SAT', '01DCM1SAT', None]
    check(t4answers, t4)

    t5answers = ['56DCM2SAT', '56PB1SAT', None, None, None, None, None, None, None, '58ED1SAT', None, None, None, None, '55SFO1SAT', None, None, None, None, None]
    check(t5answers, t5)

    t6answers = [None, None, None, None, None, None, None, '02PB1SUN', '01ED1SUN', None, None, None, None, '01DCM2SUN', None, None, None, None, None, '01SFO1SUN']
    check(t6answers, t6)

    t7answers = [None, None, None, None, None, None, None, '02PB1SUN', '01ED1SUN', None, None, None, None, '01DCM2SUN', None, None, None, None, None, '01SFO1SUN']
    check(t7answers, t7)

    t8answers = [None, None, None, None, None, None, None, '62PB1SUN', '62ED1SUN', None, None, None, None, '60DCM2SUN', None, None, None, None, None, '59SFO1SUN']
    check(t8answers, t8)

    t9answers = [None, None, '01DCM2', '01DC1', None, '01DCM1', '01SFO1', None, None, None, '01PB1', '01ED1', '01F2', None, None, '01R2', None, None, None, None]
    check(t9answers, t9)

    t10answers = [None, None, '01DCM2', '01DC1', None, '01DCM1', '01SFO1', None, None, None, '01PB1', '01ED1', '01F2', None, None, '01R2', None, None, None, None]
    check(t10answers, t10)

    t11answers = [None, None, '75DCM2', None, None, None, '90SFO1', None, None, None, '92PB1', '76ED1', None, None, None, None, None, None, None, None]
    check(t11answers, t11)

    t12answers = [None, None, '01DCM2', '01DC1', None, '01DCM1', '01SFO1', None, None, None, '01PB1', '01ED1', '01F2', None, None, '01R2', None, None, None, None]
    check(t12answers, t12)



    spt = g.shortest_path_tree( "gtfsOAK", "gtfs12TH", State(1,t2) )
    assert spt.path("gtfs12TH") == (None, None)

    spt = g.shortest_path_tree( "gtfsOAK", "gtfsbogus", State(1,t2) )

    print spt

    for v in spt.vertices:
        print v
        curr = v
        while curr.label != "gtfsOAK":
            print "\t%s @ %s"%(str(curr), str(curr.payload))
            curr = curr.incoming[0].from_v

    for e in v.outgoing:
        print e.to_v.label + " " + str(e.payload.collapse( State(1,t11) ))
        
        for triphop in e.payload.triphops:
            print triphop
    print "--==--"

