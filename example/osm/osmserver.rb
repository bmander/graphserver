

$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend.rb'

gs = Graphserver.new
gs.load_osm_from_file 'cambridge.osm'
gs.start
