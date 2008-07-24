$: << "../../extension/transit"
$: << "../../extension/kml"

require 'graphserver.rb'
require 'gtfs_extend.rb'
require 'kml_extend.rb'

gs = Graphserver.new

#load gtfs data
print "Loading GTFS data\n"
gs.load_google_transit_feed
gs.link_stops_los
gs.start
