from structures import *

tracecount = {}

def trace():
    import sys
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
        assert str(e)=="<Edge><Street name='helloworld' length='1.000000' /></Edge>"
    
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
        
    def test_shortst_path_tree_link(self):
        g = Graph()
        g.add_vertex("home")
        g.add_vertex("work")
        g.add_edge("home", "work", Link() )
        g.add_edge("work", "home", Link() )
        
        spt = g.shortest_path_tree("home", "work", State(0))
        assert spt
        assert spt.__class__ == Graph
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == Link
        assert spt.get_vertex("work").incoming[0].payload.__class__ == Link
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
    def test_shortst_path_tree_triphopschedule(self):
        g = Graph()
        g.add_vertex("home")
        g.add_vertex("work")
        
        cal = CalendarDay(0, 1*3600*24, [1,2], 0)
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0)
        
        g.add_edge("home", "work", ths )
        
        spt = g.shortest_path_tree("home", "work", State(0))
        assert spt
        assert spt.__class__ == Graph
        assert spt.get_vertex("home").outgoing[0].payload.__class__ == TripHop
        assert spt.get_vertex("work").incoming[0].payload.__class__ == TripHop
        assert spt.get_vertex("home").degree_out==1
        assert spt.get_vertex("home").degree_in==0
        assert spt.get_vertex("work").degree_in==1
        assert spt.get_vertex("work").degree_out==0
        
    def test_walk_longstreet(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        sprime = e.walk(State(0))
        
        print sprime
        
        assert str(sprime)=="<state time='Sun Jan  4 06:25:52 1970' weight='2147483647' dist_walked='240000.0' num_transfers='0' prev_edge_type='0' prev_edge_name='helloworld'></state>"

        
    def xtestx_shortest_path_tree_bigweight(self):
        g = Graph()
        fromv = g.add_vertex("home")
        tov = g.add_vertex("work")
        s = Street( "helloworld", 240000 )
        e = g.add_edge("home", "work", s)
        
        spt = g.shortest_path_tree("home", "work", State(0))
        
        assert spt.get_vertex("home").degree_out == 1
            
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
        
    def xtestx_shortest_path_bigweight(self):
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
    
    def test_hello_world(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        
        g.add_edge( "Seattle", "Portland", Street("I-5 south", 5000) )
        g.add_edge( "Portland", "Seattle", Street("I-5 north", 5500) )
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(0) )
        
        assert spt.get_vertex("Seattle").outgoing[0].payload.name == "I-5 south"
        
        g.add_vertex( "Portland-busstop" )
        g.add_vertex( "Seattle-busstop" )
        
        g.add_edge( "Seattle", "Seattle-busstop", Link() )
        g.add_edge( "Seattle-busstop", "Seattle", Link() )
        g.add_edge( "Portland", "Portland-busstop", Link() )
        g.add_edge( "Portland-busstop", "Portland", Link() )
        
        spt = g.shortest_path_tree( "Seattle", "Seattle-busstop", State(0) )
        assert spt.get_vertex("Seattle-busstop").incoming[0].payload.__class__ == Link
        
        spt = g.shortest_path_tree( "Seattle-busstop", "Portland", State(0) )
        assert spt.get_vertex("Portland").incoming[0].payload.__class__ == Street
        
        cal = CalendarDay(0, 86400, [1,2], 0)
        rawhops = [(10,     20,'A'),
                   (15,     30,'B'),
                   (400,   430,'C')]
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0)
        
        g.add_edge( "Seattle-busstop", "Portland-busstop", ths )
        
        spt = g.shortest_path_tree( "Seattle", "Portland", State(0) )
        
        assert spt.get_vertex( "Portland" ).incoming[0].from_v.incoming[0].from_v.incoming[0].from_v.label == "Seattle"
        
        vertices, edges = g.shortest_path( "Seattle", "Portland", State(0) )
        
        assert [v.label for v in vertices] == ['Seattle', 'Seattle-busstop', 'Portland-busstop', 'Portland']
        assert [e.payload.__class__ for e in edges] == [Link, TripHop, Link]

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

class TestStreet:
    def street_test(self):
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' />"
        
    def street_test_big_length(self):
        s = Street("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Street name='longstreet' length='240000.000000' />"
        
    def test_walk(self):
        s = Street("longstreet", 2)
        
        after = s.walk(State(0))
        assert after.time == 2
        assert after.weight == 4
        assert after.dist_walked == 2
        assert after.prev_edge_type == 0
        assert after.prev_edge_name == "longstreet"

class TestPyPayload:
    def _minimal_graph(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        return g
    
    def test_basic(self):
        p = NoOpPyPayload(1.1)
        
    def test_cast(self):
        g = self._minimal_graph()
        e = NoOpPyPayload(1.2)
        
        ed = g.add_edge( "Seattle", "Portland", e )
        #print ed.payload
        ep = ed.payload # uses EdgePayload.from_pointer internally.
        assert e == ep
        assert e == ed.payload
        assert ep.num == 1.2
    
        
    
    def test_walk(self):
        class IncTimePayload(PyPayloadBase):
            def walk(self, state):
                state.time = state.time + 1
            
            def walk_back(self, state):
                state.time = state.time - 1
        g = self._minimal_graph()
        
        ed = g.add_edge( "Seattle", "Portland", IncTimePayload())
        assert(isinstance(ed.payload,IncTimePayload))
        s = State(0)
        assert s.time == 0
        ed.walk(s)
        
        
    def xtestx_xtestx_walk(self):
        from graphserver.dll import lgs
        class Foo():
            def test_walk(self, s):
                print "Test walking %s" % s
            def __str__(self):
                print "F!!!!!"
                return "f"
            
        foo = py_object([1])
        print "foo %s" % foo
        #lgs.testWalk(foo, State(0).soul, 1)
        lgs.callStr(foo)
        assert False

    def xtest_walk(self):
        class IncTimePayload(PyPayloadInterface):
            def walk(self, state):
                state.time = state.time + 1
            
            def walk_back(self, state):
                state.time = state.time - 1
        
        e = IncTimePayload()
        p = PyPayloadWrapper(e,"incpayload")
        s = State(0)
        assert s.time == 0
        #print s
        return
        s = p.walk(s)
        #print s
        assert s.time == 1
        assert e
        """
        
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )

        e = IncTimePayload()
        p = PyPayload(e,"incpayload")
        
        ed = g.add_edge( "Seattle", "Portland", p )
        """
        
        
            

class TestLink:
    def link_test(self):
        l = Link()
        assert l
        assert str(l)=="<Link name='LINK'/>"
        
    def name_test(self):
        l = Link()
        assert l.name == "LINK"
        
    def test_walk(self):
        l = Link()
        
        after = l.walk(State(0))
        
        assert after.time==0
        assert after.weight==0
        assert after.dist_walked==0
        assert after.prev_edge_type==3
        assert after.prev_edge_name=="LINK"
        
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
        assert str(ths)=="<TripHopSchedule service_id='1'><TripHop depart='00:00' arrive='01:00' transit='3600' trip_id='Foo to Bar' /><TripHop depart='01:00' arrive='02:00' transit='3600' trip_id='Bar to Cow' /></TripHopSchedule>"
        
    def test_walk(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = CalendarDay(0, 1*3600*24, [1,2], 0)
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0)
        
        s = ths.walk(State(0))
        
        assert s.time == 3600
        assert s.weight == 3600
        assert s.dist_walked == 0.0
        assert s.num_transfers == 1
        assert s.prev_edge_type == 2
        assert s.prev_edge_name == "Foo to Bar"
        assert str(s) == "<state time='Thu Jan  1 01:00:00 1970' weight='3600' dist_walked='0.0' num_transfers='1' prev_edge_type='2' prev_edge_name='Foo to Bar'><calendar begin_time='Thu Jan  1 00:00:00 1970' end_time='Fri Jan  2 00:00:00 1970' service_ids='1,2'/></state>"
        
    def test_collapse(self):
        rawhops = [(0,     1*3600,'Foo to Bar'),
                   (1*3600,2*3600,'Bar to Cow')]
        cal = CalendarDay(0, 1*3600*24, [1,2], 0)
        # using a tuple
        ths = TripHopSchedule(hops=rawhops, service_id=1, calendar=cal, timezone_offset=0)
        
        th = ths.collapse(State(0))
        
        assert th.depart == 0
        assert th.arrive == 3600
        assert th.transit == 3600
        assert th.trip_id == "Foo to Bar"

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