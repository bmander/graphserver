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
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<street name='mystreet' length='1.100000' />"

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