require 'graph_core'

#Sobrecarga la clase Vertex para añadir las funciones
#inspect, edge_out y edge_in
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

#Sobrecarga la clase Graph para aÃ±adir las funciones
#edges, shortest_path, shortest_path_retro y to_dot
class Graph
  #Construye un array con todos los enlaces (edges) y devuelve su valor
  def edges
    edges = []
    self.vertices.each do |vertex|
      vertex.each_outgoing do |edge|
        edges << edge
      end
    end
    edges
  end

  #Calcula el camino mas corto entre dos vertices tomando
  #init_state como la hora de partida
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

  #Calcula el camino mas corto entre dos vertices tomando
  #final_state como la hora de llegada
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

  #Devuelve una representacion del grafo en forma de lista de enlaces
  #escribiendo "nodo_origen -> nodo_destino"
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
