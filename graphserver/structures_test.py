from structures import *

tracecount = {}

def trace():
    import sys
    return 
    caller = inspect.stack()[1][3]
    if caller not in tracecount:
        tracecount[caller] = -1
    tracecount[caller] = tracecount[caller] + 1
    print sys.stderr, "--TRACE-- %s, step %s" % (caller, tracecount[caller])

class TestGraph:
    def test_basic(self):
        g = Graph()
        assert g
        
    def test_add_vertex(self):
        g = Graph()
        v = g.add_vertex("home")
        assert v.label == "home"
        
    def test_get_vertex(self):
        g = Graph()
        g.add_vertex("home")
        v = g.get_vertex("home")
        assert v.label == "home"
        v = g.get_vertex("bogus")
        assert v == None
    def test_add_edge(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        assert e
        assert e.from_v.label == "home"
        assert e.to_v.label == "work"
        assert str(e)=="<Edge><Vertex degree_out='1' degree_in='0' label='home'/><Vertex degree_out='0' degree_in='1' label='work'/></Edge>"
    
    def test_add_edge_effects_vertices(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert fromv.degree_out==1
        assert tov.degree_in==1
    
    def test_vertices(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        
        assert g.vertices
        assert len(g.vertices)==2
        assert g.vertices[0].label == 'home'
    
    def test_shortest_path_tree(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree("home", "work", State(0))
        assert spt
        assert spt.__class__ == Graph
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
    def test_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 135698 ) #one less causes no problems
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(0))
        
        assert spt
        
    def test_shortest_path_tree_retro(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        g.add_edge("work", "home", Street("backwards",1) )
        
        spt = g.shortest_path_tree_retro("home", "work", State(0))
        assert spt
        assert spt.__class__ == Graph
        assert spt.get_vertex("home").degree_out==0
        assert spt.get_vertex("home").degree_in==1
        assert spt.get_vertex("work").degree_in==0
        assert spt.get_vertex("work").degree_out==1
    
    def test_shortest_path(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State())
        
        assert sp
        
    def xtest_shortest_path_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sp = g.shortest_path("home", "work", State())
        
        assert sp
        
    def test_add_link(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        
        assert e.payload
        assert e.payload.__class__ == Street
        
        x = g.add_edge("work", "home", Link())
        assert x.payload
        assert x.payload.name == "LINK"
        
    def xtestx_hello_world(self):
        g = Graph()
        
        def load_scheduled_data(gg):

            #====Create a Calendar Object====
            # Why no params?
            # calendar = CalendarDay()
    
            day_begin = 0               #In unix time - Midnight UTC, January 1st 1970
            day_end = 86400             #Also unix time - Midnight UTC, January 2nd 1970
            service_ids = [0]           #One bus service type runs this day, called "0"
            daylight_savings_offset = 0 #The daylight savings time offset for this day is 0 seconds
            calendar = CalendarDay(day_begin, day_end, service_ids, daylight_savings_offset)
            # Why append?
            #calendar.append_day( day_begin, day_end, service_ids, daylight_savings_offset )

            #====Create a schedule array====
            #A schedule is an array of three-element arrays in the form [depart, arrive, trip_id].
            #The "depart" and "arrive" elements are expressed in seconds-since-midnight in the service day in question.
            #It is possible for depart and arrive to both be larger than 86400 (24 hours)

            sched = [(10, 20, "A"),  #departs at 10 seconds, arrives 10 seconds later, called "A"
                     (15, 30, "B"),
                     (400, 430, "C")]

            #====Create TripHopSchedule object====
            #A TripHopSchedule represents the unevaluated weight of an edge containing schedule information

            service_id = 0   #The service type for this day is "0". Service_ids are integers, but stand in for "weekday" or "saturday" etc.
            tz_offset = 0    #The timezone offset in seconds. US West coast is -28800 (-8 hours) for instance.
            ths = TripHopSchedule( sched, service_id, calendar, tz_offset )

            # add the pertinent vertices to the ExampleServer's member variable Graph object:

            gg.add_vertex( "Seattle-busstop" )
            gg.add_vertex( "Portland-busstop" )

            # now connect the vertices with an edge

            gg.add_edge( "Seattle-busstop", "Portland-busstop", ths )

        def load_street_data(gg):

            #Street-style data is simpler
            
            gg.add_vertex( "Seattle" )
            gg.add_vertex( "Portland" )

            # street edges are one-way by default, and given length in feet

            gg.add_edge( "Seattle", "Portland", Street( "I-5", 240000 ) )
            gg.add_edge( "Portland", "Seattle", Street( "I-5", 250000 ) ) #say the return trip is longer, for some reason

  

        def load_links(gg):

            #You can link two vertices together as if they're in the same place

            #They're one-way
            
            gg.add_edge( "Seattle", "Seattle-busstop", Link() )
            gg.add_edge( "Seattle-busstop", "Seattle", Link() )

            gg.add_edge( "Portland", "Portland-busstop", Link() )
            gg.add_edge( "Portland-busstop", "Portland", Street( "a-street-payload", 1.11) )


        #load_scheduled_data(g)
        load_street_data(g)
        #load_links(g)
        
        path = g.shortest_path( "Seattle", "Portland", State() )
        
        for edge in g.edges:
            print edge
        assert False
        

class TestTriphopSchedule:
    def triphop_schedule_test(self):
        
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        
        # using a tuple
        ths = TripHopSchedule(rawhops, 1, CalendarDay(0, 1*3600*24, [1,2], 0), 0)
        
        h1 = ths.triphops[0]
        assert h1.depart == 0
        assert h1.arrive == 1*3600
        assert h1.trip_id == "Foo to Bar"
        h2 = ths.triphops[1]
        assert h2.depart == 1*3600
        assert h2.arrive == 2*3600
        assert h2.trip_id == "Bar to Cow"
                               
        assert(ths.triphops[0].trip_id == 'Foo to Bar')
        assert(len(ths.triphops) == 2)
        assert str(ths)=="<triphopschedule service_id='1'><triphop depart='00:00' arrive='01:00' transit='3600' trip_id='Foo to Bar' /><triphop depart='01:00' arrive='02:00' transit='3600' trip_id='Bar to Cow' /></triphopschedule>"

class TestStreet:
    def street_test(self):
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<street name='mystreet' length='1.100000' />"
        
    def street_test_big_length(self):
        s = Street("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<street name='longstreet' length='240000.000000' />"

class TestState:
    def test_basic(self):
        s = State(0)
        assert s.time == 0
        assert s.weight == 0
        assert s.dist_walked == 0
        assert s.num_transfers == 0
        assert s.prev_edge_name == None
        assert s.prev_edge_type == 5
        assert s.calendar_day == None

class TestLink:
    def link_test(self):
        l = Link()
        assert l
        assert str(l)=="<link name='LINK'/>"
        
    def name_test(self):
        l = Link()
        assert l.name == "LINK"

class TestListNode:
    def list_node_test(self):
        l = ListNode()

class TestVertex:
    def test_basic(self):
        v=Vertex("home")
        assert v
        
    def test_label(self):
        v=Vertex("home")
        print v.label
        assert v.label == "home"
    
    def test_incoming(self):
        v=Vertex("home")
        print v.degree_in
        assert v.degree_in == 0
        
    def test_outgoing(self):
        v=Vertex("home")
        print v.degree_out
        assert v.degree_out == 0
        
    def test_prettyprint(self):
        v = Vertex("home")
        assert v.to_xml() == "<Vertex degree_out='0' degree_in='0' label='home'/>"

class TestCalendar:
    def calendar_test(self):
        c = CalendarDay(0, 1*3600*24, [1,2], 0)
        assert(c.begin_time == 0)
        assert(c.end_time == 1*3600*24)
        assert(len(c.service_ids) == 2)
        assert(c.service_ids == [1,2])
        print c
        print c.append_day(c.end_time, c.end_time+1*3600*24, [3,4,5], 0)
        assert(c.next.service_ids == [3,4,5])
        print c.next
        assert(c.previous == None)
        assert(c.next.previous.soul == c.soul)
        assert(c.fast_forward().soul == c.next.soul)
        assert(c.next.rewind().soul == c.soul)
        
        return c
        
if __name__=='__main__':
    import nose
    nose.main()