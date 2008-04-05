class Graphserver
  SEARCH_RANGE = 0.0006 #degrees

  # Método que procesa un bloque de código para cada parada
  # pasando como parámetros el id y la localizacion
  def each_stop
    stops = conn.exec "SELECT stop_id, location FROM gtf_stops"
    stops.each do |stop_id, location|
      yield stop_id, location
    end
  end

  # Método que devuelve la calle más próxima a una parada
  def nearest_osm_line( stop_geom, search_range )
     lines = conn.exec <<-SQL
       SELECT id, geom, distance(geom, '#{stop_geom}') AS dist
       FROM osm_streets
       WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
       ORDER BY dist
       LIMIT 1
     SQL

     # Puede devolver una o ninguna respuesta
     if lines.num_tuples == 0 then
       return nil, nil
     else
       return lines[0][0..1]
     end
  end

  # divide un tramo osm por un punto intermedio
  def split_osm_line line_geom, stop_geom
    ret = []

    split = conn.exec("SELECT line_locate_point('#{line_geom}', '#{stop_geom}')").getvalue(0, 0).to_f

    #no need to split the line if the splitpoint is at the end
    if split == 0 or split == 1 then
      return nil
    end

    # en caso contrario devuelve dos filas con las geometrías divididas
    ret << conn.exec("SELECT line_substring('#{line_geom}', 0, #{split})").getvalue(0,0)
    ret << conn.exec("SELECT line_substring('#{line_geom}', #{split}, 1)").getvalue(0,0)

    return ret;
  end

  #tlid : line_id of the record to replace
  #tlid_l : line_id of the left line
  #tlid_r : line_id of the right line
  #tzid : endpoint-id joining the new split line
  #left : WKB of the lefthand line
  #right : WKB of he righthand line
  def split_osm_line! tlid, tlid_l, tlid_r, tzid, left, right

    res = conn.exec("SELECT * FROM osm_streets WHERE id = '#{tlid}'")

    nid = res.fieldnum( 'id' )
    nto_id = res.fieldnum( 'to_id' )
    nfrom_id = res.fieldnum( 'from_id' )
    ngeom = res.fieldnum( 'geom' )
    row = res[0]

    leftrow = row.dup
    rightrow = row.dup

    # crea las 2 mitades sustituyendo los ids, las geometrías, y haciendo que el nuevo punto
    # sea el final de una y el principio de la otra
    leftrow[ nid ] = tlid_l
    leftrow[ nto_id] = tzid
    leftrow[ ngeom ] = left
    rightrow[ nid ] = tlid_r
    rightrow[ nfrom_id ] = tzid
    rightrow[ ngeom ] = right

    # borra el tramo original e inserta los nuevos
    transaction = ["BEGIN;"]
    transaction << "DELETE FROM osm_streets WHERE id = '#{tlid}';"
    transaction << "INSERT INTO osm_streets (#{res.fields.join(',')}) VALUES (#{leftrow.map do |x| if x then "'"+x.delete("\'")+"'" else '' end end.join(",")});"
    transaction << "INSERT INTO osm_streets (#{res.fields.join(',')}) VALUES (#{rightrow.map do |x| if x then "'"+x.delete("\'")+"'" else '' end end.join(",")});"
    transaction << "COMMIT;"

    p transaction.join

    puts transaction

    conn.exec( transaction.join )
  end

  # Metodo que divide los tramos osm en los puntos más cercanos a las paradas
  def split_osm_lines!
    each_stop do |stop_id, stop_geom|
      # busca el tramo de calle más próximo a la parada
      line_id, line_geom = nearest_osm_line( stop_geom, SEARCH_RANGE )
      if line_id then
        # divide el tramo osm por un punto intermedio
        left, right = split_osm_line( line_geom, stop_geom )
        if left then
          split_osm_line!( line_id, stop_id+"0", stop_id+"1", stop_id, left, right )
        end
      end
    end
  end

  # Método que selecciona el nodo de un way más próximo a una parada
  def nearest_street_node stop_geom
    point, dist = conn.exec(<<-SQL)[0]
      SELECT from_id AS point,
             distance_sphere(StartPoint(geom), '#{stop_geom}') AS dist
      FROM osm_streets
      WHERE geom && expand( '#{stop_geom}'::geometry, #{SEARCH_RANGE} )
      UNION
        (SELECT to_id AS point,
                distance_sphere(EndPoint(geom), '#{stop_geom}') AS dist
         FROM osm_streets
         WHERE geom && expand( '#{stop_geom}'::geometry, #{SEARCH_RANGE}))
      ORDER BY dist LIMIT 1
    SQL

    return point
  end

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
    SQL
  end

  # Crea enlaces entre las paradas gtf y los nodos más cercanos a éstas de osm
  # Ejecutar después de split_osm_lines! para crear nuevos nodos enmedio
  # de los tramos osm más cercanos a la parada
  def link_street_gtfs!
    each_stop do |stop_id, stop_geom|
      if node_id = nearest_street_node( stop_geom ) then
        p node_id
        conn.exec "INSERT INTO street_gtfs_links (stop_id, node_id) VALUES ('#{stop_id.delete("\'")}', '#{node_id.delete("\'")}')"
      end
    end
  end

  # Carga en el grafo los enlaces entre osm y gtfs
  def load_osm_gtfs_links
    res = conn.exec "SELECT stop_id, node_id FROM street_gtfs_links"

    res.each do |stop_id, node_id|
      @gg.add_edge( stop_id, node_id, Link.new )
      @gg.add_edge( node_id, stop_id, Link.new )
    end
  end
end
