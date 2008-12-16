$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend.rb'

# At least one parameter (the osm file)
if ARGV.size < 1 then
  print "usage: ruby osm_db_server.rb DIRECTIONAL\n"
  print "       DIRECTIONAL: true if oneway tags are considered\n"
  exit
end

gs = Graphserver.new
gs.load_osm_from_db file=nil, directional=(ARGV[0]=="true"), weights=ARGV[1]
gs.start