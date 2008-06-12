require 'rexml/document'
require "rexml/streamlistener"
require 'rubygems'
require 'json'

include REXML
include Math

#Clase que modela los nodos de OSM
class OSMNode
  attr_accessor :id, :lat, :lon, :tags

  def initialize id
    @id = id
    @tags = {} #Hash que almacena los tags
  end

end

#Clase que modela los ways de OSM
class OSMWay
  attr_accessor :id, :nodes, :tags

  def initialize id
    @id = id
    @nodes = [] #Array que almacena los IDs de los nodos que componen el way
    @tags = {} #Hash que almacena los tags
  end

end


# Sobrecarga la clase Graphserver
class Graphserver
  WGS84_LATLONG_EPSG = 4326
  OSM_PREFIX = "osm" # Namespace of OSM data when loading the graph

  # Subclase OSMListener, parsea el fichero OSM y genera el grafo
  class OSMListener
    include StreamListener

    # Prepara el listener para parsear un archivo
    # e introducir datos en la base de datos
    # o bien grafo
    def initialize graph, directional, connection, file, debug_level
      #general parsing variables
      @curr_obj = nil
      @directional = directional
      @con = connection
      @file = file
      @debug_level = debug_level.to_i

      #graphserver-specific variables
      @nodes = {}
      @gg = graph
    end

    #Subclass listener
    #Metodo que procesa el inicio de un tag xml (x ej <node lat="" lon="">)
    def tag_start name, attr

      case name
        when 'node'
          @curr_obj = OSMNode.new( attr['id'] )
          @curr_obj.lat = attr['lat'].to_f
          @curr_obj.lon = attr['lon'].to_f
        when 'way'
          @curr_obj = OSMWay.new( attr['id'] )
        when 'nd'
          @curr_obj.nodes << attr['ref']
        when 'tag'
          @curr_obj.tags[ attr['k'] ] = attr['v']
      end

    end

    #Subclass listener
    #Metodo que procesa el final de un tag xml (x ej </node>)
    def tag_end name

      case name
        when 'node'
          if @gg then
            handle_node @curr_obj
          else
            handle_node_db @curr_obj
          end
        when 'way'
          # We only process walking/driving navigable ways
          if @curr_obj.tags['highway'] then
          #if ( @curr_obj.tags['highway'] || @curr_obj.tags['railway'] || @curr_obj.tags['aerialway'] || @curr_obj.tags['route'] ) then
            if @gg then
              handle_way @curr_obj
            else
              handle_way_db @curr_obj
            end
          else
            if @debug_level>0 then
              puts "ignored way( id=#{@curr_obj.id}, name='#{@curr_obj.tags['name']}' )"
            end
          end
      end

    end


    #Metodo que procesa un nodo OSM añadiendo un vertice al grafo
    def handle_node node
#      @gg.add_vertex( node.id )
      @gg.add_vertex( OSM_PREFIX+node.id )
      @nodes[node.id] = [node.lat, node.lon]
    end


    #Metodo que procesa un nodo OSM para posteriormente añadirlo a la base de datos
    def handle_node_db node
      @nodes[node.id] = [node.lat, node.lon]
    end


    #Metodo que procesa un way OSM añadiendo un enlace al grafo
    def handle_way way

      name = "#{way.tags['name'] || "Unnamed"} (#{way.id})"
      type = "#{way.tags['highway']}"
      #type = "#{way.tags['highway'] || way.tags['railway'] || way.tags['aerialway'] || way.tags['route'] || "Other"}"
      # If the oneway tag is not set or it is set to none, set oneway to false
      if not way.tags['oneway'] or way.tags['oneway']=='false' or way.tags['oneway']=='no' then
        oneway = false
      else
        oneway = true
      end

      current = nil
      total_len = 0

      # For each node in the way...
      way.nodes.each do |node|
        if current then
          from_id = current
          to_id = node

          # Calcula la longitud del tramo mediante la formula Haversine
          # http://en.wikipedia.org/wiki/Haversine_formula
          radius = 6371000 # Earth mean radius in m
          lat0 = @nodes[from_id][0] * PI / 180 #rad
          lon0 = @nodes[from_id][1] * PI / 180 #rad
          lat1 = @nodes[to_id][0] * PI / 180 #rad
          lon1 = @nodes[to_id][1] * PI / 180 #rad
          dLat = (lat1 - lat0) #rad
          dLon = (lon1 - lon0) #rad
          a = sin(dLat/2) * sin(dLat/2) +
                  cos(lat0) * cos(lat1) *
                  sin(dLon/2) * sin(dLon/2)
          c = 2 * atan2(sqrt(a), sqrt(1-a))
          len = radius * c
          total_len += len

          # Geometry of the edge
          geom = "#{lon0},#{lat0} #{lon1},#{lat1}"
#          @gg.add_edge( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(name, len) )
#          @gg.add_edge( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(CGI::escape(name), len) )
          @gg.add_edge_geom( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(name, len), geom)
          if @debug_level==2 then
#            puts "added Edge( fromId=#{prev_id}, toId=#{prev_id}, length=#{len} )"
            puts "added Edge( fromId=#{OSM_PREFIX+from_id}, toId=#{OSM_PREFIX+to_id}, length=#{len} )"
          end
          # Add reverse edge if not directional or not oneway
          if not @directional or not oneway then
            # Geometry of the reverse edge
            rgeom = "#{lon1},#{lat1} #{lon0},#{lat0}"
#            @gg.add_edge( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(name, len) )
#            @gg.add_edge( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(CGI::escape(name), len) )
            @gg.add_edge_geom( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(name, len), rgeom)
            puts "added Edge( fromId=#{OSM_PREFIX+to_id}, toId=#{OSM_PREFIX+from_id}, length=#{len} )"
          end

        end
        current = node
      end

      if @debug_level>0 then
        puts "processed way( id=#{way.id}, name='#{name}', oneway=#{oneway}, length=#{total_len})"
      end

    end


    #Metodo que procesa un way OSM añadiendo varias filas en la base de datos
    def handle_way_db way

      name = "#{way.tags['name'] || "Unnamed"}"
      type = "#{way.tags['highway']}"
      #type = "#{way.tags['highway'] || way.tags['railway'] || way.tags['aerialway'] || way.tags['route'] || "Other"}"
      # If the oneway tag is not set or it is set to none, set oneway to false
      if not way.tags['oneway'] or way.tags['oneway']=='false' or way.tags['oneway']=='no' then
        oneway = false
      else
        oneway = true
      end

      # Puts the street in the osm_ways table
      @con.exec "COPY osm_ways (id, name, type, oneway, file) FROM STDIN"
      @con.putline "#{way.id}\t#{name}\t#{type}\t#{oneway}\t#{@file}\n"
      @con.endcopy

      ret = "LINESTRING("
      node_count = 0
      current = nil

      # For each node in the way...
      way.nodes.each do |node|
        if current then
          from_id = current
          to_id = node

          lat0 = @nodes[from_id][0].to_s
          lon0 = @nodes[from_id][1].to_s
          lat1 = @nodes[to_id][0].to_s
          lon1 = @nodes[to_id][1].to_s
          # Import street in regular sense to the DB
          geom = "LINESTRING(#{lon0} #{lat0},#{lon1} #{lat1})";
          @con.exec "COPY osm_segments (seg_id, id, from_id, to_id, geom ) FROM STDIN"
#          @con.putline "#{way.id}-#{node_count.to_s.rjust(5,'0')}\t#{way.id}\t#{prev_id}\t#{cur_id}\tSRID=#{WGS84_LATLONG_EPSG};#{geom}\n"
          @con.putline "#{way.id}-#{node_count}\t#{way.id}\t#{from_id}\t#{to_id}\tSRID=#{WGS84_LATLONG_EPSG};#{geom}\n"
          @con.endcopy
          node_count += 1
        end
        ret <<  "#{@nodes[node][1]} #{@nodes[node][0]}"
        ret << ","
        current = node
      end

      ret[ret.size-1] =")"
      if @debug_level==2 then
        puts ret
      end

      if @debug_level>0 then
        puts "processed way( id=#{way.id}, name='#{name}', oneway=#{oneway})"
      end

    end

  end


  def create_osm_table!
    conn.exec <<-SQL
      CREATE TABLE osm_ways (
      id          text PRIMARY KEY,
      name        text,
      type        text,
      oneway      text,
      file        text
    )
    SQL

    conn.exec <<-SQL
      CREATE TABLE osm_segments (
      seg_id      text PRIMARY KEY,
      id          text,
      from_id     text,
      to_id       text
    )
    SQL

    conn.exec <<-SQL
      SELECT AddGeometryColumn( 'osm_segments', 'geom', #{WGS84_LATLONG_EPSG}, 'LINESTRING', 2 )
    SQL

    conn.exec <<-SQL
      CREATE OR REPLACE VIEW osm_streets AS
      SELECT osm1.id, osm2.from_id, osm2.to_id, osm1.name, osm1."type", osm1.oneway, osm2.geom, osm1.file
      FROM osm_ways osm1, osm_segments osm2
      WHERE osm1.id = osm2.id;
    SQL

    conn.exec <<-SQL
      CREATE INDEX osm_ways_id_idx ON osm_ways ( id );
      CREATE INDEX osm_segments_seg_id_idx ON osm_segments ( seg_id );
      CREATE INDEX osm_segments_geom_idx ON osm_segments USING GIST ( geom GIST_GEOMETRY_OPS );
    SQL
    puts "osm_ways table created"
    puts "osm_segments table created"
    puts "osm_streets view created"
  end

  # Une tramos de calles que tienen el mismo id
  def consolidate_lines!
    # Solicita tramos de calles simplificables
    res = conn.exec <<-SQL
      SELECT *
      FROM osm_ways
      WHERE from_id IN ( SELECT from_id
                         FROM ( SELECT from_id
                                FROM osm_ways
                                GROUP BY from_id
                                HAVING count(*)=1) tmp_from,
                              ( SELECT to_id
                                FROM osm_ways
                                GROUP BY to_id
                                HAVING count(*)=1) tmp_to
                         WHERE tmp_from.from_id=tmp_to.to_id )
      OR to_id IN      ( SELECT from_id
                         FROM ( SELECT from_id
                                FROM osm_ways
                                GROUP BY from_id
                                HAVING count(*)=1) tmp_from,
                              ( SELECT to_id
                                FROM osm_ways
                                GROUP BY to_id
                                HAVING count(*)=1) tmp_to
                         WHERE tmp_from.from_id=tmp_to.to_id )
    SQL

    # Returns the index of the column named 'id' of the response
    id_n = res.fieldnum( 'id' )

    current = nil
    # Para cada tramo simplificable
    res.each do |row|
      if current then
        prev_row = current
        cur_row = row
        # Si el to_id de la fila anterior es igual al from_id de la fila actual
        # y ambas filas pertenecen al mismo way (mismo id)
        if (cur_row[1] == prev_row[2] and cur_row[0] == prev_row[0]) then
          # Borrar el registro actual
          conn.exec "delete from osm_ways where id='#{cur_row[id_n]}'"
        end
      end
      current = row
#      cad22 = "insert into osm_ways (#{res.fields.join(',')}) VALUES (#{row.map do |ii| "\'"+ii.delete("\'") +"'" end.join(',')})"
    end
  end


  #Eliminar las tablas osm en la BD
  def remove_osm_table!
    begin
      conn.exec "DROP VIEW osm_streets"
      conn.exec "DROP TABLE osm_segments"
      conn.exec "DROP TABLE osm_ways"
      puts "osm_streets view removed"
      puts "osm_segments table removed"
      puts "osm_ways table removed"
    rescue
      nil
    end
  end

  #Importar un archivo osm a la BD
  def import_osm_to_db! file, debug_level=0

    list = OSMListener.new nil, nil, conn, file, debug_level
    source = File.new file, "r"
    REXML::Document.parse_stream(source, list)

    conn.exec "VACUUM ANALYZE osm_ways"
    conn.exec "VACUUM ANALYZE osm_segments"
#    puts "consolidating lines\n"
#    consolidate_lines!
#    conn.exec "VACUUM ANALYZE osm_ways"
  end


  # Generar el grafo a partir de tablas osm de la BD
  # Si se pasa un nombre de archivo como parámetro
  # sólo se cargarán los datos que provienen de ese archivo
  def load_osm_from_db file=nil, directional=false
    query = "SELECT id, from_id, to_id, name, type, oneway, "
    query << "length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]'), "
#    query << "AsText(geom) "
    query << "AsText(geom), AsText(Reverse(geom))"
    query << "FROM osm_streets "
    query << "WHERE file = '#{file}'" if file

    res = conn.exec query
#    res.each do |id, from_id, to_id, name, type, oneway, length|
#    res.each do |id, from_id, to_id, name, type, oneway, length, coords|
    res.each do |id, from_id, to_id, name, type, oneway, length, coords, rcoords|
      #In KML LineStrings have the spaces and the comas swapped with respect to postgis
      #We just substitute a space for a comma and viceversa
      coords.gsub!(" ","|")
      coords.gsub!(","," ")
      coords.gsub!("|",",")
      rcoords.gsub!(" ","|")
      rcoords.gsub!(","," ")
      rcoords.gsub!("|",",")
      #Also deletes the LINESTRING() envelope
      coords.gsub!("LINESTRING(","")
      coords.gsub!(")","")
      rcoords.gsub!("LINESTRING(","")
      rcoords.gsub!(")","")
#      puts "adding Street (id=#{id}, name='#{name}', type=#{type}, length=#{length}, oneway=#{oneway})"
#      @gg.add_vertex( from_id )
      @gg.add_vertex( OSM_PREFIX+from_id )
#      @gg.add_vertex( to_id )
      @gg.add_vertex( OSM_PREFIX+to_id )
#      @gg.add_edge( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new( name, Float(length) ) )
#      @gg.add_edge( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new( CGI::escape(name), Float(length) ) )
      @gg.add_edge_geom( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(name, Float(length)), coords )
#      puts "adding Edge (from_id=#{from_id}, to_id=#{to_id})"
      if not directional or oneway=="false"
#        puts "adding reverse Edge (from_id=#{to_id}, to_id=#{from_id})"
#        @gg.add_edge( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new( name, Float(length) ) )
#        @gg.add_edge( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new( CGI::escape(name), Float(length) ) )
#        @gg.add_edge_geom( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(CGI::escape(name), Float(length)), coords )
        @gg.add_edge_geom( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(name, Float(length)), rcoords )
      end

    end
  end

  #Metodo que genera el grafo desde un archivo OSM
  def load_osm_from_file file, directional=false, debug_level=0

    #Crea el objeto OSMListener que parsea el fichero OSM y genera el grafo
    list = OSMListener.new @gg, directional, nil, nil, debug_level

    source = File.new file, "r"
    REXML::Document.parse_stream(source, list)

  end

  #Overrides function which is not implemented in graphserver.rb
  #This function looks for the vertices of the closest edge to the input coords
  #Returns an array of 3 rows an columns named label, lat, lon, name, dist
  #The first row is not actually a vertex, but the nearest point in the edge
  #to the input coordinates
  def get_closest_edge_vertices(lat, lon)
    center = "GeomFromText(\'POINT(#{lon} #{lat})\',4326)"
    #Looks for the closest tiger line in the search range
    line = conn.exec <<-SQL
      SELECT id, geom, distance(geom, #{center}) AS dist
      FROM osm_streets
      WHERE geom && expand( #{center}::geometry, 0.003 )
      ORDER BY dist
      LIMIT 1
    SQL

    if line.num_tuples == 0 then return nil end

    line_id = line[0][0]
    line_geom = line[0][1]

    #Looks for the closest street vertex in a radius of approximately 500m from the center
    res = conn.exec <<-SQL
      SELECT 'nearest_point_in_line' AS label, Y(line_point) AS lat, X(line_point) AS lon, name,
             distance_sphere(line_point, #{center}) AS dist_vertex
      FROM osm_streets,
      (SELECT line_interpolate_point('#{line_geom}', line_locate_point('#{line_geom}', #{center})) AS line_point) AS tpoint
      WHERE id = '#{line_id}'
      UNION
     (SELECT 'osm' || from_id AS label, Y(StartPoint(geom)) AS lat, X(StartPoint(geom)) AS lon, name,
             distance_sphere(StartPoint(geom), #{center}) AS dist_vertex
      FROM osm_streets
      WHERE id = '#{line_id}'
      UNION
     (SELECT 'osm' || to_id AS label, Y(EndPoint(geom)) AS lat, X(EndPoint(geom)) AS lon, name,
             distance_sphere(EndPoint(geom), #{center}) AS dist_vertex
      FROM osm_streets
      WHERE id = '#{line_id}' )
      ORDER BY dist_vertex
      LIMIT 2 )
    SQL

    #An array of vertices
    v = []
    i = 0
    #Each vertex is a hash of properties
    if res then
      res.each do |vertex|
        v[i]={}
        v[i]['label'] = vertex[0] #Label of the vertex
        v[i]['lat'] = vertex[1] #Latitude of the vertex
        v[i]['lon'] = vertex[2] #Longitude of the vertex
        v[i]['name'] = vertex[3] #Name of the closest edge containing the vertex
        v[i]['dist'] = vertex[4] #Distance from the vertex to the input coordinates
        i += 1
      end
    end
    return v
  end

  #Overrides function which is not implemented in graphserver.rb
  def get_vertex_from_coords(lat, lon)
    v = {}
    center = "GeomFromText(\'POINT(#{lon} #{lat})\',4326)"

    #Searches for vertex in a radius of approximately 500m from the center
#    label, lat, lon, name, dist = conn.exec(<<-SQL)[0]
#    r = conn.exec(<<-SQL)[0]
#      SELECT from_id AS label, Y(StartPoint(geom)) AS lat, X(StartPoint(geom)) AS lon, name,
#             distance_sphere(StartPoint(geom), #{center}) AS dist
#      FROM osm_streets
#      WHERE geom && expand( #{center}::geometry, 0.003 )
#      UNION
#        (SELECT to_id AS label, Y(EndPoint(geom)) AS lat, X(EndPoint(geom)) AS lon, name,
#                distance_sphere(EndPoint(geom), #{center}) AS dist
#         FROM osm_streets
#         WHERE geom && expand( #{center}::geometry, 0.003 ))
#      ORDER BY dist LIMIT 1
#    SQL

    r = conn.exec(<<-SQL)[0]
      SELECT from_id AS label, Y(StartPoint(geom)) AS lat, X(StartPoint(geom)) AS lon, name,
             distance_sphere(StartPoint(geom), #{center}) AS dist_vertex,
             distance(geom, #{center}) AS dist_street
      FROM osm_streets
      WHERE geom && expand( #{center}::geometry, 0.003 )
      UNION
     (SELECT to_id AS label, Y(EndPoint(geom)) AS lat, X(EndPoint(geom)) AS lon, name,
             distance_sphere(EndPoint(geom), #{center}) AS dist_vertex,
             distance(geom, #{center}) AS dist_street
      FROM osm_streets
      WHERE geom && expand( #{center}::geometry, 0.003 ))
      ORDER BY dist_street, dist_vertex LIMIT 1
    SQL

    if r then
#      puts "label=#{label}, lat=#{lat}, lon=#{lon}, name=#{name}, dist=#{dist}"
      v['label'] = "osm#{r[0]}"
      v['lat'] = r[1]
      v['lon'] = r[2]
      v['name'] = r[3]
      v['dist'] = r[4]
      puts "label=#{v['label']}, lat=#{v['lat']}, lon=#{v['lon']}, name=#{v['name']}, dist=#{v['dist']}"
#    else
#      v = nil
    end

    return v
  end

end
