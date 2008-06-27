$: << "../../extension/osm_gtfs"

require 'graphserver.rb'
require 'link_osm_gtfs_extend2.rb'

print "usage: ruby setup_osm_gtfs_link_table.rb SEARCH_RANGE\n"
print "       SEARCH_RANGE: optional, search range (m) for connecting gtfs stops to osm nodes\n"

gs = Graphserver.new

puts "Removing OSM-GTFS link table..."
gs.remove_link_table! #clean up first
puts "Creating OSM-GTFS link table..."
gs.create_link_table!
puts "Linking OSM segments with GTFS stops..."
if ARGV[0] then
  gs.link_osm_gtfs!(ARGV[0])
else
  gs.link_osm_gtfs!
end

puts "Finished linking OSM-GTFS"
