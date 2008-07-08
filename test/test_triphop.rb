require 'graph'

p gg = Graph.create

p a = gg.add_vertex( "a" )
p b = gg.add_vertex( "b" )

efail = gg.add_triphop_schedule("a", "b", [])

p efail.weight( 0 )

schedule = []
schedule << [5, 10, "tripone", [true, false, false, false, false, false, true]]
schedule << [25, 35, "triptwo", [true, false, false, false, false, false, true]]
schedule << [35, 45, "tripthree", [true, false, false, false, false, false, true]]

p ee = gg.add_triphop_schedule( "a", "b", schedule )

(0..36).each do |i|
  print "ee.weight( #{i} ): #{ee.weight(i).inspect}\n"
end
