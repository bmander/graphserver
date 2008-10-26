"""Converts GTFS into a simple format, easy for parsing in a sample C program. Such a program could then be used to memory profile libgraphserver's triphopschedule components."""

try:
    from core import TripHopSchedule, ServiceCalendar, Street, State, Graph
    from ext.gtfs import GTFSLoadable
except ImportError:
    import sys
    sys.path.append("../..")
    from graphserver.core import TripHopSchedule, ServiceCalendar, Street, State, Graph
    from graphserver.ext.gtfs import GTFSLoadable

import transitfeed

class SimplifyGTFS(Graph, GTFSLoadable):
    pass

g = SimplifyGTFS()

#sched = transitfeed.Loader("./data").Load()
g.load_gtfs("./data")

fp = open("transit.txt", "w")

#print out calendar
cal = g.vertices[0].outgoing[0].payload.calendar #all edges come with the same one
calday = cal
caldays = []
while calday is not None:
    caldays.append( calday )
    calday = calday.next

fp.write( "%d\n"%len(caldays) )
#print len(caldays)

for calday in caldays:
    fp.write( "%d %d %d %d\n"%(calday.begin_time, calday.end_time, len(calday.service_ids), calday.daylight_savings) )
    #print calday.begin_time, calday.end_time, len(calday.service_ids)
    for sid in calday.service_ids:
        fp.write( "%d\n"%sid );
        #print sid

fp.write( "%d\n"%g.size )
#print g.size

for v in g.vertices:
    fp.write( "%s\n"%v.label )
    #print v.label

for v in g.vertices:
    fp.write( "%s %d\n"%(v.label, len(v.outgoing)) )
    #print v.label, len(v.outgoing)
    for e in v.outgoing:
        fp.write( "%s %d %d %d\n"%(e.to_v.label, e.payload.service_id, e.payload.timezone_offset, len(e.payload.triphops)) )
        #print e.to_v.label, e.payload.service_id, len(e.payload.triphops)
        for triphop in e.payload.triphops:
            fp.write( "%d %d %s\n"%(triphop.depart, triphop.arrive, triphop.trip_id) )
            #print triphop.depart, triphop.arrive, triphop.trip_id

fp.close()