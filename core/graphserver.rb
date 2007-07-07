require 'webrick'
#require 'xmlrpc/server.rb'
require 'graph.rb'
require 'optparse'
require 'cgi'

class Calendar
  def to_xml
    "<calendar begin_time='#{Time.at(begin_time)}' end_time='#{Time.at(end_time)}' service_ids='#{service_ids.join(", ")}' />"
  end
end

#made a different change over here

class Link
  def to_xml
    "<link/>"
  end
end

class Street
  def to_xml
    "<street name='#{name}' length='#{length}' />"
  end
end

class TripHopSchedule
  def to_xml
    ret = ["<triphopschedule service_id='#{service_id}'>"]
    triphops.each do |triphop|
      ret << triphop.to_xml
    end
    ret << "</triphopschedule>"

    return ret.join
  end
end

class TripHop
  SEC_IN_HOUR = 3600
  SEC_IN_MINUTE = 60

  def to_xml
    s_depart = "#{sprintf("%02d", depart/SEC_IN_HOUR)}:#{sprintf("%02d", (depart%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", depart%SEC_IN_MINUTE)}"
    s_arrive = "#{sprintf("%02d", arrive/SEC_IN_HOUR)}:#{sprintf("%02d", (arrive%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", arrive%SEC_IN_MINUTE)}"
    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' />"
  end
end

class State
  def to_xml
    ret = "<state "
    self.to_hash.each_pair do |name, value|
      if name == "time" then #TODO kludge alert
        ret << "time='#{Time.at( value ).inspect}' " 
      else
        ret << "#{name}='#{CGI.escape(value.to_s)}' " unless value.public_methods.include? "to_xml"
      end
    end
    ret << ">"

    self.to_hash.each_pair do |name, value|
      ret << value.to_xml if value.public_methods.include? "to_xml"
    end

    ret << "</state>"
  end
end

class Vertex
  def to_xml
    ret = ["<vertex label='#{label}'>"]
    if pl=payload then #to avoid calling payload twice. instantiating a variable may actually be more expensive.
      ret << pl.to_xml
    end
    ret << "</vertex>"
    return ret.join
  end
end

class Edge
  def to_xml verbose=true
    ret = "<edge>"
    ret << payload.to_xml if verbose
    ret << "</edge>"
  end
end

OPTIONS = { :port => 3003 }

ARGV.options do |opts|
  script_name = File.basename($0)
  opts.banner = "Usage: ruby #{script_name} [options]"

  opts.separator ""

  opts.on("-p", "--port=port", Integer,
          "Runs Rails on the specified port.",
          "Default: 3003") { |v| OPTIONS[:port] = v }

  opts.on("-h", "--help",
          "Show this help message.") { puts opts; exit }

  opts.parse!
end

class Graphserver  
  attr_reader :gg 

  def parse_init_state request
    State.new( (request.query['time'] or Time.now) ) #breaks without the extra parens
  end 

  def initialize
    @gg = Graph.create #horrible hack

    @server = WEBrick::HTTPServer.new(:Port => OPTIONS[:port])

    @server.mount_proc( "/" ) do |request, response|
      ret = ["Graphserver Web API"]
      ret << "shortest_path?from=FROM&to=TO"
      ret << "all_vertex_labels"
      ret << "outgoing_edges?label=LABEL"
      ret << "walk_edges?label=LABEL&statevar1=STV1&statevar2=STV2..."
      ret << "collapse_edges?label=LABEL&statevar1=STV1&statevar2=STV2..."
      response.body = ret.join("\n")
    end

    @server.mount_proc( "/shortest_path" ) do |request, response|
      from = request.query['from']
      to = request.query['to']
      ret = []
      
      begin
        unless  @gg.get_vertex(from) and @gg.get_vertex(to) then raise ArgumentError end

        init_state = parse_init_state( request )
        vertices, edges = @gg.shortest_path(from, to, init_state )      #Throws RuntimeError if no shortest path found.
        ret << "<?xml version='1.0'?>"
        ret << "<route>"
        ret << vertices.shift.to_xml
        edges.each do |edge|
          ret << edge.to_xml
          ret << vertices.shift.to_xml
        end
        ret << "</route>"

        rescue RuntimeError                                               #TODO: change exception type, RuntimeError is too vague.
          ret << "Couldn't find a shortest path from #{from} to #{to}"
        rescue ArgumentError
          ret << "ERROR: Invalid parameters."
      end
      
      response.body = ret.join
    end

    @server.mount_proc( "/all_vertex_labels" ) do |request, response|
      vlabels = []
      vlabels << "<?xml version='1.0'?>"
      vlabels << "<labels>"
      @gg.vertices.each do |vertex|
        vlabels << "<label>#{vertex.label}</label>"
      end
      vlabels << "</labels>"
      response.body = vlabels.join
    end

    @server.mount_proc( "/outgoing_edges" ) do |request, response|
      vertex = @gg.get_vertex( request.query['label'] )
      ret = []
      ret << "<?xml version='1.0'?>"
      ret << "<edges>"
      vertex.each_outgoing do |edge|
        ret << "<edge>"
        ret << "<dest>#{edge.to.to_xml}</dest>"
        ret << "<payload>#{edge.payload.to_xml}</payload>"
        ret << "</edge>"
      end
      ret << "</edges>"
      response.body = ret.join
    end

    @server.mount_proc( "/walk_edges" ) do |request, response|
      vertex = @gg.get_vertex( request.query['label'] )
      init_state = parse_init_state( request )

      ret = ["<?xml version='1.0'?>"]
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

      response.body = ret.join
    end
    
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
    
  end

  def database_params= params
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

    @db_params = params
    return true
  end

  def connect_to_database
    unless @db_params then return nil end

    PGconn.connect( @db_params[:host],
                    @db_params[:port],
                    @db_params[:options],
                    @db_params[:tty],
                    @db_params[:dbname],
                    @db_params[:login],
                    @db_params[:password] )
  end

  #may return nil if postgres isn't loaded, or the connection params aren't set
  def conn
    #if @conn exists and is open
    if @conn and begin @conn.status rescue PGError false end then
      return @conn
    else
      return @conn = connect_to_database
    end
  end

  def start
    trap("INT"){ @server.shutdown }
    @server.start
  end

end
