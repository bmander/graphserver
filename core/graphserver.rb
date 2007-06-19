require 'webrick'
#require 'xmlrpc/server.rb'
require 'graph.rb'
require 'optparse'
require 'cgi'

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
    triphops.each do |depart, arrive, transit, trip_id|
      ret << "<triphop depart='#{depart}' arrive='#{arrive}' transit='#{transit}' trip_id='#{trip_id}' />"
    end
    ret << "</triphopschedule>"

    return ret.join
  end
end

class State
  def to_xml
    ret = "<state "
    self.to_hash.each_pair do |name, value|
      ret << "#{name}='#{CGI.escape(value.to_s)}' "
    end
    ret << "/>"
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
      ret << "eval_edges?label=LABEL&statevar1=STV1&statevar2=STV2..."
      response.body = ret.join("\n")
    end

    @server.mount_proc( "/shortest_path" ) do |request, response|
      if request.query['debug'] == 'true' then
         verbose=true
      else
         verbose=false
      end
      
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
             ret << edge.to_xml( verbose )
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

    @server.mount_proc( "/eval_edges" ) do |request, response|
      vertex = @gg.get_vertex( request.query['label'] )
      init_state = parse_init_state( request )

      ret = ["<?xml version='1.0'?>"]
      ret << "<vertex>"
      ret << init_state.to_xml
      ret << "<outgoing_edges>"
      vertex.each_outgoing do |edge|
        ret << "<edge>"
        ret <<   "<destination label='#{edge.to.label}'>"
        if dest_state = edge.walk( init_state ) then
          ret << dest_state.to_xml
        else
          ret << "<state/>"
        end
        ret <<   "</destination>"
        ret <<   "<payload>#{edge.payload.to_xml}</payload>"
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
