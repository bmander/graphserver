#Add extensions directory to the path
$: << "../../extension/transit"

#Include class Graphserver
require 'graphserver.rb'
#Include functions create_gtfs_tables, remove_gtfs_tables and import_gtfs_to_db
require 'gtfs_extend.rb'

#At least one parameter (create_tables or directory)
if ARGV.size < 1 then
  print "usage: ruby setup_gtfs_tables.rb [create_tables] [directory [directory ...] ]\n"
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

if ix = ARGV.index("create_tables") then
  puts "removing gtfs tables"
  gs.remove_gtfs_tables! #clean up first
  puts "creating gtfs tables"
  gs.create_gtfs_tables!

  ARGV.delete_at( ix )
end

ARGV.each do |directory|
  gs.import_gtfs_to_db! directory
end

