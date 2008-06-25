require "tiger"

class Street
  #takes an open database object; will not close it.
  def geom conn
    # This query is no longer correct nor useful
    res = conn.exec "SELECT AsBinary( geom ) FROM streets WHERE id='#{name}'"
    return res.get_value(0, 0)

    #rawcoords = res[0][0].unpack( "xx4x4d*" );
    #coords = []

    #while not rawcoords.empty?
    #  coords << [ rawcoords.shift, rawcoords.shift ]
    #end

    #return coords
  end
end


class Graphserver
  WGS84_LATLONG_EPSG = 4326
  TIGER_PREFIX = "tg"

  def load_tiger_from_db filename_base=nil
    #The value id is no longer necessary, could be omitted in the query
#   query = "SELECT id, from_id, to_id, length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]'), AsText(geom) FROM tiger_streets"
#   query = "SELECT id, from_id, to_id, name, length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]'), AsText(geom) FROM tiger_streets"
   query = "SELECT id, from_id, to_id, name, length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]'), AsText(geom), AsText(Reverse(geom)) FROM tiger_streets"
    query << "WHERE file = '#{filename_base}'" if filename_base

    res = conn.exec query

#    res.each do |id, from_id, to_id, length, geom|
#    res.each do |id, from_id, to_id, name, length, geom|
    res.each do |id, from_id, to_id, name, length, geom, rgeom|
      #In KML LineStrings have the spaces and the comas swapped with respect to postgis
      #We just substitute a space for a comma and viceversa
      geom.gsub!(" ","|")
      geom.gsub!(","," ")
      geom.gsub!("|",",")
      rgeom.gsub!(" ","|")
      rgeom.gsub!(","," ")
      rgeom.gsub!("|",",")
      #Also deletes the LINESTRING() envelope
      geom.gsub!("LINESTRING(","")
      geom.gsub!(")","")
      rgeom.gsub!("LINESTRING(","")
      rgeom.gsub!(")","")
      @gg.add_vertex( TIGER_PREFIX+from_id )
      @gg.add_vertex( TIGER_PREFIX+to_id )
      @gg.add_edge_geom( TIGER_PREFIX+from_id, TIGER_PREFIX+to_id, Street.new( name, Float(length) ),geom)
      @gg.add_edge_geom( TIGER_PREFIX+to_id, TIGER_PREFIX+from_id, Street.new( name, Float(length) ),rgeom)
    end
  end

  def load_tiger_from_file dir
    tiger_line = TigerLine::Dataset.new( dir )
    tiger_line.read

    tiger_line.each_feature do |feature|
      street_length = feature.length
      @gg.add_vertex( TIGER_PREFIX+feature.tzids )
      @gg.add_vertex( TIGER_PREFIX+feature.tzide )
      @gg.add_edge( TIGER_PREFIX+feature.tzids, TIGER_PREFIX+feature.tzide, Street.new( feature.tlid, street_length ) )
      @gg.add_edge( TIGER_PREFIX+feature.tzide, TIGER_PREFIX+feature.tzids, Street.new( feature.tlid, street_length ) )
    end
  end

  def remove_tiger_table!
    begin
      conn.exec "DROP TABLE tiger_streets"
    rescue
      nil
    end
  end

  def create_tiger_table!
    conn.exec <<-SQL
      CREATE TABLE tiger_streets (
      id          text,
      from_id     text,
      to_id       text,
      name        text,
      type        text,
      file        text
    )
    SQL

    conn.exec <<-SQL
      SELECT AddGeometryColumn( 'tiger_streets', 'geom', #{WGS84_LATLONG_EPSG}, 'LINESTRING', 2 )
    SQL

    conn.exec <<-SQL
      CREATE INDEX tiger_streets_id_idx ON tiger_streets ( id );
      CREATE INDEX tiger_streets_geom_idx ON tiger_streets USING GIST ( geom GIST_GEOMETRY_OPS );
    SQL
  end

  def consolidate_lines!
    res = conn.exec <<-SQL
      SELECT *
      FROM tiger_streets
      WHERE id IN( SELECT id
                   FROM tiger_streets st
                   GROUP BY id
                   HAVING count(*)>1 )
    SQL

    id_n = res.fieldnum( 'id' )

    res.each do |row|
      conn.exec "delete from tiger_streets where id='#{row[id_n]}'"
      #Uses regexp to substitute "'" by "''" to escape offending apostrophes. It might slow the process, but works
      conn.exec "insert into tiger_streets (#{res.fields.join(',')}) VALUES (#{row.map do |ii| "'"+ii.gsub(/'/,"''")+"'" end.join(',')})"
    end

  end

  def import_tiger_to_db! directory
    tiger_line = TigerLine::Dataset.new( directory )
    tiger_line.read

    conn.exec "COPY tiger_streets (id, from_id, to_id, name, type, file, geom ) FROM STDIN"
    name = nil
    tiger_line.each_feature do |feature|
      if feature.cfcc =~ /A\d\d/ then  #if the feature is a type of road
        if feature.names.length>0 then
          names = feature.names[0]
          name = "#{names[:fedirp]} #{names[:fename]} #{names[:fetype]} #{names[:fedirs]}".strip
        else
          name=""
        end
        conn.putline "#{feature.tlid}\t#{feature.tzids}\t#{feature.tzide}\t#{name}\t#{feature.cfcc}\t#{tiger_line.filename_base}\tSRID=#{WGS84_LATLONG_EPSG};#{feature.line_wkt}\n"
      end
    end
    conn.endcopy

    conn.exec "VACUUM ANALYZE tiger_streets"

    print "consolidating lines\n"
    consolidate_lines!

    conn.exec "VACUUM ANALYZE tiger_streets"
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
      FROM tiger_streets
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
      FROM tiger_streets,
      (SELECT line_interpolate_point('#{line_geom}', line_locate_point('#{line_geom}', #{center})) AS line_point) AS tpoint
      WHERE id = '#{line_id}'
      UNION
     (SELECT 'tg' || from_id AS label, Y(StartPoint(geom)) AS lat, X(StartPoint(geom)) AS lon, name,
             distance_sphere(StartPoint(geom), #{center}) AS dist_vertex
      FROM tiger_streets
      WHERE id = '#{line_id}'
      UNION
     (SELECT 'tg' || to_id AS label, Y(EndPoint(geom)) AS lat, X(EndPoint(geom)) AS lon, name,
             distance_sphere(EndPoint(geom), #{center}) AS dist_vertex
      FROM tiger_streets
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

end
