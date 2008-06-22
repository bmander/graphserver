$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend2.rb'

# At least one parameter (the osm file)
if ARGV.size < 1 then
  print "usage: ruby osm_server.rb OSMFILE DIRECTIONAL DEBUG_LEVEL\n"
  print "       OSMFILE: osm data file name\n"
  print "       DIRECTIONAL: true if oneway tags are considered\n"
  print "       DEBUG_LEVEL: 0 (no), 1(medium) or 2(verbose)\n"
  exit
end

gs = Graphserver.new
gs.load_osm_from_file ARGV[0], directional=ARGV[1], debug_level=ARGV[2]
gs.start
