$: << "../../extension/transit"
$: << "../../extension/tiger"
$: << "../../extension/tiger_gtfs"

require 'graphserver.rb'
require 'gtfs_extend.rb'
require 'tiger_extend.rb'
require 'link_tiger_gtfs_extend.rb'

#$: << "../../extension/map"
#require 'map_extend.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => nil, #database username
              :password => nil }

gs = Graphserver.new
gs.database_params = DB_PARAMS

#load gtfs data
print "Loading GTFS data\n"
gs.load_google_transit_feed
#load tiger data
print "Loading TIGER street data\n"
gs.load_tiger_from_db
#load links
print "Linking GTFS and TIGER data\n"
gs.load_tiger_gtfs_links

gs.start
