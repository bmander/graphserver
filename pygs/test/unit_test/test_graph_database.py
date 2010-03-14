import unittest
from graphserver.core import Graph, Link, Street
from graphserver.graphdb import GraphDatabase
import os

def glen(gen):
    return len(list(gen))

class TestGraphDatabase(unittest.TestCase):
    def test_basic(self):
        g = Graph()
        g.add_vertex("A")
        g.add_vertex("B")
        g.add_edge("A", "B", Link())
        g.add_edge("A", "B", Street("foo", 20.0))
        gdb_file = os.path.dirname(__file__) + "unit_test.db"
        if os.path.exists(gdb_file):
            os.remove(gdb_file)        
        gdb = GraphDatabase(gdb_file)
        gdb.populate(g)
        
        list(gdb.execute("select * from resources"))
        assert "A" in list(gdb.all_vertex_labels())
        assert "B" in list(gdb.all_vertex_labels())
        assert glen(gdb.all_edges()) == 2
        assert glen(gdb.all_outgoing("A")) == 2
        assert glen(gdb.all_outgoing("B")) == 0
        assert glen(gdb.all_incoming("A")) == 0
        assert glen(gdb.all_incoming("B")) == 2
        assert glen(gdb.resources()) == 0
        assert gdb.num_vertices() == 2
        assert gdb.num_edges() == 2
        
        g.destroy()
        g = gdb.incarnate()
        
        list(gdb.execute("select * from resources"))
        assert "A" in list(gdb.all_vertex_labels())
        assert "B" in list(gdb.all_vertex_labels())
        assert glen(gdb.all_edges()) == 2
        assert glen(gdb.all_outgoing("A")) == 2
        assert glen(gdb.all_outgoing("B")) == 0
        assert glen(gdb.all_incoming("A")) == 0
        assert glen(gdb.all_incoming("B")) == 2
        assert glen(gdb.resources()) == 0
        assert gdb.num_vertices() == 2
        assert gdb.num_edges() == 2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestGraphDatabase)
    unittest.TextTestRunner(verbosity=2).run(suite)