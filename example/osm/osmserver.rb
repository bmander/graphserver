

$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend.rb'

gs = Graphserver.new
gs.load_osm_from_file 'greater_cambridge.osm'
gs.start
