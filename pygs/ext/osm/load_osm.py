from osm import OSM,Node,Way
from pygs.graphserver import Graph, Street

def add_osm_to_graph(g, osm, projection, multipliers=[], prefix="osm"):
    """multipliers is a dict of highway types to edge weight multipliers (highwaytype,multiplier) which effect the
       preferential weighting of a kind of edge. For example, {'cycleway':0.333} makes cycleways three
       times easier to traverse"""
    
    for nodeid in osm.nodes.keys():
        g.add_vertex( prefix+str(nodeid) )
    
    for wayid, way in osm.ways.iteritems():
        if 'highway' in way.tags:
            len = way.length(projection)
            
            if way.tags['highway'] in multipliers:
                len = len*multipliers[way.tags['highway']]
            
            g.add_edge( prefix+str(way.fromv), prefix+str(way.tov), Street( wayid, len ) )
            g.add_edge( prefix+str(way.tov), prefix+str(way.fromv), Street( wayid, len ) )
            