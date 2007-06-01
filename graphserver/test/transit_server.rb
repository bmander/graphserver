$: << "../../extension/transit"

require 'graphserver.rb'
require 'load_google_transit_feed.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => nil, #database username
              :password => nil }

gs = Graphserver.new
gs.database_params = DB_PARAMS
gs.load_calendar
gs.load_google_transit_feed

state = State.new( 1179518940 )
state[:calendar_day] = gs.calendar.day_of_or_after( 1179518940 )

vertices = gs.gg.vertices
1000.times do |i|
  vertex = vertices[i]
  vertex.each_outgoing do |edge|
    p "---"
    p payload = edge.payload
    p payload.walk( state )
  end
end

#gs.start
