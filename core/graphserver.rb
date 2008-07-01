require 'webrick'
#require 'xmlrpc/server.rb'
# Required to provide the core as well as functions shortest_path and shortest_path_retro
require 'graph.rb'
# Required to process command line parameters
require 'optparse'
require 'cgi'

#Overrides class Calendar to add to_xml function
class Calendar
  def to_xml
    "<calendar begin_time='#{Time.at(begin_time)}' end_time='#{Time.at(end_time)}' service_ids='#{service_ids.join(", ")}' />"
  end
end

#made a different change over here

#Overrides class Link to add to_xml function
class Link
  def to_xml
    "<link/>"
  end
end

#Overrides class Street to add to_xml function
class Street
  def to_xml
    "<street name='#{name}' length='#{length}' />"
  end
end

#Overrides class TripHopSchedule to add to_xml function
class TripHopSchedule
  def to_xml
    ret = ["<triphopschedule service_id='#{service_id}'>"]
    #Para cada triphop inserta su transformacion a xml
    triphops.each do |triphop|
      ret << triphop.to_xml
    end
    ret << "</triphopschedule>"

    return ret.join
  end
end

#Overrides class TripHop to add to_xml function
class TripHop
  SEC_IN_HOUR = 3600
  SEC_IN_MINUTE = 60

  def to_xml
    s_depart = "#{sprintf("%02d", depart/SEC_IN_HOUR)}:#{sprintf("%02d", (depart%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", depart%SEC_IN_MINUTE)}"
    s_arrive = "#{sprintf("%02d", arrive/SEC_IN_HOUR)}:#{sprintf("%02d", (arrive%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", arrive%SEC_IN_MINUTE)}"
    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' />"
  end
end

#Overrides class State to add to_xml function
class State
  def to_xml
    #Abre la cabecera del elemento state
    ret = "<state "
    #Insercion de atributos. Convierte la instancia de State
    #en un hash y, para cada pareja clave-valor
    self.to_hash.each_pair do |name, value|
      if name == "time" then #TODO kludge alert
        #Si la clave es "time", inserta "time='value'"
        #formateando value como tiempo
        ret << "time='#{Time.at( value ).inspect}' "
      else
        #En caso contrario escrive "name='value'"
        #a menos que el objeto value posea un método to_xml
        ret << "#{name}='#{CGI.escape(value.to_s)}' " unless value.public_methods.include? "to_xml"
      end
    end
    #Cierra la cabecera del elemento state
    ret << ">"

    #Insercion de subelementos. Para cada par clave-valor
    #que tenga un metodo to_xml, inserta el resultado de to_xml
    self.to_hash.each_pair do |name, value|
      ret << value.to_xml if value.public_methods.include? "to_xml"
    end

    #Cierra el elemento state, en este caso ya es un String
    #y no necesita convertir de Array a String con join
    ret << "</state>"
  end
end

#Overrides class Vertex to add to_xml function
class Vertex
  def to_xml
    ret = ["<vertex label='#{label}'>"]
    #La siguiente instruccion es una comparacion del resultado
    #de una asignacion (= en lugar de ==)
    #Si el objeto Vertex tiene payload lo transforma a xml
    if pl=payload then #to avoid calling payload twice. instantiating a variable may actually be more expensive.
      ret << pl.to_xml
    end
    ret << "</vertex>"
    return ret.join
  end
end

#Overrides class Edge to add to_xml function
class Edge
  def to_xml verbose=true
    if geom=="" then ret = "<edge>"
    else ret = "<edge geom='#{geom}'>"
    end
    #Si verbose=true inserta el payload transformado a xml
    ret << payload.to_xml if verbose
    ret << "</edge>"
  end
end

# A hash with default program options
OPTIONS = { :port => 3003 }

# A hash with default database parameters
DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => 'postgres', #database username
              :password => 'postgres' }

#Process command input parameters
ARGV.options do |opts|
  # Gets the name of the calling script, i.e. setup_gtfs_tables
  script_name = File.basename($0)
  opts.banner = "Usage: ruby #{script_name} [options]"

  opts.separator ""

  #If the option -p or --port is found
  opts.on("-p", "--port=port", Integer,
          "Runs Rails on the specified port.",
          "Default: 3003") { |v| OPTIONS[:port] = v }

  #If the option -d or --dbname is found
  opts.on("-d", "--dbname=dbname", String,
          "Specifies database name.",
          "Default: graphserver") { |v| DB_PARAMS[:dbname] = v }

  #If the option -u or --username is found
  opts.on("-u", "--username=username", String,
          "Specifies database username.",
          "Default: postgres") { |v| DB_PARAMS[:login] = v }

  #If the option -w or --password is found
  opts.on("-w", "--password=password", String,
          "Specifies database password.",
          "Default: postgres") { |v| DB_PARAMS[:password] = v }

  #If the option -h or --help is found, shows a help message
  opts.on("-h", "--help",
          "Show this help message.") { puts opts; exit }

  # Parse parameters in order
  opts.parse!
end

class Graphserver
  # Make the graph public
  attr_reader :gg

  #Extracts the 'time' parameter from the GET request
  #If it doesn't exist, takes the current time
  def parse_init_state request
    State.new( (request.query['time'] or Time.now) ) #breaks without the extra parens
  end

  #Extracts the 'format' parameter from the GET request
  #If it doesn't exist, uses xml as default
  def parse_format request
    (request.query['format'] or "xml") #breaks without the extra parens
  end

  #Funcion llamada al hacer Graphserver.new
  def initialize
    #Crea el grafo de clase Graph
    @gg = Graph.create #horrible hack

    #Lanza el servidor en el puerto :port (digo yo)
    @server = WEBrick::HTTPServer.new(:Port => OPTIONS[:port])

    #Response to GET request "/"
    @server.mount_proc( "/" ) do |request, response|
      #Presents all possible requests to graphserver
      ret = ["Graphserver Web API"]
      ret << "shortest_path?from=FROM&to=TO"
      ret << "all_vertex_labels"
      ret << "outgoing_edges?label=LABEL"
      ret << "walk_edges?label=LABEL&statevar1=STV1&statevar2=STV2..."
      ret << "collapse_edges?label=LABEL&statevar1=STV1&statevar2=STV2..."
      ret << "vertices_from_coords?lat=LAT&lon=LON"
      ret << "vertices_from_address?add=ADDRESS"
      ret << "stops_from_coords?lat=LAT&lon=LON"
      ret << "keep_alive"
      ret << "dot"
      response.body = ret.join("\n")
    end

    @server.mount_proc("/dot") do |request, response|
      begin
        response.body=@gg.to_dot
      end
    end

    #Response to request GET "/keep_alive"
    @server.mount_proc( "/keep_alive" ) do |request, response|
      ret = []
      ret << "Size of graph: #{@gg.vertices.count} vertices"
      ret << "First vertex: #{@gg.vertices.first.label}"
      ret << "Last vertex: #{@gg.vertices.last.label}"
      response.body = ret.join
    end

    #Response to GET request "/shortest_path"
    @server.mount_proc( "/shortest_path" ) do |request, response|
      #Read input parameters
      from = request.query['from']
      to = request.query['to']
      format = parse_format( request )
      init_state = parse_init_state( request )
      ret = []

      #This block check input parameters and calls for the right shortest path algorithm
      #depending on the parameters or generates Errors if these parameters are wrong
      begin
        #If input parameters are coordinates
        if from.count(',')==1 or to.count(',')==1 then
          if from.count(',')==1 and to.count(',')==1 then
            #If both input parameters are a pair of coordinates
            coords0 = from.split(',')
            coords1 = to.split(',')
            puts "origin lat0=#{coords0[0]} lon0=#{coords0[1]}"
            puts "destination lat1=#{coords1[0]} lon1=#{coords1[1]}"
            lat0 = coords0[0]
            lon0 = coords0[1]
            lat1 = coords1[0]
            lon1 = coords1[1]

            #Looks for the 2 closest vertices from the closest edge
            #and the closest point in the edge
            v0 = get_closest_edge_vertices(lat0, lon0)
            v1 = get_closest_edge_vertices(lat1, lon1)

            #Time stamp to differentiate requests. It's necessary as long
            #as we don't delete the nodes after the shortest path calculation
            ts = Time.now

            #If vertices are returned as expected
            if (v0 and v1) then
              #Adds a new vertex in the closest point in the edge
              #and in the origin point and connects them
              @gg.add_vertex( "origin_#{ts}" )
              @gg.add_vertex( "destination_#{ts}" )
              coords01 = "#{lon0},#{lat0} #{v0[0]['lon']},#{v0[0]['lat']} #{v0[1]['lon']},#{v0[1]['lat']}"
              coords02 = "#{lon0},#{lat0} #{v0[0]['lon']},#{v0[0]['lat']} #{v0[2]['lon']},#{v0[2]['lat']}"
              coords11 = "#{lon1},#{lat1} #{v1[0]['lon']},#{v1[0]['lat']} #{v1[1]['lon']},#{v1[1]['lat']}"
              coords12 = "#{lon1},#{lat1} #{v1[0]['lon']},#{v1[0]['lat']} #{v1[2]['lon']},#{v1[2]['lat']}"
              @gg.add_edge_geom( "origin_#{ts}", v0[1]['label'], Link.new, coords01)
              @gg.add_edge_geom( "origin_#{ts}", v0[2]['label'], Link.new, coords02)
              @gg.add_edge_geom( v1[1]['label'], "destination_#{ts}", Link.new, coords11)
              @gg.add_edge_geom( v1[2]['label'], "destination_#{ts}", Link.new, coords12)
            else
              #If no vertices are returned then probably the GS has not street data
              #In that case we look for the 2 closest stops
              s0 = get_closest_stops(lat0, lon0, 2)
              s1 = get_closest_stops(lat1, lon1, 2)

              #Adds a new vertex in the closest point in the edge
              #and in the origin point and connects them
              @gg.add_vertex( "origin_#{ts}" )
              @gg.add_vertex( "destination_#{ts}" )
              coords01 = "#{lon0},#{lat0} #{s0[0]['lon']},#{s0[0]['lat']}"
              coords02 = "#{lon0},#{lat0} #{s0[1]['lon']},#{s0[1]['lat']}"
              coords11 = "#{lon1},#{lat1} #{s1[0]['lon']},#{s1[0]['lat']}"
              coords12 = "#{lon1},#{lat1} #{s1[1]['lon']},#{s1[1]['lat']}"
#              puts "new edge( origin_#{ts}, #{s0[0]['label']})"
#              puts "new edge( origin_#{ts}, #{s0[1]['label']})"
#              puts "new edge( #{s1[0]['label']}, destination_#{ts})"
#              puts "new edge( #{s1[1]['label']}, destination_#{ts})"
              @gg.add_edge_geom( "origin_#{ts}", s0[0]['label'], Link.new, coords01)
              @gg.add_edge_geom( "origin_#{ts}", s0[1]['label'], Link.new, coords02)
              @gg.add_edge_geom( s1[0]['label'], "destination_#{ts}", Link.new, coords11)
              @gg.add_edge_geom( s1[1]['label'], "destination_#{ts}", Link.new, coords12)
            end

            #Calculates the shortest path
            vertices, edges = @gg.shortest_path("origin_#{ts}", "destination_#{ts}", init_state )      #Throws RuntimeError if no shortest path found.
            ret << ( format_shortest_path vertices, edges, format )
          else
            #If only one input parameter is a pair of coordinates
            raise ArgumentError
          end
        else
          #If input parameters are vertex labels
          #Checks that both from and to parameters exist, generates an exception elsewhere
          unless @gg.get_vertex(from) and @gg.get_vertex(to) then raise ArgumentError end

          #Calculates the shortest path
          vertices, edges = @gg.shortest_path(from, to, init_state )      #Throws RuntimeError if no shortest path found.
          ret << ( format_shortest_path vertices, edges, format )
        end

        #Catch alike sentence for RuntimeError
        rescue RuntimeError                                               #TODO: change exception type, RuntimeError is too vague.
          ret << "Couldn't find a shortest path from #{from} to #{to}"
        #Catch alike sentence for ArgumentError
        rescue ArgumentError
          ret << "ERROR: Invalid parameters."
      end

      response.body = ret.join
    end

    #Response to request GET "/all_vertex_labels"
    @server.mount_proc( "/all_vertex_labels" ) do |request, response|
      vlabels = []
      vlabels << "<?xml version='1.0'?>"
      vlabels << "<labels>"
      @gg.vertices.each do |vertex|
        #Para cada vertice escribe su etiqueta
        vlabels << "<label>#{vertex.label}</label>"
      end
      vlabels << "</labels>"
      response.body = vlabels.join
    end

    #Response to request GET "/outgoing_edges"
    @server.mount_proc( "/outgoing_edges" ) do |request, response|
      ret = []

      begin
        #Busca vertice asociado al parametro 'label'
        #Si no existe, genera una excepcion de parametros invalidos
        unless vertex = @gg.get_vertex( request.query['label'] ) then raise ArgumentError end
#      vertex = @gg.get_vertex( request.query['label'] )
        ret << "<?xml version='1.0'?>"
        ret << "<edges>"
        vertex.each_outgoing do |edge|
          ret << "<edge>"
          ret << "<dest>#{edge.to.to_xml}</dest>"
          ret << "<payload>#{edge.payload.to_xml}</payload>"
          ret << "</edge>"
        end
        ret << "</edges>"

        #Catch alike sentence
        rescue ArgumentError
          ret << "ERROR: Invalid parameters."
      end

      response.body = ret.join
    end

    #Response to GET request "/walk_edges"
    @server.mount_proc( "/walk_edges" ) do |request, response|
      ret = []
      begin
        #Busca vertice asociado al parametro 'label'
        #Si no existe, genera una excepcion de parametros invalidos
        unless vertex = @gg.get_vertex( request.query['label'] ) then raise ArgumentError end
        #Obtiene el parametro 'time' de la peticion GET o lo genera automaticamente
        init_state = parse_init_state( request )

        ret << "<?xml version='1.0'?>"
        ret << "<vertex>"
        ret << init_state.to_xml
        ret << "<outgoing_edges>"
        vertex.each_outgoing do |edge|
          ret << "<edge>"
          ret <<   "<destination label='#{edge.to.label}'>"
          if collapsed = edge.payload.collapse( init_state ) then
            ret << collapsed.walk( init_state ).to_xml
          else
            ret << "<state/>"
          end
          ret <<   "</destination>"
          if collapsed then
            ret << "<payload>#{collapsed.to_xml}</payload>"
          else
            ret << "<payload/>"
          end
          ret << "</edge>"
        end
        ret << "</outgoing_edges>"
        ret << "</vertex>"

        #Catch alike sentence
        rescue ArgumentError
          ret << "ERROR: Invalid parameters."
      end

      response.body = ret.join
    end

    #Response to GET request "/collapse_edges"
    @server.mount_proc( "/collapse_edges" ) do |request, response|
      vertex = @gg.get_vertex( request.query['label'] )
      init_state = parse_init_state( request )

      ret = ["<?xml version='1.0'?>"]
      ret << "<vertex>"
      ret << init_state.to_xml
      ret << "<outgoing_edges>"
      vertex.each_outgoing do |edge|
        ret << "<edge>"
        ret << "<destination label='#{edge.to.label}' />"
        if collapsed = edge.payload.collapse( init_state ) then
          ret << "<payload>#{collapsed.to_xml}</payload>"
        else
          ret << "<payload/>"
        end
        ret << "</edge>"
      end
      ret << "</outgoing_edges>"
      ret << "</vertex>"

      response.body = ret.join
    end

    #Response to GET request "/vertices_from_coords"
    @server.mount_proc( "/vertices_from_coords" ) do |request, response|
      begin
        #Check input parameters are present
        unless lat = request.query['lat'] then raise ArgumentError end
        unless lon = request.query['lon'] then raise ArgumentError end

        v = get_closest_edge_vertices(lat, lon)
#        v = get_vertex_from_coords(lat, lon)

        if v == nil then
          ret = ["ERROR: function not implemented by any extension"]
        else
          ret = ["<?xml version='1.0'?>"]
          ret << "<vertices>"
          v.each do |vv|
            ret << "<vertex>"
            if vv['label'] then
              ret << "<label>#{vv['label']}</label>"
              ret << "<lat>#{vv['lat']}</lat>"
              ret << "<lon>#{vv['lon']}</lon>"
              ret << "<name>#{vv['name']}</name>"
              ret << "<dist>#{vv['dist']}</dist>"
            end
            ret << "</vertex>"
          end
          ret << "</vertices>"
        end

        #Catch alike sentence
        rescue ArgumentError
          ret = ["ERROR: Invalid parameters."]
      end
      response.body = ret.join
    end

    #Response to GET request "/vertex_from_address"
    @server.mount_proc( "/vertices_from_address" ) do |request, response|
      begin
        unless add = request.query['add'] then raise ArgumentError end

        ret = ["<?xml version='1.0'?>"]
        ret << "<vertex>"
        ret << "</vertex>"

        #Catch alike sentence
        rescue ArgumentError
          ret = ["ERROR: Invalid parameters."]
      end
      response.body = ret.join
    end

    #Response to GET request "/stops_from_coords"
    @server.mount_proc( "/stops_from_coords" ) do |request, response|
      begin
        #Check input parameters are present
        unless lat = request.query['lat'] then raise ArgumentError end
        unless lon = request.query['lon'] then raise ArgumentError end

        v = get_closest_stops(lat, lon, 10)

        if v == nil then
          ret = ["ERROR: function not implemented by any extension"]
        else
          ret = ["<?xml version='1.0'?>"]
          ret << "<stops>"
          v.each do |vv|
            ret << "<stop>"
            if vv['label'] then
              ret << "<label>#{vv['label']}</label>"
              ret << "<lat>#{vv['lat']}</lat>"
              ret << "<lon>#{vv['lon']}</lon>"
              ret << "<dist>#{vv['dist']}</dist>"
            end
            ret << "</stop>"
          end
          ret << "</stops>"
        end

        #Catch alike sentence
        rescue ArgumentError
          ret = ["ERROR: Invalid parameters."]
      end
      response.body = ret.join
    end

  end

  #Formats a shortest path response depending on the format parameter
  def format_shortest_path vertices, edges, format
    ret = []
    if format == "xml" then
      ret << "<?xml version='1.0'?>"
      ret << "<route>"
      #Converts to XML the first vertex
      ret << vertices.shift.to_xml
      edges.each do |edge|
        #For each edge, converts the edge to xml
        ret << edge.to_xml
        #Shifts to the next vertex and converts to xml
        ret << vertices.shift.to_xml
      end
      ret << "</route>"
    end
  end

  #This function looks for the vertices of the closest edge to the input coords
  #Returns an array of 3 rows, with columns named label, lat, lon, name, dist
  #The first row is not actually a vertex, but the nearest point in the edge
  #to the input coordinates
  def get_closest_edge_vertices(lat, lon)
    #Override this function in the corresponding extension (tiger and osm initially)
    return nil
  end

  #This function looks for the closest stops to the input coords
  # Returns an array of n_stops rows, with columns named label, lat, lon, name, dist
  def get_closest_stops(lat, lon, n_stops)
    # Override this function in the corresponding extension (gtfs initially)
    return nil
  end

  # Assigns the database parameters
  def database_params= params
    # Check the presence of the postgres extension
    begin
      require 'postgres'
    rescue LoadError
      @db_params = nil
      raise
    end

    begin
      #check if database connection works
      conn = PGconn.connect( params[:host],
                             params[:port],
                             params[:options],
                             params[:tty],
                             params[:dbname],
                             params[:login],
                             params[:password] )
      conn.close
    rescue PGError
      @db_params = nil
      raise
    end

    # If everything went ok, assigns the parameters
    @db_params = params
    return true
  end

  # Connect with the database
  def connect_to_database
    # If no input parameters are defined then read the database params
    # from the command line or the default ones
    unless @db_params then self.database_params= DB_PARAMS end

    PGconn.connect( @db_params[:host],
                    @db_params[:port],
                    @db_params[:options],
                    @db_params[:tty],
                    @db_params[:dbname],
                    @db_params[:login],
                    @db_params[:password] )
  end

  # May return nil if postgres isn't loaded, or the connection params aren't set
  def conn
    # If @conn exists and is open
    if @conn and begin @conn.status rescue PGError false end then
      return @conn
    else
      return @conn = connect_to_database
    end
  end

  # Starts graphserver, if a KILL signal is received, kills the webrick server too
  def start
    trap("INT"){ @server.shutdown }
    @server.start
  end

end
