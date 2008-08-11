$: << "../../extension/tiger"

require 'graphserver.rb'
require 'tiger_extend.rb'

gs = Graphserver.new
gs.load_tiger_from_file 'data'
gs.start
