from graphserver.core import Graph, Street, State

g = Graph()

i = 0
g.add_vertex( str(i) )

while i < 1000000:
  for j in range(1000):
    i += 1
    g.add_vertex( str(i) )
    e = g.add_edge(str(i-1), str(i), Street(str(i-1)+"to"+str(i), 1))

  print i,"vertices added."
  print "Computing shortest path tree from \'0\' to \'",i,"\'"
  spt = g.shortest_path_tree("0", str(i), State(1,0))
