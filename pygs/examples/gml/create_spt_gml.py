"""Here's a little example whereby a shortest path tree is generated for the San Francisco area starting at the node "65287655",
   which corresponds to an intersection near the Presidio. The output is a text file where each line represents a branch in the
   shortest path tree. The line takes the format STARTING_VERTEX:ENDING_VERTEX:LENGTH:x1 y1,x2 y2..."""


import time
import transitfeed
from pyproj import Proj

try:
    #from ext.osm import OSM, Node, Way, OSMLoadable
    from ext.osm import *
    from ext.gtfs import GTFSLoadable
    from core import Graph, Street, State, Link, TripHop
except ImportError:
    import sys
    #from graphserver.ext.osm import OSM, Node, Way, OSMLoadable
    from graphserver.ext.osm import *
    from graphserver.ext.gtfs import GTFSLoadable
    from graphserver.core import Graph, Street, State, Link, TripHop

class SPTGraph(Graph, OSMLoadable, GTFSLoadable):
    pass

def main():
    #print get_osm_xml( -122.33, 47.66, -122.31, 47.68 )
    #utmzone10 = Proj(init='epsg:26910')
    #utmzone10 = Proj(init='epsg:4326')

    g = SPTGraph()
    osm = OSM("./osm/valencia.osm")
    sched = transitfeed.Loader("./gtfs").Load()
    #sched = transitfeed.Loader("/home/juangui/proyectos/siti/datos/gtfs/MetroBus/").Load()
    print "loading osm data"
    #g.load_osm( osm, utmzone10, {'cycleway':0.3333, 'footway':0.5, 'motorway':100} )
    #g.load_osm( osm, utmzone10, {'footway':0.8, 'motorway':1.5} ) # benefit footways against motorways
    g.load_osm( osm, None )
    print "loading gtfs data"
    g.load_gtfs( sched )

    print "linking stops to streets"
    for stop in sched.GetStopList():
        node = osm.find_nearest_node(stop.stop_lon,stop.stop_lat)
        # explicitly link transit vertices to nearby street vertices
        g.add_edge( "gtfs" + stop.stop_id, "osm" + node.id, Link() )
        g.add_edge( "osm" + node.id, "gtfs" + stop.stop_id, Link() )
        print "linked " + stop.stop_id + " to " + node.id

    #twothirtysix = 1217367385 # unix time for about 2:36PM July 29, 2008 UTC-0700
    init_time = time.mktime(time.strptime('2008-06-12 08:00:00',"%Y-%m-%d %H:%M:%S"))
    #init_time = 1217392380
    random_vertex_label = "osm29935874" # (calle) Plaza del Ayuntamiento
    #random_vertex_label = "gtfs1704" # (parada) Angel Guimera

    print "finding shortest path tree"
    t0 = time.time()
    spt = g.shortest_path_tree( random_vertex_label, "bogus", State(1, init_time) )
    t1 = time.time()
    print "took: %f"%(t1-t0)

    print "writing gml file"
    fp = open("spt.gml", "w")
    fp.write("<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n")
    fp.write("<gml:FeatureCollection xmlns:cit=\"http://www.gvsig.com/cit\" xmlns:gml=\"http://www.opengis.net/gml\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://www.gvsig.com/cit spt.xsd\">\n")
    for edge in spt.edges:
        weight = edge.to_v.payload.weight
        secs = edge.to_v.payload.time - init_time #seconds since journey start
        if isinstance( edge.payload, Street ):
            osmway = osm.ways[ edge.payload.name ]
            #points = osmway.get_projected_points(utmzone10)
            points = osmway.get_projected_points()
            #length = osmway.length(utmzone10)
            length = edge.payload.length
        elif isinstance( edge.payload, TripHop ):
            from_stop = sched.GetStop (edge.from_v.label[4:]) #truncate string to eliminate "gtfs" prefix
            to_stop = sched.GetStop (edge.to_v.label[4:]) #truncate string to eliminate "gtfs" prefix
            points = [[from_stop.stop_lon, from_stop.stop_lat], [to_stop.stop_lon, to_stop.stop_lat]]
            #length = dist_haversine( from_stop.stop_lon, from_stop.stop_lat, to_stop.stop_lon, to_stop.stop_lat )
            length = 0
        else:
            if edge.from_v.label[:3] == "osm":
                v0 = osm.nodes[ edge.from_v.label[3:] ]
                p0 = [ v0.lon, v0.lat]
            else:
                v0 = sched.GetStop ( edge.from_v.label[4:] )
                p0 = [ v0.stop_lon, v0.stop_lat]
            if edge.to_v.label[:3] == "osm":
                v1 = osm.nodes[ edge.to_v.label[3:] ]
                p1 = [ v1.lon, v1.lat]
            else:
                v1 = sched.GetStop ( edge.to_v.label[4:] )
                p1 = [ v1.stop_lon, v1.stop_lat]
            points = [ p0, p1 ]
            #length = dist_haversine( p0[0], p0[1], p1[0], p1[1] )
            length = 0

        #fp.write( "%s:%s:%f:%d:"%(edge.from_v.label,edge.to_v.label,length,weight)+",".join( [" ".join([str(c) for c in p]) for p in points] ) + "\n" )
        fp.write("  <gml:featureMember>\n")
        fp.write("    <cit:spt>\n")
        fp.write("      <cit:the_geom>\n")
        fp.write("        <gml:MultiLineString srsName='0'>\n")
        fp.write("          <gml:lineStringMember>\n")
        fp.write("            <gml:LineString srsName='0'>\n")
        fp.write("              <gml:coordinates>\n")
        fp.write("                " + " ".join( [",".join([str(c) for c in p]) for p in points] ) + "\n")
        #-0.49537544565178776,39.55130548895181 -0.4940425538294964,39.551897885317274
        fp.write("              </gml:coordinates>\n")
        fp.write("            </gml:LineString>\n")
        fp.write("          </gml:lineStringMember>\n")
        fp.write("        </gml:MultiLineString>\n")
        fp.write("      </cit:the_geom>\n")
        fp.write("      <cit:from>%s"%(edge.from_v.label)+"</cit:from>\n")
        fp.write("      <cit:to>%s"%(edge.to_v.label)+"</cit:to>\n")
        fp.write("      <cit:length>%f"%(length)+"</cit:length>\n")
        fp.write("      <cit:weight>%d"%(weight)+"</cit:weight>\n")
        fp.write("      <cit:time>%d"%(secs)+"</cit:time>\n")
        fp.write("    </cit:spt>\n")
        fp.write("  </gml:featureMember>\n")

    fp.write("</gml:FeatureCollection>\n")
    fp.close()
    print "writing xsd schema"
    create_xsd("spt")

def create_xsd(name):
    fp = open(name + ".xsd", "w")
    fp.write("<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n")
    fp.write("<xs:schema targetNamespace=\"http://www.gvsig.com/cit\" xmlns:cit=\"http://www.gvsig.com/cit\" xmlns:gml=\"http://www.opengis.net/gml\" xmlns:xs=\"http://www.w3.org/2001/XMLSchema\" elementFormDefault=\"qualified\" attributeFormDefault=\"unqualified\" version=\"2.1.2\">\n")
    fp.write("  <xs:import namespace=\"http://www.opengis.net/gml\" schemaLocation=\"feature.xsd\"/>\n")
    fp.write("  <xs:complexType xmlns:xs=\"http://www.w3.org/2001/XMLSchema\" name=\"spt_Type\">\n")
    fp.write("    <xs:complexContent>\n")
    fp.write("      <xs:extension base=\"gml:AbstractFeatureType\">\n")
    fp.write("        <xs:sequence>\n")
    fp.write("          <xs:element name=\"the_geom\" minOccurs=\"0\" nillable=\"true\" type=\"gml:MultiLineStringPropertyType\"/>\n")
    fp.write("          <xs:element name=\"from\" minOccurs=\"0\" nillable=\"true\" type=\"xs:string\"/>\n")
    fp.write("          <xs:element name=\"to\" minOccurs=\"0\" nillable=\"true\" type=\"xs:string\"/>\n")
    fp.write("          <xs:element name=\"length\" minOccurs=\"0\" nillable=\"true\" type=\"xs:double\"/>\n")
    fp.write("          <xs:element name=\"weight\" minOccurs=\"0\" nillable=\"true\" type=\"xs:integer\"/>\n")
    fp.write("          <xs:element name=\"time\" minOccurs=\"0\" nillable=\"true\" type=\"xs:integer\"/>\n")
    fp.write("        </xs:sequence>\n")
    fp.write("      </xs:extension>\n")
    fp.write("    </xs:complexContent>\n")
    fp.write("  </xs:complexType>\n")
    fp.write("  <xs:element name=\"spt\" type=\"cit:spt_Type\" substitutionGroup=\"gml:_Feature\"/>\n")
    fp.write("</xs:schema>\n")
    fp.close()

if __name__=='__main__':
    main()