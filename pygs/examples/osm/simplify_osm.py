from osm import OSM, Node, Way

data = open("map.osm").read()

osm = OSM( data )

fp = open("nodes.csv", "w")
for nodeid in osm.nodes.keys():
    fp.write( "%s\n"%nodeid )
fp.close()

fp = open("map.csv", "w")

for wayid, way in osm.ways.iteritems():
    if 'highway' in way.tags:
        fp.write("%s,%d,%d,%f\n"%(wayid, way.fromv, way.tov, way.length))
        
fp.close()