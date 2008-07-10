from load_gtfs import add_gtfs_to_graph
import sys
sys.path.append('../..')
from structures import Graph, Street, CalendarDay, TripHopSchedule, Calendar, State
import time
from calendar import timegm

#NON-DST DATES
#weekday
t1 = (timegm((2008,7,9,3,50,0))+8*3600) #Wed 2008-7-9 03:50:00 PST-0800, right before first train in system
t2 = (timegm((2008,7,9,23,15,0))+8*3600) #Wed 2008-7-9 11:15:00 PST-0800
t3 = (timegm((2008,7,10,2,36,0))+8*3600) #Thu 2008-7-10 2:36:00 PST-0800, right after last train in system

#saturday
t4 = (timegm((2008,7,5,3,49,0))+8*3600) #Sat 2008-7-5 03:50:00 PST-0800, right before first train in system
t5 = (timegm((2008,7,5,23,15,0))+8*3600) #Sat 2008-7-5 11:15:00 PST-0800
t6 = (timegm((2008,7,6,2,36,0))+8*3600) #Sun 2008-7-6 2:36:00 PST-0800, right after last train in system

#sunday
t7 = (timegm((2008,7,6,3,49,0))+8*3600) #Sun 2008-7-6 03:50:00 PST-0800, right before first train in system
t8 = (timegm((2008,7,6,23,15,0))+8*3600) #Sun 2008-7-6 11:15:00 PST-0800
t9 = (timegm((2008,7,7,2,36,0))+8*3600) #Mon 2008-7-7 2:36:00 PST-0800, right after last train in system

#DST DATES
#weekday
t10 = (timegm((2008,1,9,3,50,0))+7*3600) #Wed 2008-1-9 03:50:00 PST-0800, right before first train in system
t11 = (timegm((2008,1,9,23,15,0))+7*3600) #Wed 2008-1-9 11:15:00 PST-0800
t12 = (timegm((2008,1,10,2,36,0))+7*3600) #Thu 2008-1-10 2:36:00 PST-0800, right after last train in system

g = Graph()
add_gtfs_to_graph(g, "./data")

v = g.get_vertex("24TH")
assert v.outgoing[0].payload.collapse( State(t1) ).trip_id == "01PB1"
assert v.outgoing[1].payload.collapse( State(t1) ).trip_id == "01SFO1"
assert v.outgoing[2].payload.collapse( State(t1) ) == None

assert v.outgoing[0].payload.collapse( State(t2) ).trip_id == "76ED1"
assert v.outgoing[1].payload.collapse( State(t2) ).trip_id == "90SFO1"
assert v.outgoing[2].payload.collapse( State(t2) ) == None

assert v.outgoing[0].payload.collapse( State(t3) ).trip_id == "01PB1"
assert v.outgoing[1].payload.collapse( State(t3) ).trip_id == "01SFO1"
assert v.outgoing[2].payload.collapse( State(t3) ) == None

assert v.outgoing[0].payload.collapse( State(t4) ) == None
assert v.outgoing[1].payload.collapse( State(t4) ) == None
assert v.outgoing[2].payload.collapse( State(t4) ).trip_id == "01ED1SAT"
assert v.outgoing[3].payload.collapse( State(t4) ) == None
assert v.outgoing[4].payload.collapse( State(t4) ).trip_id == "01DCM2SAT"
assert v.outgoing[5].payload.collapse( State(t4) ) == None

assert v.outgoing[0].payload.collapse( State(t5) ) == None
assert v.outgoing[1].payload.collapse( State(t5) ) == None
assert v.outgoing[2].payload.collapse( State(t5) ).trip_id == "58ED1SAT"
assert v.outgoing[3].payload.collapse( State(t5) ) == None
assert v.outgoing[4].payload.collapse( State(t5) ).trip_id == "55SFO1SAT"
assert v.outgoing[5].payload.collapse( State(t5) ) == None

assert v.outgoing[0].payload.collapse( State(t6) ) == None
assert v.outgoing[1].payload.collapse( State(t6) ) == None
assert v.outgoing[2].payload.collapse( State(t6) ) == None
assert v.outgoing[3].payload.collapse( State(t6) ).trip_id == "01DCM2SUN"
assert v.outgoing[4].payload.collapse( State(t6) ) == None
assert v.outgoing[5].payload.collapse( State(t6) ).trip_id == "01ED1SUN"

assert v.outgoing[0].payload.collapse( State(t7) ) == None
assert v.outgoing[1].payload.collapse( State(t7) ) == None
assert v.outgoing[2].payload.collapse( State(t7) ) == None
assert v.outgoing[3].payload.collapse( State(t7) ).trip_id == "01DCM2SUN"
assert v.outgoing[4].payload.collapse( State(t7) ) == None
assert v.outgoing[5].payload.collapse( State(t7) ).trip_id == "01ED1SUN"

assert v.outgoing[0].payload.collapse( State(t8) ) == None
assert v.outgoing[1].payload.collapse( State(t8) ) == None
assert v.outgoing[2].payload.collapse( State(t8) ) == None
assert v.outgoing[3].payload.collapse( State(t8) ).trip_id == "59SFO1SUN"
assert v.outgoing[4].payload.collapse( State(t8) ) == None
assert v.outgoing[5].payload.collapse( State(t8) ).trip_id == "62ED1SUN"

assert v.outgoing[0].payload.collapse( State(t9) ).trip_id == "01PB1"
assert v.outgoing[1].payload.collapse( State(t9) ).trip_id == "01SFO1"
assert v.outgoing[2].payload.collapse( State(t9) ) == None

assert v.outgoing[0].payload.collapse( State(t10) ).trip_id == "01PB1"
assert v.outgoing[1].payload.collapse( State(t10) ).trip_id == "01SFO1"
assert v.outgoing[2].payload.collapse( State(t10) ) == None

assert v.outgoing[0].payload.collapse( State(t11) ).trip_id == "76ED1"
assert v.outgoing[1].payload.collapse( State(t11) ).trip_id == "90SFO1"
assert v.outgoing[2].payload.collapse( State(t11) ) == None

assert v.outgoing[0].payload.collapse( State(t12) ).trip_id == "01PB1"
assert v.outgoing[1].payload.collapse( State(t12) ).trip_id == "01SFO1"
assert v.outgoing[2].payload.collapse( State(t12) ) == None

print t2
spt = g.shortest_path_tree( "16TH", "bogus", State(t2) )

print spt

for v in spt.vertices:
    print v
    curr = v
    while curr.label != "16TH":
        print "\t%s @ %s"%(str(curr), str(curr.payload))
        curr = curr.incoming[0].from_v

"""
for e in v.outgoing:
    print e.to_v.label + " " + str(e.payload.collapse( State(t12) ))
    
    for triphop in e.payload.triphops:
        print triphop
print "--==--"
"""

"""
v = g.get_vertex("16TH")
for e in v.outgoing:
    print e.to_v.label + " " + str(e.payload.collapse( State(int(time.time()))))
print "--==--"
    
v = g.get_vertex("CIVC")
for e in v.outgoing:
    print e.to_v.label + " " + str(e.payload.collapse( State(int(time.time()))))
print "--==--"
    
v = g.get_vertex("POWL")
for e in v.outgoing:
    print e.to_v.label + " " + str(e.payload.collapse( State(int(time.time()))))
print "--==--"
"""