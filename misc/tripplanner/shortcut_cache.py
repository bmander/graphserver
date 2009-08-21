from graphserver.core import ContractionHierarchy, Combination
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.graphdb import GraphDatabase
from glineenc import encode_pairs

def reincarnate_ch(basename):
    chdowndb = GraphDatabase( basename+".down.gdb" )
    chupdb = GraphDatabase( basename+".up.gdb" )
    
    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()
    
    return ContractionHierarchy(upgg, downgg)
    
def unpack_streets(ep):
    if ep.__class__ == Combination:
        return ep.unpack()
    else:
        return [ep]
        
def get_street_geom( osmdb, street ):
    id, parent_id, node1, node2, distance, geom, tags = osmdb.edge( street.name )
    
    if street.reverse_of_source:
        geom.reverse()
        
    return geom
    
def get_ep_geom( osmdb, edgepayload ):
    streets = unpack_streets( ep )
    geoms = [get_street_geom(osmdb, street) for street in streets]
    return reduce( lambda x,y:x+y, geoms )
    
def get_encoded_ep_geom( osmdb, edgepayload ):
    return encode_pairs( [(lat, lon) for lon, lat in get_ep_geom( osmdb, edgepayload )] )
    
if __name__=='__main__':
    ch = reincarnate_ch( "wallingford" )
    osmdb = OSMDB( "wallingford.osmdb" )
    
    for vv in ch.upgraph.vertices:
        for ee in vv.outgoing:
            epid, ep = ee.payload.external_id, ee.payload
            
            print get_encoded_ep_geom( osmdb, ep )
            
    for vv in ch.downgraph.vertices:
        for ee in vv.outgoing:
            epid, ep = ee.payload.external_id, ee.payload