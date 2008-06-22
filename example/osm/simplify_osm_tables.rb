$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend2.rb'

gs = Graphserver.new
gs.simplify_graph!
