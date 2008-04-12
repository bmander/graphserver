$: << "../../extension/transit"

require 'graphserver.rb'
require 'gtfs_extend.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => 'postgres', #database username
              :password => 'postgres' }

gs = Graphserver.new
gs.database_params = DB_PARAMS

#load gtfs data
print "Loading GTFS data\n"
gs.load_google_transit_feed
gs.link_stops_los

gs.start
