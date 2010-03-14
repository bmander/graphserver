from graphserver.core import *
from graphserver.engine import Engine
import unittest

class TestEngine(unittest.TestCase):
    def test_basic(self):
        gg = Graph()
        eng = Engine(gg)
        
        assert eng
        
    def test_basic(self):
        gg = Graph()
        eng = Engine(gg)
        
        assert eng
        
    def test_all_vertex_labels(self):
        gg = Graph()
        gg.add_vertex("A")
        gg.add_vertex("B")
        gg.add_edge("A","B",Street("1",10))
        gg.add_edge("B","A",Street("2",10))
        gg.add_vertex("C")
        gg.add_edge("C","A",Street("3",10))
        gg.add_edge("A","C",Street("4",10))
        gg.add_edge("B","C",Street("5",10))
        gg.add_edge("C","B",Street("6",10))
        
        eng = Engine(gg)
        
        assert eng.all_vertex_labels() == "<?xml version='1.0'?><labels><label>A</label><label>B</label><label>C</label></labels>"
        
    def test_walk_edges_street(self):
        gg = Graph()
        gg.add_vertex("A")
        gg.add_vertex("B")
        gg.add_edge("A","B",Street("1",10))
        gg.add_edge("B","A",Street("2",10))
        gg.add_vertex("C")
        gg.add_edge("C","A",Street("3",10))
        gg.add_edge("A","C",Street("4",10))
        gg.add_edge("B","C",Street("5",10))
        gg.add_edge("C","B",Street("6",10))
        
        eng = Engine(gg)
        
        assert eng.walk_edges("A", time=0) == "<?xml version='1.0'?><vertex><state time='0' weight='0' dist_walked='0.0' num_transfers='0' trip_id='None'></state><outgoing_edges><edge><destination label='C'><state time='11' weight='11' dist_walked='10.0' num_transfers='0' trip_id='None'></state></destination><payload><Street name='4' length='10.000000' rise='0.000000' fall='0.000000' way='0'/></payload></edge><edge><destination label='B'><state time='11' weight='11' dist_walked='10.0' num_transfers='0' trip_id='None'></state></destination><payload><Street name='1' length='10.000000' rise='0.000000' fall='0.000000' way='0'/></payload></edge></outgoing_edges></vertex>"

    def xtest_outgoing_edges_entire_osm(self):
        gg = Graph()
        osm = OSM("sf.osm")
        add_osm_to_graph(gg,osm)
        
        eng = Engine(gg)
        
        assert eng.outgoing_edges("65287655") == "<?xml version='1.0'?><edges><edge><dest><Vertex degree_out='4' degree_in='4' label='65287660'/></dest><payload><Street name='8915843-0' length='218.044876' /></payload></edge></edges>"
        
    def xtest_walk_edges_entire_osm(self):
        gg = Graph()
        osm = OSM("sf.osm")
        add_osm_to_graph(gg,osm)
        
        eng = Engine(gg)
        
        assert eng.walk_edges("65287655", time=0) == "<?xml version='1.0'?><vertex><state time='Thu Jan  1 00:00:00 1970' weight='0' dist_walked='0.0' num_transfers='0' prev_edge_type='5' prev_edge_name='None' trip_id='None'></state><outgoing_edges><edge><destination label='65287660'><state time='Thu Jan  1 00:04:16 1970' weight='512' dist_walked='218.044875866' num_transfers='0' prev_edge_type='0' prev_edge_name='8915843-0'></state></destination><payload><Street name='8915843-0' length='218.044876' /></payload></edge></outgoing_edges></vertex>"
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestEngine)
    unittest.TextTestRunner(verbosity=2).run(suite)