require 'postgres'
require 'webrick'

require 'rubygems'
require 'geo_ruby'

DB_PARAMS = { :host => nil,
              :port => nil,
              :options => nil,
              :tty => nil,
              :dbname => 'graphserver',
              :login => nil, #database username
              :password => nil }

conn = PGconn.connect( DB_PARAMS[:host],
                DB_PARAMS[:port],
                DB_PARAMS[:options],
                DB_PARAMS[:tty],
                DB_PARAMS[:dbname],
                DB_PARAMS[:login],
                DB_PARAMS[:password] )

# this is how to use a conn object
#stops = conn.exec "SELECT stop_id FROM gtf_stops"
#stops.each do |stop| p stop end

def linestring_to_geojson( ls )
    ret = []
    ls.points.each do |point|
        ret << [point.x, point.y]
    end
    return ret
end

def tiger_to_geom( conn, id )
    ewkb = conn.exec( "select geom from tiger_streets  where id ='#{id}'" )[0][0]
    return linestring_to_geojson( GeoRuby::SimpleFeatures::Geometry.from_hex_ewkb( ewkb ) )
end

def gtfs_to_geom( conn, fromid, toid, tripid )
   fromdist = Integer( conn.exec( "select shape_dist_traveled from gtf_stop_times where stop_id = '#{fromid}' and trip_id = '#{tripid}'" )[0][0] )
   todist   = Integer( conn.exec( "select shape_dist_traveled from gtf_stop_times where stop_id = '#{toid}' and trip_id = '#{tripid}'" )[0][0] )
   shapedist = 3.2808399*Float( conn.exec( "select st_length_spheroid(shape, 'SPHEROID[\"GRS_1980\",6378137,298.257222101]') from gtf_trips, gtf_shapes where gtf_trips.shape_id = gtf_shapes.shape_id and trip_id = '#{tripid}'" )[0][0] ) #convert to feet as a horrible hack for portland demo only. What we really should do is store the largest shapefile value and query it here.
   
   startpoint = if fromdist/shapedist < 1 then fromdist/shapedist else 1 end
   endpoint = if todist/shapedist < 1 then todist/shapedist  else 1 end
   
   slice = conn.exec( "select st_line_substring(shape, #{startpoint}, #{endpoint}) from gtf_trips, gtf_shapes where gtf_trips.shape_id = gtf_shapes.shape_id and trip_id = '#{tripid}'" )[0][0]
   
   return linestring_to_geojson( GeoRuby::SimpleFeatures::Geometry.from_hex_ewkb( slice ) )
end

def link_to_geom( conn, tigerpoint, gtfpoint )
    stopwkb = conn.exec( "select location from gtf_stops where stop_id='#{gtfpoint}'" )[0][0]
    streetwkb = conn.exec( "select startpoint(geom) as point from tiger_streets where from_id = '#{tigerpoint}' union (select endpoint(geom) as point from tiger_streets where to_id='#{tigerpoint}') limit 1;")[0][0]
    
    line = conn.exec( "select st_makeline('#{stopwkb}', '#{streetwkb}')" )[0][0]
    
    return linestring_to_geojson( GeoRuby::SimpleFeatures::Geometry.from_hex_ewkb( line ) )
end

#p tiger_to_geom( conn, "157594969" )
#p gtfs_to_geom( conn, "3957", "1844", "41U1500" )
#p link_to_geom( conn, "3957", "3957" )

def triad_to_geom( conn, prevlabel, nextlabel, el )
    if prevlabel[0..3]=="gtfs" and nextlabel[0..3]=="gtfs" then
        fromid = prevlabel[4..-1]
        toid = nextlabel[4..-1]
        tripid = el.children[0].attributes["trip_id"]
        return ["transit", gtfs_to_geom( conn, fromid, toid, tripid ) ]
    elsif prevlabel[0..1]=='tg' and nextlabel[0..1]=="tg" then
        tigerid = el.children[0].attributes['name']
        return ["street", tiger_to_geom( conn, tigerid ) ]
    else
        if prevlabel[0..1]=='tg'
            tigerpoint = prevlabel[2..-1]
            gtfpoint = nextlabel[4..-1]
        else
            tigerpoint = nextlabel[2..-1]
            gtfpoint = prevlabel[4..-1]
        end
        return ["link", link_to_geom(conn, tigerpoint, gtfpoint)]
    end
end

require 'uri'
require 'net/http'
url = "http://localhost:3003/shortest_path?from=tg53964086&to=tg7542"
itin = Net::HTTP.get_response( URI.parse( url ) ).body

require "rexml/document"
doc = REXML::Document.new itin

doc.elements.each("route/edge") do |el|
    prevlabel = el.previous_element.attributes["label"]
    nextlabel = el.next_element.attributes["label"]
    p triad_to_geom( conn, prevlabel, nextlabel, el )
end