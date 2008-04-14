$: << "../../extension/osm_gtfs"

require 'graphserver.rb'
require 'link_osm_gtfs_extend2.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => 'postgres', #database username
              :password => 'postgres' }

gs = Graphserver.new
gs.database_params = DB_PARAMS

puts "Removing OSM-GTFS link table"
gs.remove_link_table! #clean up first
puts "Creating OSM-GTFS link table"
gs.create_link_table!
#puts "Splitting OSM segments close to GTFS stops..."
#gs.split_osm_segments!
puts "Linking OSM segments with GTFS stops..."
gs.link_osm_gtfs!
puts "Finished linking OSM-GTFS"
