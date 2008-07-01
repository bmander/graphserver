$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend.rb'

gs = Graphserver.new
gs.simplify_graph!
