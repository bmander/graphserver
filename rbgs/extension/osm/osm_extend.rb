require 'rexml/document'
require "rexml/streamlistener"
require 'rubygems'
require 'json'

include REXML
include Math

# A class for modeling OSM nodes
class OSMNode
  attr_accessor :id, :lat, :lon, :tags

  def initialize id
    @id = id
    @tags = {} #A hash to store node tags
  end

end

# A class for modeling OSM ways
class OSMWay
  attr_accessor :id, :nodes, :tags

  def initialize id
    @id = id
    @nodes = [] # An array to store the node IDs that form a way
    @tags = {} #A hash to store way tags
  end

end


# Overrides Graphserver class to add OSMListener
class Graphserver
  WGS84_LATLONG_EPSG = 4326
  OSM_PREFIX = "osm" # Namespace of OSM data when loading the graph

  # Subclass OSMListener, parses an OSM file to feed the database and create the graph
  class OSMListener
    include StreamListener

    # Prepares the listener to parse a file
    def initialize graph, directional, connection, file, debug_level
      #general parsing variables
      @curr_obj = nil
      @directional = directional
      @file = file
      @debug_level = debug_level.to_i
      @ncount = 0
      @wcount = 0

      #graphserver-specific variables
      @nodes = {}
      @gg = graph
      @conn = connection

      #some class variables to avoid memory leaking caused by local data
      @query = ""
      @qcount = 0
      @type = ""
      @name = ""
      @geom = ""

    end

    # Subclass listener
    # A method that processes the start of an xml tag (i.e. <node lat="" lon="">)
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

    # Subclass listener
    # A method that processes the end of an xml tag (i.e. </node>)
    def tag_end name
      # Check the tag name
      case name
        when 'node'
          if @gg then
            handle_node @curr_obj
          else
            handle_node_db @curr_obj
          end
          @ncount += 1
          if @ncount%1000==0 then
            $stderr.print( sprintf("\rProcessed %d osm nodes", @ncount ) )
            STDOUT.flush
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
          @wcount += 1
          if @wcount%100==0 then
            $stderr.print( sprintf("\rProcessed %d osm ways", @wcount ) )
            STDOUT.flush
          end
        when 'osm'
          # End of file. Perform last query
          @conn.exec @query
      end

      # Check if @query stores a sufficient number of operations to query the db
      if @qcount>=100 then
        @conn.exec @query
        @query = ""
        @qcount = 0
      end

    end

    # Processes an OSM node in order to load the graph directly from a file
    # Adds the node to the graph and to a list of nodes,
    # to be processed by the handle_way method
    def handle_node node
      @gg.add_vertex( OSM_PREFIX+node.id )
      @nodes[node.id] = [node.lat, node.lon]
    end


    # Processes an OSM node in order to load the osm data to the database
    # If it is a routing node, adds the node to a list of nodes,
    # to be processed by the handle_way method
    # If it is a place node, adds the place to the database
    def handle_node_db node
      @nodes[node.id] = [node.lat, node.lon]
      # If the node is a place
      if node.tags['place'] then
        @type = "#{node.tags['place']}"
        @name = "#{node.tags['name'] || 'Unnamed'}".gsub(/'/,"''") #Substitute ' by '' for SQL queries
        @geom = "SRID=#{WGS84_LATLONG_EPSG};POINT(#{node.lon} #{node.lat})"
        # Import place to the DB
        @query << "insert into osm_places (id, type, name, location)"
        @query << " VALUES (\'#{node.id}\',\'#{@type}\',\'#{@name}\',\'#{@geom}\');\n"
        @qcount += 1
      end
    end


    # Processes an OSM way in order to load the graph directly from a file
    def handle_way way
      name = "#{way.tags['name'] || 'Unnamed'}"
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

          # Computes the length of the stretch by means of the Haversine formula
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
          @gg.add_edge_geom( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(name, len), geom)
          if @debug_level==2 then
            puts "added Edge( fromId=#{OSM_PREFIX+from_id}, toId=#{OSM_PREFIX+to_id}, length=#{len} )"
          end
          # Add reverse edge if not directional or not oneway
          if not @directional or not oneway then
            # Geometry of the reverse edge
            rgeom = "#{lon1},#{lat1} #{lon0},#{lat0}"
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


    # Processes an OSM way in order to load the osm data to the database
    def handle_way_db way

      @name = "#{way.tags['name'] || 'Unnamed'}".gsub(/'/,"''") #Substitute ' by '' for SQL queries
      @type = "#{way.tags['highway']}"
      #type = "#{way.tags['highway'] || way.tags['railway'] || way.tags['aerialway'] || way.tags['route'] || "Other"}"
      # If the oneway tag is not set or it is set to none, set oneway to false
      if not way.tags['oneway'] or way.tags['oneway']=='false' or way.tags['oneway']=='no' then
        oneway = false
      else
        oneway = true
      end

      # Puts the street in the osm_ways table
      @query << "insert into osm_ways (id, name, type, oneway, file)"
      @query << " VALUES (\'#{way.id}\',\'#{@name}\',\'#{@type}\',\'#{oneway}\',\'#{@file}\');\n"
      @qcount += 1

      ret = "LINESTRING("
      node_count = 0
      current = nil
      digits = Math.log10(way.nodes.length).ceil

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
          @geom = "SRID=#{WGS84_LATLONG_EPSG};LINESTRING(#{lon0} #{lat0},#{lon1} #{lat1})"
          @query << "insert into osm_segments (seg_id, id, from_id, to_id, geom ) "
          @query << "VALUES (\'#{way.id}-#{node_count.to_s.rjust(digits,'0')}\',"
          @query << "\'#{way.id}\',\'#{from_id}\',\'#{to_id}\',\'#{@geom}\');\n"
          @qcount += 1
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

  # Simplify the graph eliminating nodes that are not junctions
  def simplify_graph!
    puts "Querying database for simplifiable nodes"
    STDOUT.flush

    # Nodes that are eliminable
    nodes = conn.exec <<-SQL
       SELECT   t1.to_id
       FROM     osm_segments AS t1, osm_segments AS t2,
               (SELECT   t3.id
                FROM     (SELECT from_id AS id FROM osm_segments
                          UNION ALL
                          SELECT to_id AS id FROM osm_segments) AS t3
                GROUP BY t3.id
                HAVING   COUNT(t3.id) = 2) AS t4
       WHERE    t1.id = t2.id
       AND      t1.to_id = t4.id
       AND      t2.from_id = t4.id
       ORDER BY t1.seg_id
    SQL

    total = nodes.num_tuples
    puts "Detected #{total} simplifiable nodes"
    STDOUT.flush
    t0 = Time.now

    query = ""
    coords = ""
    count = 0
    target = 1000
    prev_seg = nil
    seg0 = nil
    seg1 = nil
    new_seg = []
    reg_exp_1 = /(\d|-).+\w/ # A regular expression to keep only the coordinates from the AsText
    reg_exp_2 = /,.+\w/ # A regular expression to keep only the coordinates from the AsText except the first tuple
    # Indexes of the columns of the response (hardcoded to run faster)
    seg_id_n = 0
    id_n = 1
    from_id_n = 2
    to_id_n = 3
    coords_n = 4

    # Query db for segments containing the eliminable nodes
    nodes.each do |node|
      count += 1
      if count%1000==0 then $stderr.print( sprintf("\rEliminated %d/%d osm nodes (%d%%)", count, total, (count.to_f/total)*100) ) end
      segments = conn.exec <<-SQL
        SELECT seg_id, id, from_id, to_id, AsText(geom) AS geom
        FROM osm_segments
        WHERE to_id = '#{node}' OR from_id = '#{node}'
        ORDER BY seg_id
      SQL

      # Each eliminable node should be part of only 2 segments
      #                   seg0 node seg1
      #                * ------> * ------> *

      seg0 = segments[0]
      seg1 = segments[1]

      # The whole idea is to eliminate several nodes in a row creating a new segment
      #   -Initial state (eliminable nodes 1, 2 and 3)
      #          node0 seg0 node1 seg1 node2 seg2 node3 seg3 node4
      #            * -------> * -------> * -------> * -------> *
      #   -Final state (after 4 SQL deletes and 1 SQL insert)
      #          node0                  seg0                 node4
      #            * ----------------------------------------> *

      # If it's the first node of the nodes query
      if (!prev_seg) then
        # Starts writing the first query
        # Adds sentences to the query to delete segments #0 and #1
        query << "delete from osm_segments where seg_id='#{seg0[seg_id_n]}';\n"
        query << "delete from osm_segments where seg_id='#{seg1[seg_id_n]}';\n"
        # Stores coordinates from segment #0 and #1
        seg0[coords_n] =~ reg_exp_1
        coords = $&
        seg1[coords_n] =~ reg_exp_2
        coords << $&
        # Assigns seg_id, id and from_id to new segment
        new_seg[seg_id_n] = seg0[seg_id_n]
        new_seg[id_n] = seg0[id_n]
        new_seg[from_id_n] = seg0[from_id_n]
      # If it's not the first node of the nodes query
      else
        # If the current node follows the last node in the same segment
        if (prev_seg[seg_id_n]==seg0[seg_id_n]) then
          # Continues the same query
          # Appends coordinates from segment #1
          seg1[coords_n] =~ reg_exp_2
          coords << $&
          # Adds sentence to the query to delete segment #1
          query << "delete from osm_segments where seg_id='#{seg1[seg_id_n]}';\n"
        else
          # Finish writing current query
          new_seg[to_id_n] = prev_seg[to_id_n]
          new_seg[coords_n] = "LINESTRING(#{coords})"
          query << "insert into osm_segments (seg_id, id, from_id, to_id, geom)"
          query << " VALUES (\'#{new_seg[seg_id_n]}\',\'#{new_seg[id_n]}\',"
          query << "\'#{new_seg[from_id_n]}\',\'#{new_seg[to_id_n]}\',"
          query << "GeomFromText(\'#{new_seg[coords_n]}\',4326));\n"
          # Executes query in blocks of 1000 or more lines
          if (count > target) then
            conn.exec query
            # Clears query and start writing a new one
            query = ""
            target += 1000
          end
          # Adds sentences to the query to delete segments #0 and #1
          query << "delete from osm_segments where seg_id='#{seg0[seg_id_n]}';\n"
          query << "delete from osm_segments where seg_id='#{seg1[seg_id_n]}';\n"
          # Stores coordinates from segment #0 and #1
          seg0[coords_n] =~ reg_exp_1
          coords = $&
          seg1[coords_n] =~ reg_exp_2
          coords << $&
          # Assigns seg_id, id and from_id to new segment
          new_seg[seg_id_n] = seg0[seg_id_n]
          new_seg[id_n] = seg0[id_n]
          new_seg[from_id_n] = seg0[from_id_n]
        end

      end
      prev_seg = seg1
    end
    # Finishes last query
    new_seg[to_id_n] = prev_seg[to_id_n]
    new_seg[coords_n] = "LINESTRING(#{coords})"
    query << "insert into osm_segments (seg_id, id, from_id, to_id, geom)"
    query << " VALUES (\'#{new_seg[seg_id_n]}\',\'#{new_seg[id_n]}\',"
    query << "\'#{new_seg[from_id_n]}\',\'#{new_seg[to_id_n]}\',"
    query << "GeomFromText(\'#{new_seg[coords_n]}\',4326));\n"
    conn.exec query

    t1 = Time.now
    puts "Graph simplification accomplished in #{t1-t0} sec"
  end


  # Create osm tables in the db
  def create_osm_table!
    # Create a table to store osm ways
    puts "Creating osm_ways table..."
    conn.exec <<-SQL
      CREATE TABLE osm_ways (
      id          text PRIMARY KEY,
      name        text,
      type        text,
      oneway      text,
      file        text
    )
    SQL

    # Create a table to store osm segments
    puts "Creating osm_segments table..."
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

    # Create a view to match osm_ways and osm_segments in a single table
    puts "Creating osm_streets view..."
    conn.exec <<-SQL
      CREATE OR REPLACE VIEW osm_streets AS
--      SELECT osm1.id, osm2.from_id, osm2.to_id, osm1.name, osm1."type", osm1.oneway, osm2.geom, osm1.file
      SELECT osm2.seg_id, osm2.id, osm2.from_id, osm2.to_id, osm1.name, osm1."type", osm1.oneway, osm2.geom, osm1.file
      FROM osm_ways osm1, osm_segments osm2
      WHERE osm1.id = osm2.id;
    SQL

    # Create a table to store places in order to implement the geocoder
    puts "Creating osm_places table..."
    conn.exec <<-SQL
      CREATE TABLE osm_places (
      id          text PRIMARY KEY,
      type        text,
      name        text
    )
    SQL

    conn.exec <<-SQL
      SELECT AddGeometryColumn( 'osm_places', 'location', #{WGS84_LATLONG_EPSG}, 'POINT', 2 )
    SQL

    # Create the necessary indexes to speed up the database access
    # These indexes are related to the most frequent and time consuming
    # SQL 'where' clauses used in this extension
    puts "Creating indexes..."
    conn.exec <<-SQL
--      CREATE INDEX osm_ways_id_idx ON osm_ways ( id );
      CREATE INDEX osm_segments_id_idx ON osm_segments ( id );
      CREATE INDEX osm_segments_seg_id_idx ON osm_segments ( seg_id );
--      CREATE INDEX osm_segments_node_idx ON osm_segments ( from_id, to_id );
      CREATE INDEX osm_segments_from_id_idx ON osm_segments ( from_id );
      CREATE INDEX osm_segments_to_id_idx ON osm_segments ( to_id );
      CREATE INDEX osm_segments_geom_idx ON osm_segments USING GIST ( geom GIST_GEOMETRY_OPS );
      CREATE INDEX osm_places_idx ON osm_places USING GIST ( location GIST_GEOMETRY_OPS );
    SQL
  end

  # Removes osm tables from the db
  def remove_osm_table!
    begin
      puts "Removing osm_streets view..."
      conn.exec "DROP VIEW osm_streets"
      puts "Removing osm_segments table..."
      conn.exec "DROP TABLE osm_segments"
      puts "Removing osm_ways table..."
      conn.exec "DROP TABLE osm_ways"
      puts "Removing osm_places table..."
      conn.exec "DROP TABLE osm_places"
    rescue
      nil
    end
  end

  # Imports an osm file to the db
  def import_osm_to_db! file, debug_level=0
    puts "Importing #{file} to the database..."

    list = OSMListener.new nil, nil, conn, file, debug_level
    source = File.new file, "r"
    REXML::Document.parse_stream(source, list)

#    puts "consolidating lines\n"
#    consolidate_lines!
    conn.exec "VACUUM ANALYZE osm_ways"
    conn.exec "VACUUM ANALYZE osm_segments"
    conn.exec "VACUUM ANALYZE osm_places"
  end


  # Builds the graph from the osm tables in the db
  def load_osm_from_db file=nil, directional=false
    query = "SELECT id, from_id, to_id, name, type, oneway, "
    query << "length_spheroid(geom, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]'), "
    query << "AsText(geom), AsText(Reverse(geom))"
    query << "FROM osm_streets "
    query << "WHERE file = '#{file}'" if file

    res = conn.exec query
    total = res.num_tuples
    count = 0


    res.each do |id, from_id, to_id, name, type, oneway, length, coords, rcoords|
      count += 1
      if count%1000==0 then $stderr.print( sprintf("\rProcessed %d/%d osm segments (%d%%)", count, total, (count.to_f/total)*100) ) end
      #In KML LineStrings have the spaces and the comas swapped with respect to postgis
      #We just substitute a space for a comma and viceversa
      coords.gsub!(/[ ,()A-Z]/) {|s| if (s==' ') then ',' else if (s==',') then ' ' end end}
      rcoords.gsub!(/[ ,()A-Z]/) {|s| if (s==' ') then ',' else if (s==',') then ' ' end end}
      @gg.add_vertex( OSM_PREFIX+from_id )
      @gg.add_vertex( OSM_PREFIX+to_id )
      @gg.add_edge_geom( OSM_PREFIX+from_id, OSM_PREFIX+to_id, Street.new(name, Float(length)), coords )
      if not directional or oneway=="false"
        @gg.add_edge_geom( OSM_PREFIX+to_id, OSM_PREFIX+from_id, Street.new(name, Float(length)), rcoords )
      end

    end
  end

  # Builds the graph from an osm file
  def load_osm_from_file file, directional=false, debug_level=0

    # Creates an OSMListener instance which parses the osm file and builds the graph
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

    # Looks for the closest street vertex in a radius of approximately 500m from the center
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

    # An array of vertices
    v = []
    i = 0
    # Each vertex is a hash of properties
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
  def get_vertices_from_address(address)
    # If there's a comma in the address string, separate direction and place
    if address.count(',') > 0 then
      address = address.split(',')
      add_dir = address[0]
      add_place = address[1]
    else
      add_dir = address
      add_place = nil
    end

    # If the direction field is too short the db queries wouldn't have sense
    if add_dir.length < 3 then return nil end

    # Query db for ways that match the address
    ways = conn.exec <<-SQL
      SELECT name, id
      FROM osm_ways
      WHERE LOWER(name) LIKE '%#{add_dir.downcase}%'
      ORDER BY name
      LIMIT 10
    SQL

    if ways.num_tuples == 0 then return nil end

    # An array of vertices
    v = []
    i = 0

    # Query db for the nearest place to each matched way
    ways.each do |name, id|
      vertex = conn.exec(<<-SQL)[0]
        SELECT 'osm' || t1.from_id AS label,
               Y(StartPoint(t1.geom)) AS lat, X(StartPoint(t1.geom)) AS lon,
               distance_sphere(StartPoint(t1.geom), t2.location) AS dist_place, t2.name
        FROM osm_segments AS t1, osm_places AS t2
        WHERE t1.id = '#{id}'
        ORDER BY dist_place
        LIMIT 1
      SQL

      # If no place was specified or the given place matches the nearest place
      if add_place == nil or add_place.downcase == vertex[4].downcase then
        v[i]={}
        v[i]['label'] = vertex[0] #Label of the vertex
        v[i]['lat'] = vertex[1] #Latitude of the vertex
        v[i]['lon'] = vertex[2] #Longitude of the vertex
        v[i]['name'] = name #Name of the closest edge to the vertex
        v[i]['dist'] = vertex[3] #Distance from the vertex to the nearest place
        v[i]['place'] = vertex[4] #Name of the nearest place
        i += 1
      end
    end

    return v
  end

end
