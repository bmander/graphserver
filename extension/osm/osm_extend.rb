require 'rexml/document'
require "rexml/streamlistener"
require 'rubygems'
require 'json'

include REXML

class OSMNode
  attr_accessor :id, :lat, :lon, :tags
  
  def initialize id
    @id = id
    @tags = {}
  end
  
end

class OSMWay
  attr_accessor :id, :nodes, :tags
  
  def initialize id
    @id = id
    @nodes = []
    @tags = {}
  end
  
end

class Graphserver

  class MyListener
    include StreamListener
    
    def initialize graph
      #general parsing varialbes
      @curr_obj = nil
      
      #graphserver-specific variables
      @nodes = {}
      @gg = graph
    end
    
    # Subclass listener
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
    def tag_end name
      case name
        when 'node'
          handle_node @curr_obj
        when 'way'
          handle_way @curr_obj
      end
    end
    
    def handle_node node
      @gg.add_vertex( node.id )
      @nodes[node.id] = [node.lat, node.lon]
    end
    
    def handle_way way
      current = nil
      
      name = "#{way.tags['name'] || "Unnamed"} (#{way.id})"
    
      # For each node in the way...
      way.nodes.each do |node|
        if current then
          prev_id = current
          cur_id = node
          x = (@nodes[prev_id][0] - @nodes[cur_id][0]) 
          y = (@nodes[prev_id][1] - @nodes[cur_id][1])
          num = (x*x + y*y)
          len = Math.sqrt(num) * 10000
          @gg.add_edge( prev_id, cur_id, Street.new(name, len) )
          # If the oneway tag isn't set or is set to none, add a reverse directed edge
          if not way.tags['oneway'] or way.tags['oneway']=='false' or way.tags['oneway']=='no' then
            @gg.add_edge( cur_id, prev_id, Street.new(name, len) )
          end
        end
        current = node
      end  
    end
    
  end

  def load_osm_from_file osmfile, verbose=true

    list = MyListener.new @gg
    source = File.new osmfile, "r"
    REXML::Document.parse_stream(source, list)
  
  end
  
end
