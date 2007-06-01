$: << "../../extension/tiger"

require 'graphserver.rb'
require 'load_tiger_line.rb'

gs = Graphserver.new
gs.load_tiger_from_file 'data'
gs.start
