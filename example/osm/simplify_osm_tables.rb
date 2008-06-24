$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend2.rb'

gs = Graphserver.new
t0 = Time.now
gs.simplify_graph!
t1 = Time.now
puts "Graph simplification accomplished in #{t1-t0} sec"