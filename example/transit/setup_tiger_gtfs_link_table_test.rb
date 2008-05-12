$: << "../../extension/tiger_gtfs"

require 'graphserver.rb'
require 'link_tiger_gtfs_extend.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'gstest',
              :login => nil, #database username
              :password => nil }

gs = Graphserver.new
gs.database_params = DB_PARAMS

puts "Removing Tiger-GTFS link table..."
gs.remove_link_table! #clean up first
puts "Creating Tiger-GTFS link table..."
gs.create_link_table!
puts "Splitting Tiger streets close to GTFS stops..."
#gs.split_tiger_lines!
puts "Linking Tiger streets with GTFS stops..."
gs.link_street_gtfs!
puts "Finished linking Tiger-GTFS"
