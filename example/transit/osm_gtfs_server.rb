$: << "../../extension/transit"
$: << "../../extension/osm"
$: << "../../extension/osm_gtfs"
$: << "../../extension/kml"

require 'graphserver.rb'
require 'gtfs_extend.rb'
require 'osm_extend.rb'
require 'link_osm_gtfs_extend.rb'
require 'kml_extend.rb'

# At least one parameter (the osm file)
if ARGV.size < 1 then
  print "usage: ruby osm_gtfs_server.rb DIRECTIONAL\n"
  print "       DIRECTIONAL: true if oneway tags are considered\n"
  exit
end

gs = Graphserver.new

#load gtfs data
print "Loading GTFS data\n"
gs.load_google_transit_feed
#load osm data
print "Loading OSM street data\n"
gs.load_osm_from_db file=nil, directional=(ARGV[0]=="false")
#load links
print "Linking GTFS and OSM data\n"
gs.load_osm_gtfs_links

gs.start
