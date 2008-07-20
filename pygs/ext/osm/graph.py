import time
from osm import OSM

try:
    from pygs.graphserver import Graph, Street, State
except ImportError, e:
    sys.path.append('../..')
    from graphserver import Graph, Street, State



class OSMGraph(Graph):
        
    def __init__(self, filename_or_stream, projection):
        """ Builds an OSM graph based on a filename or filehandle.  Projection is used for calculating lengths.
        Subclasses can override the is_valid_way and create_edgepayload methods to filter path types and 
        create alternative payloads."""
        
        super(OSMGraph, self).__init__()
        self.projection = projection

        t0 = time.time()
        print "parsing OSM file"
        osm = OSM(filename_or_stream)
        self.osm = osm
        t1 = time.time()
        print "parsing took: %f"%(t1-t0)
        t0 = t1

        print "load vertices into memory"
        for nodeid in osm.nodes.keys():
            self.add_vertex( str(nodeid) )

        print "load edges into memory"
        for way in osm.ways.values():
            if self.is_valid_way(way):
                # need two copies of the payload
                self.add_edge( str(way.fromv), str(way.tov), self.create_edgepayload(way) )
                self.add_edge( str(way.tov), str(way.fromv), self.create_edgepayload(way) )
        t1 = time.time()
        print "populating graph took: %f"%(t1-t0)
    
    def is_valid_way(self, way):
        return 'highway' in way.tags
    
    def create_edgepayload(self, way):
        len = way.length(self.projection)
        return Street( way.id, len )
            
    def shortest_path_tree(self, from_v, to_v, state):
        t0 = time.time()
        spt = super(OSMGraph, self).shortest_path_tree( from_v, to_v, state)
        t1 = time.time()
        print "shortest_path_tree took: %f"%(t1-t0)
        return spt
    
    def write_graph(self, fp, format="%(from)s:%(to)s:%(points)s\n", reproject=True, point_delim=","):
        for edge in self.edges:
            osmway = self.osm.ways[ edge.payload.name ]
            if reproject:
                points = osmway.get_projected_points(self.osm.nodes, self.projection)
            else:
                points = osmway.get_projected_points(self.osm.nodes, lambda x,y: (x,y))
            fp.write( format % {'from':edge.from_v.label,
                                'to':edge.to_v.label,
                                'name':osmway.tags.get('name',''),
                                'length':edge.payload.length,
                                'points':point_delim.join( [" ".join([str(c) for c in p]) for p in points] )})
            
    
    def write_spt(self, fp, spt, format="%(from)s:%(to)s:%(length)f:%(weight)d:%(points)s\n", 
                  reproject=True, point_delim=","):
        """ Writes out a shortest path tree. """
        for edge in spt.edges:
            osmway = self.osm.ways[ edge.payload.name ]
            state = edge.to_v.payload
            if reproject:
                points = osmway.get_projected_points(self.projection)
            else:
                points = osmway.get_projected_points()
            length = edge.payload.length #osmway.length(osm.nodes)
            elapsed = state.time
            num_transfers = state.num_transfers
            
            fp.write( format % {'from':edge.from_v.label,
                                'to':edge.to_v.label,
                                'length':length,
                                'weight':state.weight,
                                'state':state,
                                'time':state.time,
                                'dist_walked':state.dist_walked,
                                'num_transfers':state.num_transfers,
                                'points':point_delim.join( [" ".join([str(c) for c in p]) for p in points] )} )
 