$: << "../../extension/transit"
$: << "../../extension/osm"
$: << "../../extension/osm_gtfs"

require 'graphserver.rb'
require 'gtfs_extend3.rb'
require 'osm_extend2.rb'
require 'link_osm_gtfs_extend2.rb'

#Modulo que permite acceder a la base de datos desde diferentes clases
#creando una única conexión
module GsDbAccessor
  def setConn conn
    @@conn = conn
  end
  def conn
    return @@conn
  end
end

#Sobrecarga la clase TripHop para añadir la funcion to_xml
class TripHop
  include GsDbAccessor
  #Transforma a xml TripHop
  def to_xml
    s_depart = "#{sprintf("%02d", depart/SEC_IN_HOUR)}:#{sprintf("%02d", (depart%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", depart%SEC_IN_MINUTE)}"
    s_arrive = "#{sprintf("%02d", arrive/SEC_IN_HOUR)}:#{sprintf("%02d", (arrive%SEC_IN_HOUR)/SEC_IN_MINUTE)}:#{sprintf("%02d", arrive%SEC_IN_MINUTE)}"
    query = conn.exec <<-SQL
      SELECT trip_headsign
      FROM gtf_trips
      WHERE trip_id = '#{trip_id}'
    SQL
    trip_headsign = query[0][0].to_str
    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' trip_headsign='#{trip_headsign}' />"
#    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' trip_headsign='#{trip_headsign}' route_id='#{route_id}' agency_id='#{agency_id}' route_short_name='#{name}' route_long_name='#{route_long_name}' />"
#    "<triphop depart='#{s_depart}' arrive='#{s_arrive}' transit='#{transit}' trip_id='#{trip_id}' />"
  end
end

#Sobrecarga la clase Edge para añadir la funcion to_xml
class Edge
  include GsDbAccessor
  #Transforma a xml Edge, con parametro de entrada verbose
  #con valor por defecto true
  def to_xml verbose=true
    ret = "<edge>"
    #Si verbose=true inserta el payload transformado a xml
    ret << payload.to_xml if verbose
    if payload.kind_of? Street then
      ret << "<shape>"
      from_id = from.label
      to_id = to.label
      #Obtenemos el LINESTRING asociado a la calle recorrida
      shape = conn.exec <<-SQL
        SELECT AsText(geom)
        FROM osm_segments
        WHERE ('osm'||from_id)='#{from_id}' AND ('osm'||to_id)='#{to_id}'
        OR ('osm'||from_id)='#{to_id}' AND ('osm'||to_id)='#{from_id}'
        LIMIT 1
      SQL
      ret << shape[0][0].to_str
      ret << "</shape>"
    else
      if payload.kind_of? TripHop then
        ret << "<shape>"
        from_id = from.label
        to_id = to.label
        shape = conn.exec <<-SQL
          SELECT lon1, lat1, lon2, lat2
          FROM    (SELECT stop_lat AS lat1,stop_lon AS lon1
                   FROM gtf_stops
                   WHERE ('gtfs'||stop_id)='#{from_id}') AS stops1,
                  (SELECT stop_lat AS lat2,stop_lon AS lon2
                   FROM gtf_stops
                   WHERE ('gtfs'||stop_id)='#{to_id}') AS stops2
        SQL
        ret << "LINESTRING(" + shape[0][0] + " " + shape[0][1] + "," + shape[0][2] + " " + shape[0][3] + ")"
        ret << "</shape>"
      end
    end
    ret << "</edge>"
  end
end

#Sobrecargamos Graphserver para que incluya el módulo de acceso a la base de datos
class Graphserver
  include GsDbAccessor
end

# At least one parameter (the osm file)
if ARGV.size < 1 then
  print "usage: ruby osm_gtfs_server.rb DIRECTIONAL --port=PORT\n"
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
#asignamos la conexión al módulo de acceso a la base de datos
gs.setConn gs.conn

#load gtfs data
print "Loading GTFS data\n"
gs.load_google_transit_feed
#load osm data
print "Loading OSM street data\n"
gs.load_osm_from_db file=nil, directional=(ARGV[0]=="true")
#load links
print "Linking GTFS and OSM data\n"
gs.load_osm_gtfs_links

gs.start
