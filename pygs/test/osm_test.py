from pyproj import Proj
from StringIO import StringIO
from random import randint

import sys, os, subprocess
#sys.path.append("..")
from graphserver.ext.osm.graph import OSMGraph
from graphserver.ext.osm.osm import OSM
from graphserver.core import State
import unittest

RESOURCE_DIR=os.path.dirname(os.path.abspath(__file__))

def find_resource(s):
    return os.path.join(RESOURCE_DIR, s)

class TestOSM(unittest.TestCase):
    def setUp(self):
        if os.path.exists(os.path.join(os.path.dirname(__file__), "map.osm.zip")) and not os.path.exists(os.path.join(os.path.dirname(__file__), "map.osm")):
            subprocess.call(['unzip', "map.osm.zip"], cwd=os.path.dirname(__file__))


    def test_basic(self):
        """basic osm file load test."""
        #utmzone10 = Proj(init='epsg:26910')
        print "loading map.osm"
        osm = OSM(find_resource("map.osm"))
        print "iterating over all the ways and calculating length."
        for way in osm.ways.values():
            way.length()
            assert glen(way.nds) > 1
        print "done"

    def test_osmgraph(self):
        """create graph from osm file."""
        utmzone10 = Proj(init='epsg:26910')
        g = OSMGraph(find_resource("map.osm"), utmzone10)
        vert = g.vertices

        while True:
            random_vertex_label = vert[randint(0, len(vert)-1)].label
            if len(g.get_vertex(random_vertex_label).outgoing) != 0:
                break
            print "finding a better vertex..."

        print "finding shortest path tree for %s" % random_vertex_label
        spt = g.shortest_path_tree(random_vertex_label, "!bogus!!@", State(1,0))
        assert spt
        s = StringIO()
        g.write_spt(s, spt)
        assert len(s.getvalue()) > 0
        s.close()
        spt.destroy()
        g.destroy()

    def test_osmgraph_from_object(self):
        utmzone10 = Proj(init='epsg:26910')
        g = OSMGraph(OSM(find_resource("map.osm")), utmzone10)
        assert len(g.vertices) != 0

    def test_find_nearest_node(self):
        osm = OSM(find_resource("sf.osm"))
        n = osm.find_nearest_node(-122.4179760000,37.7434470000)
        print n.id
        assert n.id == "65325497"

def glen(gen):
    return len(list(gen))


if __name__=='__main__':
    tl = unittest.TestLoader()

    testables = [\
                 TestOSM,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)
