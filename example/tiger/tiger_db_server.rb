$: << "../../extension/tiger"

require 'graphserver.rb'
require 'tiger_extend.rb'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => 'postgres', #database username
              :password => 'postgres' }

gs = Graphserver.new
gs.database_params = DB_PARAMS
gs.load_tiger_from_db
gs.start
