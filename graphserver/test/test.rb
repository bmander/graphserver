require 'graphserver.rb'

gg = Graph.create

a = gg.add_vertex("a", "a")
b = gg.add_vertex("b", "b")
c = gg.add_vertex("c", "c")
c = gg.add_vertex("d", "d")

1000.times do |i|
  gg.add_vertex( i.to_s, i.to_s )
  if i != 0 then
    gg.add_street( (i-1).to_s, (i).to_s, "#{i-1}to#{i}", 10.0 )
  end
end

p gg.shortest_path_tree "0", "non"

gg.vertices.each do |vertex|
  p vertex.label
  vertex.each_outgoing do |edge|
    p edge
  end
end

aa = gg.get_vertex("a")
aa.label

gg.get_vertex( "doesn't exist" )

p gg.add_edge( "a", "b", "blah" ) 
p gg.add_street( "a", "b", "14420", 1.4 )
p gg.add_street( "a", "c", "1234", 1.4 )
p gg.add_street( "c", "d", "4578", 1.5 )
p gg.add_street( "a", "d", "1111", 1.0 )

a.each_outgoing do |edge|
  edge
end

gg.shortest_path_tree "a", "d"

gg.shortest_path_tree "a", "nil"

p gg.shortest_path_tree "a", "d", 100
