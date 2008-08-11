$: << "../../extension/tiger"
$: << "../../extension/kml"

require 'graphserver.rb'
require 'tiger_extend.rb'
require 'kml_extend.rb'

#DB_PARAMS = { :host => nil,
#              :port => nil,
#              :options => nil,
#              :tty => nil,
#              :dbname => 'graphserver',
#              :login => nil, #database username
#              :password => nil }

gs = Graphserver.new
#gs.database_params = DB_PARAMS
gs.load_tiger_from_db
gs.start
