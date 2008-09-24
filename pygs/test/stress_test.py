from stress_utils import get_mem_usage
import sys
sys.path.append("..")
from graphserver.core import *

"""
print get_mem_usage()

g = Graph()
for i in xrange(1000000):
    v = Vertex("bogus")
    del v
    
print get_mem_usage()
"""

def grind(func, n):
    mperc, m0 = get_mem_usage()

    g = Graph()
    for i in xrange(n):
        func()
        
    mperc, m1 = get_mem_usage()
    
    print m0, m1
    #assert m1 - m0 < n/1024 #the difference between the two memories is less than 1 byte*number of iterations
    assert m1 <= m0+10

import unittest
class StressTest(unittest.TestCase):

    def test_state_destroy(self):
        """State picks up after itself"""
        def func():
            s = State(1,0)
            s.destroy()
            
        grind(func, 1000000)
        
    def test_simple_vertex_destroy(self):
        """A simple Vertex object picks up after itself"""
        
        def func():
            s = Vertex("bogus")
            s.destroy()
            
        grind(func, 1000000)
        
    def test_street_destroy(self):
        """Street.destroy() completely destroys Street"""
        
        def func():
            s = Street("bogus", 1.1)
            s.destroy()
            
        grind(func, 1000000)
        
    def test_link_destroy(self):
        """Link.destroy() completely destroys Link"""
        
        def func():
            s = Link()
            s.destroy()
            
        grind(func, 1000000)

    rawhops = [(0,     1*3600,'Foo to Bar'),
                (1*3600,2*3600,'Bar to Cow'),
                (2*3600,3*3600,'four score and seven years'),
                (3*3600,4*3600,'hoombacha')]
    cal = ServiceCalendar()
    cal.add_period( 0, 1*3600*24, ["1","2"] )

    def test_ths_destroy(self):
        """TripHopSchedule.destroy() completely destroys TripHopSchedule"""
        
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 100000, 0 ) )
        
        def func():

            s = TripHopSchedule(hops=self.rawhops, service_id="1", calendar=self.cal, timezone=tz,agency=0)
            s.destroy()
            
        grind(func, 100000)
        
    def test_minimal_graph_delete(self):
        """Graph.destroy() completely destroys minimal Graph"""
        
        def func():
            s = Graph()
            s.destroy()
            
        grind( func, 1000000 )
        
    def test_min_vertex_graph_delete(self):
        """Graph.destroy() completely destroys Graph with vertices"""
        
        def func():
            s = Graph()
            s.add_vertex("A")
            s.add_vertex("B")
            s.destroy()
            
        grind(func, 100000)
        
    def test_min_edge_graph_delete(self):
        """Graph.destroy() completely destroys Graph with a smattering of edge payloads"""
        
        tz = Timezone()
        tz.add_period( TimezonePeriod( 0, 100000, 0 ) )
        
        def func():
            s = Graph()
            s.add_vertex("A")
            s.add_vertex("B")
            s.add_vertex("C")
            s.add_edge("A","B",Link())
            s.add_edge("A","B",Street("1",1.1))
            s.add_edge("A","B",Street("2",2.2))
            s.add_edge("A","B",Street("3",3.3))
            s.add_edge("B","A",Link())
            s.add_edge("B","C",TripHopSchedule(hops=self.rawhops, service_id="1", calendar=self.cal, timezone=tz,agency=0))
            s.add_edge("B","C",TripHopSchedule(hops=self.rawhops, service_id="1", calendar=self.cal, timezone=tz,agency=0))
            s.destroy()
            
        grind(func, 100000)
        
    def test_minimal_spt_delete(self):
        """ShortestPathTree.destroy() completely destroys the spt for a minimal tree"""
        
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("B")
        s.add_vertex("C")
        s.add_edge("A","B",Street("1", 1.1))
        s.add_edge("B","A",Street("1", 1.1))
        s.add_edge("B","C",Street("2", 2.2))
        
        def func():
            spt = s.shortest_path_tree("A", "C", State(1,0))
            spt.destroy()
            
        grind( func, 100000 )
        
    def test_shortest_path_grind(self):
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("B")
        s.add_vertex("C")
        s.add_edge("A","B",Street("1", 1.1))
        s.add_edge("B","A",Street("1", 1.1))
        s.add_edge("B","C",Street("2", 2.2))
        
        def func():
            spt = s.shortest_path_tree("A","C", State(1,0))
            sp = spt.path("C")
            spt.destroy()
            
        grind(func, 50000)
    

from random import randint
def random_graph(nvertices, nedges):
    """generates random graph. useful for stress testing"""
    
    vertices = [str(x) for x in range(nvertices)]
    
    g = Graph()
    
    for vertex in vertices:
        g.add_vertex(vertex)
        
    for i in range(nedges):
        a = vertices[ randint( 0, len(vertices)-1 ) ]
        b = a
        while b==a:
            b = vertices[ randint( 0, len(vertices)-1 ) ]
            
        g.add_edge(a,b,Link())
    
    return g
    
if __name__=='__main__':
    tl = unittest.TestLoader()
    
    testables = [\
                 StressTest,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)