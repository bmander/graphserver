from structures import *

class TestGraph:
    def test_basic(self):
        g = Graph()
        assert g
    
    def graph_xtestx(self):
        g = Graph()
        g.add_vertex("home")
        g.add_vertex("work")
        s = Street( "helloworld", 1 )
        e = g.add_edge("home", "work", s)
        assert(g.get_vertex("home").label == 'home')
        assert(g.get_vertex("work").label == 'work')
        assert(s.name == "helloworld")
        assert(s.length == 1)
        assert(isinstance(e.payload, Street))
        assert(e.payload.name == "helloworld")
        assert(e.from_v.label == "home")
        assert(str(e) == 
               """<Edge><Vertex degree_out='1' degree_in='0' label='home'/>"""
               """<Vertex degree_out='0' degree_in='1' label='work'/></Edge>""")
        assert(e.to_v.label == "work")
        assert(len(g.vertices) == 2)
        assert(g.vertices[0].label == 'home')
        
        print g.shortest_path("home", "work", State())
        
        
        #l = Link()
        x = g.add_edge("work", "home", Link())
        assert(x.payload.name == "LINK")
        print x.payload
        
        
        print "Okay... dumping the vertices"
        for v in g.vertices:
            print v    
        
        assert(g)


class TestTriphopSchedule:
    def triphop_schedule_test(self):
        hops = [TripHop(1, 0, 1*3600, 1, "Foo to Bar", schedule=None), 
                               TripHop(1, 1*3600, 2*3600, 1, "Bar to Cow", schedule=None)]
        
        # using hop objects
        ths = TripHopSchedule(hops, 1, CalendarDay(0, 1*3600*24, [1,2], 0), 0)
        assert(len(ths.triphops) == 2)
        assert(ths.triphops[0].trip_id == 'Foo to Bar')
        # using a tuple
        ths = TripHopSchedule([(0,1*3600,'Foo to Bar'),
                               (1*3600,2*3600,'Bar to Cow')], 1, CalendarDay(0, 1*3600*24, [1,2], 0), 0)
        assert(ths.triphops[0].trip_id == 'Foo to Bar')
        assert(len(ths.triphops) == 2)
        print ths

class TestTriphop:
    def triphop_test(self):
        th = TripHop(1, 0, 1*3600, 1, "Foo to Bar", schedule=None)
        print th

class TestStreet:
    def street_test(self):
        x = lgs.streetNew(c_char_p("foo"), c_double(1.2)).contents
        print "API %s" % x
        x = Street("mystreet", 1.1)
        print "%s" % x

class TestListNode:
    def list_node_test(self):
        l = ListNode()
        
class TestEdge:
    def edge_test(self):
        ep = EdgePayload()
        e = Edge(Vertex("home"),Vertex("work"), ep)
        print e

class TestVertex:
    def vertex_test(self):
        v = Vertex("home")
        v.payload_ptr = pointer(EdgePayload(1))
        assert(v.label == "home")
        assert(len(v.incoming) == 0)
        assert(len(v.outgoing) == 0)
        print v

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
        assert(addressof(c.next.previous)== addressof(c))
        assert(addressof(c.fast_forward())== addressof(c.next))
        assert(addressof(c.next.rewind())== addressof(c))
        
        return c