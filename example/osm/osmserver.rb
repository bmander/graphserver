

$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend.rb'

gs = Graphserver.new
gs.build_graph_from_osmfile 'cambridge.osm', directional=true
gs.start
