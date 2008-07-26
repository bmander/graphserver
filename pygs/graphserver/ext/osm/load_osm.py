from osm import OSM,Node,Way
import sys
sys.path.append('../../..')
from graphserver.core import Graph, Street

class OSMLoadable:
    def load_osm(self, osm_filename_or_object, projection, multipliers=[], prefix="osm"):
        """multipliers is a dict of highway types to edge weight multipliers (highwaytype,multiplier) which effect the
           preferential weighting of a kind of edge. For example, {'cycleway':0.333} makes cycleways three
           times easier to traverse"""
           
        if type(osm_filename_or_object) == str:
            osm = OSM(osm_filename_or_object)
        else:
            osm = osm_filename_or_object
        
        for nodeid in osm.nodes.keys():
            self.add_vertex( prefix+str(nodeid) )
        
        for wayid, way in osm.ways.iteritems():
            if 'highway' in way.tags:
                len = way.length(projection)
                
                if way.tags['highway'] in multipliers:
                    len = len*multipliers[way.tags['highway']]
                
                self.add_edge( prefix+str(way.fromv), prefix+str(way.tov), Street( wayid, len ) )
                self.add_edge( prefix+str(way.tov), prefix+str(way.fromv), Street( wayid, len ) )
            