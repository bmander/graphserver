$: << "../../extension/osm"

require 'graphserver.rb'
require 'osm_extend2.rb'

# At least one parameter (the osm file)
if ARGV.size < 1 then
  print "usage: ruby osm_db_server.rb DIRECTIONAL --port=PORT\n"
  print "       DIRECTIONAL: true if oneway tags are considered\n"
  exit
end

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => 'postgres', #database username
              :password => 'postgres' }

gs = Graphserver.new
gs.database_params = DB_PARAMS
gs.load_osm_from_db file=nil, directional=(ARGV[0]=="true")
gs.start