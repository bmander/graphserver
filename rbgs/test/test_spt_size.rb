# Shortest path tree size
# This test aims to find a limit in the size of the shortest path tree
# Each iteration will add 1000 vertices and trigger a shortest path calculation
# between the first and the last vertex
# Should end with a segment fault or memory leak

$: << ".."
load 'graphserver.rb'

g = Graph.create

i=0
g.add_vertex( i.to_s )

while true do

  1000.times do |j|
    i += 1
    g.add_vertex( i.to_s )
    s = Street.new( "#{i-1}to#{i}", 1 )
    e = g.add_edge((i-1).to_s, i.to_s, s)
  end

  puts "#{i} vertices added."
  puts "Computing shortest path tree from \'0\' to \'#{i}\'"
  spt = g.shortest_path_tree("0", i.to_s, State.new(1,0),true)

end
