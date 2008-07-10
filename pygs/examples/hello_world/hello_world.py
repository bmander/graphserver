try:
    from graphserver.engine import XMLGraphEngine
    from graphserver.structures import TripHopSchedule, CalendarDay, Street, Link, State
except ImportError:
    import sys
    sys.path.append("../..")
    from engine import XMLGraphEngine
    from graphserver import TripHopSchedule, CalendarDay, Street, Link, State

class HelloWorldEngine(XMLGraphEngine):

  def load_scheduled_data(self):

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

    self.gg.add_vertex( "Seattle-busstop" )
    self.gg.add_vertex( "Portland-busstop" )

    # now connect the vertices with an edge

    self.gg.add_edge( "Seattle-busstop", "Portland-busstop", ths )

  

  def load_street_data(self):

    #Street-style data is simpler
    
    self.gg.add_vertex( "Seattle" )
    self.gg.add_vertex( "Portland" )

    # street edges are one-way by default, and given length in feet

    self.gg.add_edge( "Seattle", "Portland", Street( "I-5", 240000 ) )
    self.gg.add_edge( "Portland", "Seattle", Street( "I-5", 250000 ) ) #say the return trip is longer, for some reason

  

  def load_links(self):

    #You can link two vertices together as if they're in the same place

    #They're one-way
    
    self.gg.add_edge( "Seattle", "Seattle-busstop", Link() )
    self.gg.add_edge( "Seattle-busstop", "Seattle", Link() )

    self.gg.add_edge( "Portland", "Portland-busstop", Link() )
    self.gg.add_edge( "Portland-busstop", "Portland", Street( "a-street-payload", 1.11) )

  def __init__(self):
    super(HelloWorldEngine, self).__init__()
    self.load_scheduled_data()
    self.load_street_data()
    self.load_links()
  

if __name__ == '__main__':
    from xml.dom import minidom
    from xml.dom.ext import PrettyPrint
    from xml.parsers.expat import ExpatError
    import sys
    def pretty(label, content):
        try:
            dom = minidom.parseString(content)
            print label,":"
            PrettyPrint(dom, sys.stdout)
            print "\n\n"
        except ExpatError, e:
            raise "Invalid XML: " + content
        
    h = HelloWorldEngine()
    pretty("all_vertex_labels", h.all_vertex_labels())
    pretty("outgoing_edges?label=Seattle", h.outgoing_edges("Seattle"))
    # no method exists:
    #pretty("eval_edges?label=Seattle", h.eval_edges("Seattle"))
    pretty("/shortest_path?from=Seattle&to=Portland", h.shortest_path("Seattle","Portland",0))