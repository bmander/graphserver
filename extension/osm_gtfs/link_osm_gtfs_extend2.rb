class Graphserver
  SEARCH_RANGE = 0.0006 #degrees
  WGS84_LATLONG_EPSG = 4326

  # Método que procesa un bloque de código para cada parada
  # pasando como parámetros el id y la localizacion
  def each_stop
    stops = conn.exec "SELECT stop_id, location FROM gtf_stops"
    stops.each do |stop_id, location|
      yield stop_id, location
    end
  end

  # Método que devuelve el nodo más próximo del segmento más próximo a una parada
  def nearest_osm_node_in_segment( stop_geom, search_range )
#     node = conn.exec <<-SQL
#       SELECT from_id AS node_id, distance(StartPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
#       FROM osm_segments
#       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
#       UNION
#      (SELECT to_id AS node_id, distance(EndPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
#       FROM osm_segments
#       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} ))
#       ORDER BY dist_seg, dist_node LIMIT 1
#     SQL
#     node = conn.exec <<-SQL
#       SELECT from_id AS node_id, X(StartPoint(geom)) AS x1, Y(StartPoint(geom)) AS y1, X('#{stop_geom}') AS x2, Y('#{stop_geom}') AS y2, distance(StartPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
#       FROM osm_segments
#       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
#       UNION
#      (SELECT to_id AS node_id, X(EndPoint(geom)) AS x1, Y(EndPoint(geom)) AS y1, X('#{stop_geom}') AS x2, Y('#{stop_geom}') AS y2, distance(EndPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
#       FROM osm_segments
#       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} ))
#       ORDER BY dist_seg, dist_node LIMIT 1
#     SQL
     node = conn.exec <<-SQL
       SELECT from_id AS node_id, StartPoint(geom) AS location, distance(StartPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
       FROM osm_segments
       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
       UNION
      (SELECT to_id AS node_id, EndPoint(geom) AS location, distance(EndPoint(geom), '#{stop_geom}') AS dist_node, seg_id, distance(geom, '#{stop_geom}') AS dist_seg
       FROM osm_segments
       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} ))
       ORDER BY dist_seg, dist_node LIMIT 1
     SQL

     # Puede devolver una o ninguna respuesta
     if node.num_tuples == 0 then
       return nil
     else
#       return node[0][0]
#       return node[0][0..4]
       return node[0][0..1]
     end
  end

  # Método que devuelve el tramo de calle más próximo a una parada
  def nearest_osm_segment( stop_geom, search_range )
     segments = conn.exec <<-SQL
       SELECT seg_id, distance(geom, '#{stop_geom}') AS dist
       FROM osm_segments
       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
       ORDER BY dist
       LIMIT 1
     SQL

     # Puede devolver una o ninguna respuesta
     if segments.num_tuples == 0 then
       return nil, nil, nil
     else
       return segments[0][0..2]
     end
  end

  # Método que selecciona el nodo de un way más próximo a una parada
  def nearest_street_node ( stop_geom, search_range )
    point, dist = conn.exec(<<-SQL)[0]
      SELECT from_id AS point,
             distance_sphere(StartPoint(geom), '#{stop_geom}') AS dist
      FROM osm_segments
      WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
      UNION
        (SELECT to_id AS point,
                distance_sphere(EndPoint(geom), '#{stop_geom}') AS dist
         FROM osm_segments
         WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range}))
      ORDER BY dist LIMIT 1
    SQL

    return point
  end

  # divide un tramo osm por un punto intermedio
  def split_osm_segment seg_geom, stop_geom
    ret = []

    split = conn.exec("SELECT line_locate_point('#{seg_geom}', '#{stop_geom}')").getvalue(0, 0).to_f

    #no need to split the segment if the splitpoint is at the end
    if split == 0 or split == 1 then
      return nil
    end

    # en caso contrario devuelve dos filas con las geometrías divididas
    ret << conn.exec("SELECT line_substring('#{seg_geom}', 0, #{split})").getvalue(0,0)
    ret << conn.exec("SELECT line_substring('#{seg_geom}', #{split}, 1)").getvalue(0,0)

    return ret;
  end

  #seg_id : seg_id of the record to replace
  #seg_id_l : seg_id of the left segment
  #seg_id_r : seg_id of the right segment
  #mid_id : endpoint-id joining the new split segment
  #left : WKB of the lefthand segment
  #right : WKB of he righthand segment
  def split_osm_segment! seg_id, seg_id_l, seg_id_r, mid_id, left, right

    res = conn.exec("SELECT * FROM osm_segments WHERE seg_id = '#{seg_id}'")

    nseg_id = res.fieldnum( 'seg_id' )
#    nid = res.fieldnum( 'id' ) # no es necesario el id, simplemente se copia a los 2 tramos
    nto_id = res.fieldnum( 'to_id' )
    nfrom_id = res.fieldnum( 'from_id' )
    ngeom = res.fieldnum( 'geom' )
    row = res[0]

    leftrow = row.dup
    rightrow = row.dup

    # crea las 2 mitades sustituyendo los ids, las geometrías, y haciendo que el nuevo punto
    # sea el final de una y el principio de la otra
    leftrow[ nseg_id ] = seg_id_l
    leftrow[ nto_id] = mid_id
    leftrow[ ngeom ] = left
    rightrow[ nseg_id ] = seg_id_r
    rightrow[ nfrom_id ] = mid_id
    rightrow[ ngeom ] = right

    # borra el tramo original e inserta los nuevos
    transaction = ["BEGIN;"]
    transaction << "DELETE FROM osm_segments WHERE seg_id = '#{seg_id}';"
    transaction << "INSERT INTO osm_segments (#{res.fields.join(',')}) VALUES (#{leftrow.map do |x| if x then "'"+x.delete("\'")+"'" else '' end end.join(",")});"
    transaction << "INSERT INTO osm_segments (#{res.fields.join(',')}) VALUES (#{rightrow.map do |x| if x then "'"+x.delete("\'")+"'" else '' end end.join(",")});"
    transaction << "COMMIT;"

    p transaction.join

    puts transaction

    conn.exec( transaction.join )
  end

  # Looks for the nearest node in the nearest segment for each stop
  # and creates the links in the street_gtfs_links table
  def link_osm_gtfs!
    each_stop do |stop_id, stop_geom|
      # Looks for the nearest node in the nearest segment to the stop in a certain range
#      node_id = nearest_osm_node_in_segment( stop_geom, SEARCH_RANGE )
#      node_id, x1, y1, x2, y2 = nearest_osm_node_in_segment( stop_geom, SEARCH_RANGE )
      node_id, location = nearest_osm_node_in_segment( stop_geom, SEARCH_RANGE )
      # If still not found performs a simpler search in a wider range
#      if not node_id then
#        node_id = nearest_street_node(stop_geom, SEARCH_RANGE*10)
#      end
      # If found, creates the link in the table
      if node_id then
#        conn.exec "INSERT INTO street_gtfs_links (stop_id, node_id) VALUES ('#{stop_id.delete("\'")}', '#{(node_id).delete("\'")}')"
#        geom_wkt = "SRID=#{WGS84_LATLONG_EPSG};LINESTRING( #{x1} #{y1}, #{x2} #{y2} )"
        geom_wkt = "MakeLine('#{stop_geom}', '#{location}')"
        puts geom_wkt
        conn.exec "INSERT INTO street_gtfs_links (stop_id, node_id, geom) VALUES ('#{stop_id.delete("\'")}', '#{(node_id).delete("\'")}', '#{(geom_wkt).delete("\'")}')"
        puts "Linked stop #{stop_id}"
      else
        puts "Didn't find a node close to the stop #{stop_id}"
      end
    end
    #Vacuum analyze table
    conn.exec "VACUUM ANALYZE street_gtfs_links"
  end

  # Metodo que divide los tramos osm en los puntos más cercanos a las paradas
  # y crea los enlaces en la tabla street_gtfs_links
#  def split_osm_segments!
#    each_stop do |stop_id, stop_geom|
#      # busca el tramo de calle más próximo a la parada
#      id, seg_id, seg_geom = nearest_osm_segment( stop_geom, SEARCH_RANGE )
#      if seg_id then
#        # divide el tramo osm por un punto intermedio
#        left, right = split_osm_segment( seg_geom, stop_geom )
#        if left then
#          split_osm_segment!( seg_id, seg_id+"l", seg_id+"r", id+"-"+stop_id, left, right )
#          conn.exec "INSERT INTO street_gtfs_links (stop_id, node_id) VALUES ('#{stop_id.delete("\'")}', '#{(id+"-"+stop_id).delete("\'")}')"
#        end
#      end
#    end
#  end

  # Método que elimina la tabla de enlaces entre osm y gtfs
  def remove_link_table!
    begin
      conn.exec "DROP TABLE street_gtfs_links"
    rescue
      nil
    end
  end

  # Método que crea la tabla de enlaces entre osm y gtfs
  def create_link_table!
    #an extremely simple join table
    conn.exec <<-SQL
      create table street_gtfs_links (
        stop_id            text NOT NULL,
        node_id            text NOT NULL
      );

      select AddGeometryColumn( 'street_gtfs_links', 'geom', #{WGS84_LATLONG_EPSG}, 'LINESTRING', 2 );
    SQL
  end

#  # Crea enlaces entre las paradas gtf y los nodos más cercanos a éstas de osm
#  # Ejecutar después de split_osm_segments! para crear nuevos nodos enmedio
#  # de los tramos osm más cercanos a la parada
#  def link_street_gtfs!
#    each_stop do |stop_id, stop_geom|
#      if node_id = nearest_street_node( stop_geom, SEARCH_RANGE ) then
#        p node_id
#        conn.exec "INSERT INTO street_gtfs_links (stop_id, node_id) VALUES ('#{stop_id.delete("\'")}', '#{node_id.delete("\'")}')"
#      end
#    end
#  end

  # Carga en el grafo los enlaces entre osm y gtfs
  def load_osm_gtfs_links
    res = conn.exec "SELECT stop_id, node_id FROM street_gtfs_links"

    res.each do |stop_id, node_id|
      @gg.add_edge( GTFS_PREFIX+stop_id, OSM_PREFIX+node_id, Link.new )
      @gg.add_edge( OSM_PREFIX+node_id, GTFS_PREFIX+stop_id, Link.new )
    end
  end
end
