require "tiger"

class Street
  #takes an open database object; will not close it.
  def geom conn
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
    query = "SELECT id, from_id, to_id, length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]') FROM tiger_streets"
    query << "WHERE file = '#{filename_base}'" if filename_base

    res = conn.exec query

    res.each do |id, from_id, to_id, length|
      @gg.add_vertex( TIGER_PREFIX+from_id )
      @gg.add_vertex( TIGER_PREFIX+to_id )
      @gg.add_edge( TIGER_PREFIX+from_id, TIGER_PREFIX+to_id, Street.new( id, Float(length) ) )
      @gg.add_edge( TIGER_PREFIX+to_id, TIGER_PREFIX+from_id, Street.new( id, Float(length) ) )
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
#        name = "#{feature.fedirp} #{feature.fename} #{feature.fetype} #{feature.fedirs}".strip
        conn.putline "#{feature.tlid}\t#{feature.tzids}\t#{feature.tzide}\t#{name}\t#{feature.cfcc}\t#{tiger_line.filename_base}\tSRID=#{WGS84_LATLONG_EPSG};#{feature.line_wkt}\n"
      end
    end
    conn.endcopy

    conn.exec "VACUUM ANALYZE tiger_streets"

    print "consolidating lines\n"
    consolidate_lines!

    conn.exec "VACUUM ANALYZE tiger_streets"
  end

end
