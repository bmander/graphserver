require 'graph.rb'

g = Graph.new
g.add_vertex(:A, nil)
g.add_vertex(:B, String.new( "what" ))
g.add_vertex(:C, nil)
g.add_vertex(:D, 1)
g.add_vertex(:E, [12, 20])
g.add_vertex(:F, nil)
g.add_vertex(:G, nil)

g.add_edge(:A, :B, 7)
g.add_edge(:A, :D, 5)
g.add_edge(:B, :A, 7)
g.add_edge(:B, :D, 9)
g.add_edge(:B, :E, 7)
g.add_edge(:B, :C, 8)
g.add_edge(:C, :B, 8)
g.add_edge(:C, :E, 5)
g.add_edge(:D, :A, 5)
g.add_edge(:D, :B, 9)
g.add_edge(:D, :E, 15)
g.add_edge(:D, :F, 6)
g.add_edge(:E, :C, 5)
g.add_edge(:E, :B, 7)
g.add_edge(:E, :D, 15)
g.add_edge(:E, :F, 8)
g.add_edge(:E, :G, 9)
g.add_edge(:F, :D, 6)
g.add_edge(:F, :E, 8)
g.add_edge(:F, :G, 11)
g.add_edge(:G, :E, 9)
g.add_edge(:G, :F, 11)

g.get_shortest_path(:A, :G)

g.methods

ma = Marshal.dump g
 Marshal.load ma

