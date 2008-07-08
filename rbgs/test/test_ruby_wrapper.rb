require 'graphserver.rb'
require 'test/unit'

def create_ths
    #====Create a Calendar Object====
    calendar = Calendar.new
    
    day_begin = 0               #In unix time - Midnight UTC, January 1st 1970
    day_end = 86400             #Also unix time - Midnight UTC, January 2nd 1970
    service_ids = [0]           #One bus service type runs this day, called "0"
    daylight_savings_offset = 0 #The daylight savings time offset for this day is 0 seconds
    calendar.append_day( day_begin, day_end, service_ids, daylight_savings_offset )

    sched = []
    sched << [10, 20, "A"]  #departs at 10 seconds, arrives 10 seconds later, called "A"
    sched << [15, 30, "B"]
    sched << [400, 430, "C"]

    #====Create TripHopSchedule object====
    #A TripHopSchedule represents the unevaluated weight of an edge containing schedule information

    service_id = 0   #The service type for this day is "0". Service_ids are integers, but stand in for "weekday" or "saturday" etc.
    tz_offset = 0    #The timezone offset in seconds. US West coast is -28800 (-8 hours) for instance.
    ths = TripHopSchedule.new( service_id, sched, calendar, tz_offset )
    
    return ths
end


class TestGraph < Test::Unit::TestCase

  #def setup
  #end

  # def teardown
  # end

  def test_graph
    g = Graph.create
    assert_not_nil( g )
  end
 
  def test_add_vertex
    g = Graph.create
    v = g.add_vertex("home")
    assert( v.label == "home" )
  end 

  def test_double_add_vertex
    g = Graph.create
    v = g.add_vertex("double")
    assert( v.label == "double" )
    assert( g.size == 1 )
    v = g.add_vertex("double")
    assert( g.size == 1 )
    assert( v.label == "double" )
  end

  def test_get_vertex
    g = Graph.create
        
    g.add_vertex("home")
    v = g.get_vertex("home")
    assert( v.label == "home" )
    v = g.get_vertex("bogus")
    assert( v == nil )
  end
  
  def test_add_edge
    g = Graph.create
    
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    assert_not_nil( e )
    assert( e.from.label == "home" )
    assert( e.to.label == "work" )
    assert( e.payload.class == Street )
    assert( e.payload.length == 1.0 )
  end
  
  def test_add_edge_effects_vertices
    g = Graph.create
    
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    
    assert( fromv.degree_out==1 )
    assert( tov.degree_in==1 )
  end
  
  def test_vertices
    g = Graph.create
        
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    
    assert g.vertices
    assert g.vertices.length==2
    assert g.vertices[0].label == 'home'
  end
  
  def test_shortest_path_tree
    g = Graph.create
    
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    g.add_edge("work", "home", Street.new("backwards",1) )
    
    spt = g.shortest_path_tree("home", "work", State.new(0), true)
    assert spt
    assert spt.class == Graph
    assert spt.get_vertex("home").degree_out==1
    assert spt.get_vertex("home").degree_in==0
    assert spt.get_vertex("home").payload['weight']==0
    assert spt.get_vertex("work").degree_in==1
    assert spt.get_vertex("work").degree_out==0
    assert spt.get_vertex("work").payload['weight']==2
  end
  
  def test_shortest_path_tree_link
    g = Graph.create
    
    g.add_vertex("home")
    g.add_vertex("work")
    g.add_edge("home", "work", Link.new() )
    g.add_edge("work", "home", Link.new() )
    
    spt = g.shortest_path_tree("home", "work", State.new(0), true)
    assert spt
    assert spt.class == Graph
    assert spt.get_vertex("home").edge_out(0).payload.class == Link
    assert spt.get_vertex("work").edge_in(0).payload.class == Link
    assert spt.get_vertex("home").degree_out==1
    assert spt.get_vertex("home").degree_in==0
    assert spt.get_vertex("work").degree_in==1
    assert spt.get_vertex("work").degree_out==0
  end
  
  def test_shortest_path_tree_retro
    g = Graph.create
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    g.add_edge("work", "home", Street.new("backwards",1) )
    
    spt = g.shortest_path_tree("home", "work", State.new(0), false)
    assert spt
    assert spt.class == Graph
    assert spt.get_vertex("home").degree_out==0
    assert spt.get_vertex("home").degree_in==1
    assert spt.get_vertex("work").degree_in==0
    assert spt.get_vertex("work").degree_out==1
  end
  
  def test_shortest_path
    g = Graph.create
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    
    sp = g.shortest_path("home", "work", State.new(0))
    
    assert sp
  end
  
  def test_add_link
    g = Graph.create
    
    fromv = g.add_vertex("home")
    tov = g.add_vertex("work")
    s = Street.new( "helloworld", 1 )
    e = g.add_edge("home", "work", s)
    
    assert e.payload
    assert e.payload.class == Street
    
    x = g.add_edge("work", "home", Link.new())
    assert x.payload.class == Link
  end
  
  def test_hello_world
    g = Graph.create
    
    g.add_vertex( "Seattle" )
    g.add_vertex( "Portland" )
    
    g.add_edge( "Seattle", "Portland", Street.new("I-5 south", 5000) )
    g.add_edge( "Portland", "Seattle", Street.new("I-5 north", 5500) )
    
    spt = g.shortest_path_tree( "Seattle", "Portland", State.new(0), true )
    
    assert spt.get_vertex("Seattle").edge_out(0).payload.name == "I-5 south"
    
    g.add_vertex( "Portland-busstop" )
    g.add_vertex( "Seattle-busstop" )
    
    g.add_edge( "Seattle", "Seattle-busstop", Link.new() )
    g.add_edge( "Seattle-busstop", "Seattle", Link.new() )
    g.add_edge( "Portland", "Portland-busstop", Link.new() )
    g.add_edge( "Portland-busstop", "Portland", Link.new() )
    
    spt = g.shortest_path_tree( "Seattle", "Seattle-busstop", State.new(0), true )
    assert spt.get_vertex("Seattle-busstop").edge_in(0).payload.class == Link
    
    spt = g.shortest_path_tree( "Seattle-busstop", "Portland", State.new(0), true )
    assert spt.get_vertex("Portland").edge_in(0).payload.class == Street
    
    ths = create_ths()
    
    g.add_edge( "Seattle-busstop", "Portland-busstop", ths )
    
    spt = g.shortest_path_tree( "Seattle", "Portland", State.new(0), true )
    
    assert spt.get_vertex( "Portland" ).edge_in(0).from.edge_in(0).from.edge_in(0).from.label == "Seattle"
    
    vertices, edges = g.shortest_path( "Seattle", "Portland", State.new(0) )
    
    assert vertices.collect{|v| v.label} == ['Seattle', 'Seattle-busstop', 'Portland-busstop', 'Portland']
    assert edges.collect{|e| e.payload.class} == [Link, TripHop, Link]
  end

end

class TestState < Test::Unit::TestCase
  def test_basic
    s = State.new(0)
    assert s['time'] == 0
    assert s['weight'] == 0
    assert s['dist_walked'] == 0
    assert s['num_transfers'] == 0
    assert s['prev_edge_name'] == nil
    assert s['prev_edge_type'] == 5
    assert s['calendar_day'] == nil
  end
        
  def test_dup
    s = State.new(0)
    
    s2 = s.dup()
    
    assert s2['time'] == 0
    assert s2['weight'] == 0
    assert s2['dist_walked'] == 0
    assert s2['num_transfers'] == 0
    assert s2['prev_edge_name'] == nil
    assert s2['prev_edge_type'] == 5
    assert s2['calendar_day'] == nil
  end
end

class TestStreet < Test::Unit::TestCase
    def test_street
        s = Street.new("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.to_xml() == "<street name='mystreet' length='1.1' />"
    end
        
    def test_street_big_length
        s = Street.new("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<street name='longstreet' length='240000.0' />"
    end
        
    def test_walk
        s = Street.new("longstreet", 2)
        
        after = s.walk(State.new(0))
        assert after['time'] == 2
        assert after['weight'] == 4
        assert after['dist_walked'] == 2
        assert after['prev_edge_type'] == 0
        assert after['prev_edge_name'] == "longstreet"
    end
  end
  
class TestLink < Test::Unit::TestCase
    def test_link
        l = Link.new()
        assert l
        assert l.to_xml()=="<link/>"
    end
        
    def test_walk
        l = Link.new()
        
        after = l.walk(State.new(0))
        
        assert after['time']==0
        assert after['weight']==0
        assert after['dist_walked']==0
        assert after['prev_edge_type']==3
        assert after['prev_edge_name']=="LINK"
    end
  end
  
class TestTriphopSchedule < Test::Unit::TestCase
    def test_triphop_schedule
        
        ths = create_ths()
        
        h1 = ths.triphops[0]
        assert_equal( h1.depart, 10 )
        assert_equal( h1.arrive , 20 )
        assert_equal( h1.trip_id , "A")
        h2 = ths.triphops[1]
        assert_equal( h1.depart, 10 )
        assert_equal( h2.arrive, 30 )
        assert_equal( h2.trip_id, "B")
                               
        assert_equal(ths.triphops.length , 3)
        assert_equal(ths.to_xml(), "<triphopschedule service_id='0'><triphop depart='00:00:10' arrive='00:00:20' transit='10' trip_id='A' /><triphop depart='00:00:15' arrive='00:00:30' transit='15' trip_id='B' /><triphop depart='00:06:40' arrive='00:07:10' transit='30' trip_id='C' /></triphopschedule>" )
    end
        
    def test_walk
        ths = create_ths()
        
        s = ths.walk(State.new(0))
        
        assert_equal( 20, s['time'] )
        assert_equal( 20, s['weight'] )
        assert_equal( s['dist_walked'] , 0.0 )
        assert_equal( s['num_transfers'] , 1 )
        assert_equal( s['prev_edge_type'] , 2 )
        assert_equal( s['prev_edge_name'] , "A" )
        assert_equal( s.to_xml() ,  "<state weight='20' time='Wed Dec 31 16:00:20 -0800 1969' prev_edge_name='A' dist_walked='0.0' num_transfers='1' prev_edge_type='2' ><calendar begin_time='Wed Dec 31 16:00:00 -0800 1969' end_time='Thu Jan 01 16:00:00 -0800 1970' service_ids='0' /></state>" )
    end
    
    def test_collapse
        ths = create_ths()
        
        th = ths.collapse(State.new(0))
        
        assert_equal( 10, th.depart )
        assert_equal( 20, th.arrive )
        assert_equal( 10, th.transit )
        assert_equal( "A", th.trip_id )
    end
  end
  
class TestVertex < Test::Unit::TestCase
    def test_basic
        v=Vertex.new("home")
        assert v
    end
        
    def test_label
        v=Vertex.new("home")
        print v.label
        assert v.label == "home"
    end
    
    def test_incoming
        v=Vertex.new("home")
        print v.degree_in
        assert v.degree_in == 0
    end
        
    def test_outgoing
        v=Vertex.new("home")
        print v.degree_out
        assert v.degree_out == 0
    end
        
    def test_prettyprint
        v = Vertex.new("home")
        assert v.to_xml() == "<vertex label='home'></vertex>"
    end
end