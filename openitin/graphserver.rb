require 'webrick'
require 'xmlrpc/server.rb'
require 'graph.rb'
require 'optparse'

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
    "<triphopschedule/>"
  end
end

class State
  def to_xml
    ret = "<state "
    self.to_hash.each_pair do |name, value|
      ret << "#{name}='#{value.to_s}' "
    end
    ret << "/>"
  end
end

class Vertex
  def to_xml
    "<vertex label='#{label}'/>"
  end
end

class Edge
  def to_xml
    ret = "<edge>"
    ret << payload.to_xml
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

class GSREST < WEBrick::HTTPServlet::AbstractServlet

  def initialize( config, graph, calendar )
    super
    @gg = graph
    @calendar = calendar
  end

  def do_GET( request, response )
    case request.path_info
    when "/shortest_path"
      p init_time = request.query['time'] 
      unless init_time then init_time = Time.now end
      init_state = State.new( init_time )
      init_state[:calendar_day] = @calendar.day_of_or_after( init_time )

      ret = []
      ret << "<?xml version='1.0'?>"
      ret << "<route>"
      vertices, edges = @gg.shortest_path( request.query['from'], request.query['to'], init_state )
      ret << vertices.shift.to_xml      
      edges.each do |edge|
        ret << edge.to_xml
        ret << vertices.shift.to_xml
      end
      ret << "</route>"
      response.body = ret.join
    when "/all_vertex_labels"
      vlabels = []
      vlabels << "<?xml version='1.0'?>"
      vlabels << "<labels>"
      @gg.vertices.each do |vertex|
        vlabels << "<label>#{vertex.label}</label>"
      end
      vlabels << "</labels>"
      response.body = vlabels.join
    when "/outgoing_edges"
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
  end
end

class Graphserver  
  attr_reader :gg  

  def initialize
    @gg = Graph.create #horrible hack

    @servlet = XMLRPC::WEBrickServlet.new
    @servlet.add_handler("shortest_path") do |from, to, init_time| 
      p path = @gg.shortest_path( from, to, State.new( init_time ) ) 
      path
    end
    @servlet.add_handler("shortest_path_tree") do |from, to, init_time|
      @gg.shortest_path_tree( from, to, State.new( init_time ) )
    end
    @servlet.add_handler("all_vertex_labels") do
      @gg.vertices.collect do |vertex|
        vertex.label
      end
    end
    @servlet.add_handler("outgoing_edges") do |label|
      vertex = @gg.get_vertex( label )

      ret = []
      vertex.each_outgoing do |edge|
        ret << [edge.to.label, edge.payload]
      end

      ret
    end
    @servlet.add_handler("outgoing_edge") do |label, ordinal|
      vertex = @gg.get_vertex( label )
      
      i = 0
      vertex.each_outgoing do |edge|
        if i == ordinal then
          break edge.inspect
        end
        i += 1
      end
    end
    @servlet.add_handler("vertex_outgoing_weights") do |label, param|
      vertex = @gg.get_vertex( label )

      ret = []
      vertex.each_outgoing do |edge|
        ret << {:to => edge.to.label, :w => edge.weight(param)}
      end

      ret
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
    server = WEBrick::HTTPServer.new(:Port => OPTIONS[:port])
    trap("INT"){ server.shutdown }
    server.mount("/RPC2", @servlet)
    server.mount( "", GSREST, @gg, @calendar )
    server.start
  end

end
