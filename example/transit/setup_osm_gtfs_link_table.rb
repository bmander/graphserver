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

gs.remove_link_table! #clean up first
gs.create_link_table!
#gs.split_osm_segments!
gs.link_osm_gtfs!
