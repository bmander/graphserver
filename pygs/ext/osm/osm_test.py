from pyproj import Proj
from StringIO import StringIO
from random import randint
from graph import OSMGraph
from osm import OSM
from pygs.graphserver import State


class TestOSM:
    def test_basic(self):
        """basic osm file load test."""        
        utmzone10 = Proj(init='epsg:26910')
        print "loading map.osm"
        osm = OSM("map.osm")
        print "iterating over all the ways and calculating length."
        for way in osm.ways.values():
            way.length(osm.nodes, utmzone10)
        print "done"
        
    def test_osmgraph(self):
        """create graph from osm file."""
        utmzone10 = Proj(init='epsg:26910')
        g = OSMGraph("map.osm", utmzone10)
        vert = g.vertices
        
        while True:
            random_vertex_label = vert[randint(0, len(vert)-1)].label
            if len(g.get_vertex(random_vertex_label).outgoing) != 0:
                break
            print "finding a better vertex..."
        
        print "finding shortest path tree for %s" % random_vertex_label
        spt = g.shortest_path_tree(random_vertex_label, "!bogus!!@", State(0))
        assert spt
        s = StringIO()
        g.write_spt(s, spt)
        assert len(s.getvalue()) > 0
        s.close()
        spt.destroy()
        g.destroy() 