require 'rexml/document'
require 'rubygems'
require 'json'

class Graphserver

USAGE = %<
 USAGE:
 Start the server
 $ ruby gserver.rb --port=PORT

 Then test the XML API from a web browser:
 http://path.to.server:port/                               (blank, returns API documentation)
 .../all_vertex_labels
 .../outgoing_edges?label=Seattle                             (currently segfaults. eep!)
 .../eval_edges?label=Seattle                                 (evaluates outgoing edges at current time)
 .../eval_edges?label=Seattle-busstop&time=0                  (evaluates edges at given unix time)
 .../shortest_path?from=Seattle&to=Portland                   (finds shortest route for current. this example broken due to int range issues)
 .../shortest_path?from=Seattle&to=Portland&time=0            (finds short for given unix time)
 .../shortest_path?from=Seattle&to=Portland&time=0&debug=true (finds short for given unix time, with verbose output)
>

  def load_osm_from_file osmfile, verbose=true

    if verbose then
        print "Loading OSM file #{osmfile}\n"
    end

    #Street-style data is simpler
    
    # Load raw OSM street data from file
    f = File.new osmfile, "r"
    @xml_data =  f.read
    
    if verbose then print "Parsing XML in one big bite...\n" end
    # Parse all data all at once - very expensive
    doc = REXML::Document.new(@xml_data)
    
    if verbose then print "Putting nodes in the graph...\n" end
    # Pull all the nodes out
    @nodes = {} 
    doc.elements.each('osm/node') do |ele|
       @gg.add_vertex( ele.attribute('id').value.to_s )
       @nodes[ele.attributes['id']] = [ele.attributes['lat'].to_f,ele.attributes['lon'].to_f]
    end
   
    if verbose then print "Putting ways in the graph...\n" end
    # For each way...
    doc.elements.each('osm/way') do |ele|
      current = nil
      name = "Unnamed"  
      tag = ele.elements['tag[@k="name"]']
      if tag then
        name = "#{tag.attributes["v"]} (#{ele.attributes['id']})" 
      end  
    
      # For each node in the way...
      ele.elements.each('nd') do |node|
        if current then
          prev_id = current.attributes['ref']
          cur_id = node.attributes['ref']
          x = (@nodes[prev_id][0] - @nodes[cur_id][0]) 
          y = (@nodes[prev_id][1] - @nodes[cur_id][1]) 
          num = (x*x + y*y)
          len = Math.sqrt(num) * 10000
          @gg.add_edge( prev_id, cur_id, Street.new(name, len) )
          @gg.add_edge( cur_id, prev_id, Street.new(name, len) )
        end
        current = node
      end  
    end
    
    if verbose then print "done\n" end
  
  end
  
end
