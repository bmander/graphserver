require 'Graphserver'

# Overrides Vertex to add the methods inspect, edge_out and edge_in
class Vertex
  def inspect
    ret = "#<Vertex label=\"#{label}\" degree_in=#{degree_in} degree_out=#{degree_out}"
    (ret << " payload=#{payload.inspect}") if payload
    ret << ">"
  end

  def edge_out index
    i=0
    self.each_outgoing do |edge|
      p edge
      if i==index then
        return edge
      end
      i += 1
    end
    return nil
  end

  def edge_in index
    i=0
    self.each_incoming do |edge|
      if i==index then
        return edge
      end
      i += 1
    end
    return nil
  end
end

# Overrides Graph to add the methods edges, shortest_path, shortest_path_retro and to_dot
class Graph
  def edges
    edges = []
    self.vertices.each do |vertex|
      vertex.each_outgoing do |edge|
        edges << edge
      end
    end
    edges
  end

  # Computes the shortest path between two vertices
  # using init_state as departure time
  def shortest_path from, to, init_state
    path_vertices = []
    path_edges    = []

    spt = shortest_path_tree( from, to, init_state, true )
    curr = spt.get_vertex( to )

    #if the end node wasn't found
    unless curr then raise RuntimeError end

    path_vertices << curr

    while incoming = curr.edge_in( 0 )
      path_edges << incoming

      curr = incoming.from
      path_vertices << curr
    end

    return path_vertices.reverse, path_edges.reverse
  end

  # Computes the shortest path between two vertices
  # using init_state as arrival time
  def shortest_path_retro from, to, final_state
    path_vertices = []
    path_edges    = []

    spt = shortest_path_tree( from, to, final_state, false )
    curr = spt.get_vertex( from )
    path_vertices << curr

    while incoming = curr.edge_in(0)
      path_edges << incoming

      curr = incoming.from
      path_vertices << curr
    end

    return path_vertices, path_edges
  end

  # Returns a representation of the graph as a list of links
  def to_dot
    accum = []
    accum << "digraph G {"
    self.edges.each do |edge|
      accum << "   #{edge.from.label} -> #{edge.to.label};\n"
    end
    accum << "}"
    accum.join
  end

end
