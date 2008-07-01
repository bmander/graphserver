$: << "../../extension/tiger_gtfs"

require 'graphserver.rb'
require 'link_tiger_gtfs_extend.rb'

gs = Graphserver.new

puts "Removing Tiger-GTFS link table..."
gs.remove_link_table! #clean up first
puts "Creating Tiger-GTFS link table..."
gs.create_link_table!
puts "Linking Tiger streets with GTFS stops..."
gs.link_street_gtfs!
puts "Finished linking Tiger-GTFS"
