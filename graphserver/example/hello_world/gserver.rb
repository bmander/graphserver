require 'graphserver.rb'

require '../extension/load_tiger_line.rb'

class ExampleServer < Graphserver

  def load_scheduled_data

    #make database or file calls to get your scheduled data

    # format it into a "schedule" object.
    # A schedule is a short array that looks like this: [depart, arrive, trip_id, daymask]
    # depart and arrive are expressed as seconds since midnight sunday
    # trip_id is a string; it has to be unique
    # daymask is an array of seven booleans like [true, false, false, false, false, false, true]
    #   that indicate which days-of-the-week the schedule runs

    sched = []
    sched << [10, 20, "A", [true, false, false, false, false, false, true]]
    sched << [15, 30, "B", [true, false, false, false, false, false, true]]
    sched << [400, 430, "C", [false, true, true, true, true, true, false]]

    # add the pertinent vertices to the ExampleServer's member variable Graph object:

    @gg.add_vertex( "Seattle-busstop", nil )
    @gg.add_vertex( "Portland-busstop", nil )

    # now connect the vertices with an edge

    @gg.add_triphop_schedule( "Seattle-busstop", "Portland-busstop", sched )

  end

  def load_street_data

    #Street-style data is simpler
    
    @gg.add_vertex( "Seattle", nil )
    @gg.add_vertex( "Portland", nil )

    # street edges are one-way by default, and given length in feet

    @gg.add_street( "Seattle", "Portland", "I-5", 240000 )
    @gg.add_street( "Portland", "Seattle", "I-5", 250000 ) #the return trip is longer, for some reason

  end

  def load_links

    #You can link two vertices together as if they're in the same place

    #They're one-way
    
    @gg.add_link( "Seattle", "Seattle-busstop" )
    @gg.add_link( "Seattle-busstop", "Seattle" )

    @gg.add_link( "Portland", "Portland-busstop" )
    @gg.add_link( "Portland-busstop", "Portland" )

  end

  def initialize
    super
    load_scheduled_data
    load_street_data
    load_links
  end
end

gs = ExampleServer.new
gs.start
