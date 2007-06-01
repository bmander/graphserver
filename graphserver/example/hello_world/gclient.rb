#An sample graphserver client

require 'xmlrpc/client'

server = XMLRPC::Client.new("localhost", "/RPC2", 9090)
#p server.call("shortest_path", "41885313", "41885340", {:w => 0})
#print server.call("shortest_path_tree", "41885313", "41885312", {:w => 0})

if ARGV[0] == 'edges' then
  p server.call( "outgoing_edges", ARGV[1] )
end

if ARGV[0] == 'edge' then
  p server.call( "outgoing_edge", ARGV[1], ARGV[2].to_i )
end

if ARGV[0] == 'vertices' then
  p server.call( "all_vertex_labels" )
end

if ARGV[0] == 'route' then
  p server.call( "shortest_path", ARGV[1], ARGV[2], ARGV[3].to_f)
end

if ARGV[0] == 'weight' then
  p server.call( "vertex_outgoing_weights", ARGV[1], ARGV[2].to_f )
end
