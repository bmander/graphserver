USAGE = %<
 USAGE:
 Start the server
 $ ruby gserver.rb --port=PORT

 Then test the XML API from a web browser:
 http://path.to.server:port/                               (blank, returns API documentation)
 .../all_vertex_labels
 .../outgoing_edges?label=Seattle                             (currently segfaults. eep!)
 .../eval_edges?label=Seattle                                 (evaluates outgoing edges at current time)
 .../eval_edges?label=Seattle-busstop&time=0                  (evaluates edges at given unix time)
 .../shortest_path?from=Seattle&to=Portland                   (finds shortest route for current. this example broken due to int range issues)
 .../shortest_path?from=Seattle&to=Portland&time=0            (finds short for given unix time)
 .../shortest_path?from=Seattle&to=Portland&time=0&debug=true (finds short for given unix time, with verbose output)
>

$: << "../.."
require 'graphserver.rb'

class ExampleServer < Graphserver

  def load_scheduled_data

    #====Create a Calendar Object====
    calendar = Calendar.new
    
    day_begin = 0               #In unix time - Midnight UTC, January 1st 1970
    day_end = 86400             #Also unix time - Midnight UTC, January 2nd 1970
    service_ids = [0]           #One bus service type runs this day, called "0"
    daylight_savings_offset = 0 #The daylight savings time offset for this day is 0 seconds
    calendar.append_day( day_begin, day_end, service_ids, daylight_savings_offset )

    #====Create a schedule array====
    #A schedule is an array of three-element arrays in the form [depart, arrive, trip_id].
    #The "depart" and "arrive" elements are expressed in seconds-since-midnight in the service day in question.
    #It is possible for depart and arrive to both be larger than 86400 (24 hours)

    sched = []
    sched << [10, 20, "A"]  #departs at 10 seconds, arrives 10 seconds later, called "A"
    sched << [15, 30, "B"]
    sched << [400, 430, "C"]

    #====Create TripHopSchedule object====
    #A TripHopSchedule represents the unevaluated weight of an edge containing schedule information

    service_id = 0   #The service type for this day is "0". Service_ids are integers, but stand in for "weekday" or "saturday" etc.
    tz_offset = 0    #The timezone offset in seconds. US West coast is -28800 (-8 hours) for instance.
    ths = TripHopSchedule.new( service_id, sched, calendar, tz_offset, 0 )

    # add the pertinent vertices to the ExampleServer's member variable Graph object:

    @gg.add_vertex( "Seattle-busstop" )
    @gg.add_vertex( "Portland-busstop" )

    # now connect the vertices with an edge

    @gg.add_edge( "Seattle-busstop", "Portland-busstop", ths )

  end

  def load_street_data

    #Street-style data is simpler
    
    @gg.add_vertex( "Seattle" )
    @gg.add_vertex( "Portland" )

    # street edges are one-way by default, and given length in feet

    @gg.add_edge( "Seattle", "Portland", Street.new( "I-5", 240000 ) )
    @gg.add_edge( "Portland", "Seattle", Street.new( "I-5", 250000 ) ) #say the return trip is longer, for some reason

  end

  def load_links

    #You can link two vertices together as if they're in the same place

    #They're one-way
    
    @gg.add_edge( "Seattle", "Seattle-busstop", Link.new )
    @gg.add_edge( "Seattle-busstop", "Seattle", Link.new )

    @gg.add_edge( "Portland", "Portland-busstop", Link.new )
    @gg.add_edge( "Portland-busstop", "Portland", Link.new )

  end

  def initialize
    super
    load_scheduled_data
    load_street_data
    load_links
  end

  def start
    print USAGE
    super
  end
end

gs = ExampleServer.new
gs.start
