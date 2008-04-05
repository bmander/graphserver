$: << "../extension/tiger"

require 'graphserver.rb'
require 'tiger_extend.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => nil, #database username
              :password => nil }

gs = Graphserver.new
gs.database_params = DB_PARAMS
gs.load_tiger_from_db

graph = gs.gg
vertex = graph.get_vertex( "41939956" ) #base of ballard bridge

init_state = State.new( 1179783170 ) #2:33PM monday, May 21, 2007

vertex.each_outgoing do |edge|
  p edge
  p edge.walk( init_state )
end

#test case 1: zero-length route
#base of ballard bridge to nowhere
tree = graph.shortest_path_tree( "41939956", "41939956", init_state, true )
graph.shortest_path( "41939956", "41939956", init_state )
#now in reverse
tree = graph.shortest_path_tree( "41939956", "41939956", init_state, false )
graph.shortest_path_retro( "41939956", "41939956", init_state )

#an extremely simple route
#base of ballard bridge, to one block north
tree = graph.shortest_path_tree( "41939956", "41939955", init_state, true ) 
graph.shortest_path( "41939956", "41939955", init_state )

#now in reverse
tree = graph.shortest_path_tree( "41939956", "41939955", init_state, false )
graph.shortest_path_retro( "41939956", "41939955", init_state )

#several blocks, straight up fifteenth
tree = graph.shortest_path_tree( "41939956", "41938969", init_state, true )
graph.shortest_path(  "41939956", "41938969", init_state )

#across town
tree = graph.shortest_path_tree( "41939956", "41955413", init_state, true )
tree = graph.shortest_path_tree( "41939956", "41955413", init_state, false )

#exhaust the network
tree = graph.shortest_path_tree( "41939956", nil, init_state, true )
tree = graph.shortest_path_tree( nil, "41939956", init_state, false )

#gs.start
