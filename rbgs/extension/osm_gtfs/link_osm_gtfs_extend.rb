class Graphserver
  OSM_LINK_SEARCH_RANGE = 100 #meters
  WGS84_LATLONG_EPSG = 4326

  # A method to process a block for each stop,
  # using stop_id and location as parameters for the block
  def each_stop
    stops = conn.exec "SELECT stop_id, location FROM gtf_stops"
    stops.each do |stop_id, location|
      yield stop_id, location
    end
  end

  # Looks for the nearest node in the nearest segment
  # and creates the links in the osm_gtfs_links table
  def link_stop! (stop_id, stop_geom, search_range)
    #Looks for the nearest segment
    ret = conn.exec <<-SQL
      SELECT seg_id, from_id, to_id, geom, distance(geom, '#{stop_geom}') AS dist
      FROM osm_segments
      WHERE geom && expand( '#{stop_geom}'::geometry, #{search_range} )
      ORDER BY dist
      LIMIT 1
    SQL

    # If no segments where found in the search range return nil
    if ret.num_tuples == 0 then return nil end

    # Extract values from the query
    # The coordinates are filtered from the AsText clause which contains 'LINESTRING(...)'
    seg_id = ret[0][0]
    from_id = ret[0][1]
    to_id = ret[0][2]
    seg_geom = ret[0][3]

    # Splits segment in the nearest point to the stop
    ret = conn.exec("SELECT line_locate_point('#{seg_geom}', '#{stop_geom}'), AsText('#{stop_geom}')")
    split = ret[0][0].to_f
    stop_coords = ret[0][1].gsub(/[()A-Z]/,'')

    # Check if the splitted left segment's size is = 0 and inserts it into the database
    if (split == 0.0) then
      # Connects only with the left (shortest) side
      l_coords = conn.exec("SELECT AsText(StartPoint('#{seg_geom}'))").getvalue(0,0)
      l_coords = l_coords.gsub(/[()A-Z]/,'')
      # Connects the left segment with the stop
      coords1 = []
      coords1 << stop_coords
      coords1 << l_coords
      query = "INSERT INTO osm_gtfs_links (stop_id, node_id, geom) VALUES ('#{stop_id}', '#{from_id}', GeomFromText('LINESTRING(#{coords1.join(',')})',4326))"
      conn.exec query
    end
    # Check if the splitted right segment's size is = 0 and inserts it into the database
    if (split == 1.0) then
      # Connects only with the right (shortest) side
      r_coords = conn.exec("SELECT AsText(EndPoint('#{seg_geom}'))").getvalue(0,0)
      r_coords = r_coords.gsub(/[()A-Z]/,'')
      # Connects the right segment with the stop
      coords2 = []
      coords2 << stop_coords
      coords2 << r_coords
      query = "INSERT INTO osm_gtfs_links (stop_id, node_id, geom) VALUES ('#{stop_id}', '#{to_id}', GeomFromText('LINESTRING(#{coords2.join(',')})',4326))"
      conn.exec query
    end
    # If both splitted segment's size are > 0, then inserts them into the database
    if ((split > 0.0) and (split < 1.0)) then
      l_coords = conn.exec("SELECT AsText(line_substring('#{seg_geom}', 0, #{split}))").getvalue(0,0)
      l_coords = l_coords.gsub(/[()A-Z]/,'').split(',')
      r_coords = conn.exec("SELECT AsText(line_substring('#{seg_geom}', #{split}, 1))").getvalue(0,0)
      r_coords = r_coords.gsub(/[()A-Z]/,'').split(',')
      # Connects the left segment with the stop and reorders it
      coords1 = []
      coords1 << stop_coords
      coords1 << l_coords.reverse
      query = "INSERT INTO osm_gtfs_links (stop_id, node_id, geom) VALUES ('#{stop_id}', '#{from_id}', GeomFromText('LINESTRING(#{coords1.join(',')})',4326))"
      conn.exec query
      # Connects the right segment with the stop, no need to reorder in that case
      coords2 = []
      coords2 << stop_coords
      coords2 << r_coords
      query = "INSERT INTO osm_gtfs_links (stop_id, node_id, geom) VALUES ('#{stop_id}', '#{to_id}', GeomFromText('LINESTRING(#{coords2.join(',')})',4326))"
      conn.exec query
    end
    return true
  end

  # Tries to link all gtfs stops to osm nodes,
  # reporting the number of linked stops
  def link_osm_gtfs!(search_range=OSM_LINK_SEARCH_RANGE)
    puts "Search range = #{search_range} meters"
    # Converts approximately from meters to degrees
    search_range = search_range.to_f / (6371000*(Math::PI/180))
    count = 0
    total = conn.exec("SELECT COUNT(*) FROM gtf_stops").getvalue(0,0)
    stops_linked = 0
    stops_isolated = 0
    isolated = []
    each_stop do |stop_id, stop_geom|
      count += 1
      if count%1000==0 then $stderr.print( sprintf("\rProcessed %d/%d gtfs stops (%d%%)", count, total, (count.to_f/total)*100) ) end
      if (link_stop!(stop_id, stop_geom, search_range) ) then
        stops_linked += 1
      else
        stops_isolated += 1
        isolated << stop_id
      end
    end

    # Vacuum analyze table
    conn.exec "VACUUM ANALYZE osm_gtfs_links"
    # Report linked stops
    puts "Linked #{stops_linked}/#{total} stops."
    if (stops_isolated > 0) then
      puts "Remaining #{stops_isolated} without link."
      puts "Isolated stops:"
      isolated.each do |stop_id| puts stop_id end
      return isolated
    end
    # If everything's ok returns nil
    return nil
  end

  # Removes link table between osm and gtfs
  def remove_link_table!
    begin
      conn.exec "DROP TABLE osm_gtfs_links"
    rescue
      nil
    end
  end

  # Creates link table between osm and gtfs
  def create_link_table!
    #an extremely simple join table
    conn.exec <<-SQL
      create table osm_gtfs_links (
        stop_id            text NOT NULL,
        node_id            text NOT NULL
      );

      select AddGeometryColumn( 'osm_gtfs_links', 'geom', #{WGS84_LATLONG_EPSG}, 'LINESTRING', 2 );
    SQL
  end

  # Loads into the graph the links between osm and gtfs
  def load_osm_gtfs_links
    res = conn.exec "SELECT stop_id, node_id, AsText(geom), AsText(Reverse(geom)) FROM osm_gtfs_links"
    res.each do |stop_id, node_id, coords, rcoords|
      # In KML LineStrings have the spaces and the comas swapped with respect to postgis
      # We just substitute a space for a comma and viceversa
      coords.gsub!(/[ ,()A-Z]/) {|s| if (s==' ') then ',' else if (s==',') then ' ' end end}
      rcoords.gsub!(/[ ,()A-Z]/) {|s| if (s==' ') then ',' else if (s==',') then ' ' end end}
      # Add edges to the graph, both from the stop to the node and viceversa
      @gg.add_edge_geom( GTFS_PREFIX+stop_id, OSM_PREFIX+node_id, Link.new, coords )
      @gg.add_edge_geom( OSM_PREFIX+node_id, GTFS_PREFIX+stop_id, Link.new, rcoords )
    end
  end
end
