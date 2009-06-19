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

def grind(func, n, threshold=10):
    mperc, m0 = get_mem_usage()

    g = Graph()
    for i in xrange(n):
        func()
        
    mperc, m1 = get_mem_usage()
    
    print m0, m1
    #assert m1 - m0 < n/1024 #the difference between the two memories is less than 1 byte*number of iterations
    assert m1 <= m0+threshold

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

    def test_trip_board_destroy(self):
        """TripBoard.destroy() completely destroys TripBoard"""
        
        sc = ServiceCalendar()
        sc.add_period( 0, 1*3600*24-1, ['WKDY'] )
        sc.add_period( 1*3600*25, 2*3600*25-1, ['SAT'] )
        tz = Timezone()
        tz.add_period( TimezonePeriod(0, 1*3600*24, 0) )
        
        def func():
            tb = TripBoard( "WKDY", sc, tz, 0 )
            tb.add_boarding( "1111", 50 )
            tb.add_boarding( "2222", 100 )
            tb.add_boarding( "3333", 200 )
            
            tb.destroy()
            
        grind( func, 100000 )
        
    def test_crossing_destroy(self):
        def func():
            cr = Crossing(10)
            cr.destroy()
            
        grind( func, 100000 )
        
    def test_alight_destroy(self):
        print Timezone.__module__
        tz = Timezone()                    
        cal = ServiceCalendar()            
                                       
        def func():                        
            al = Alight(0, cal,tz, 0)      
            al.destroy()                   
                                       
        grind( func, 100000 )           
        print dir(tz)                      
        tz.destroy()                    
        cal.destroy()                   

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

class WaitStressTest(unittest.TestCase):
    def test_wait_destroy(self):
        """Wait.destroy() completely destroys Wait"""
        
        tz = Timezone.generate( "America/Los_Angeles" )
        
        def func():
            s = Wait(60, tz)
            s.destroy()
            
        grind(func, 1000000)
        
class TripHopStressTest(unittest.TestCase):
    def test_triphop_destroy(self):
        """Wait.destroy() completely destroys TripHop"""
        
        tz = Timezone()
        tz.add_period( TimezonePeriod( 0, 100000, 0 ) )
        cal = ServiceCalendar()
        cal.add_period( 0, 1*3600*24, ["WKDY","WKND"] )
        
        def func():
            s = TripHop(01, 20, "AA", cal, tz, 0, "WKDY")
            s.destroy()
            
        grind(func, 1000000)
        
class DAGStressTest(unittest.TestCase):
    
    def test_dag_destroy(self):
        """completely destroys DAG"""
        
        tz = Timezone()
        tz.add_period( TimezonePeriod( 0, 100000, 0 ) )
        cal = ServiceCalendar()
        cal.add_period( 0, 1*3600*24, ["WKDY","WKND"] )
        
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("A@10")
        s.add_vertex("A@20")
        s.add_vertex("A@30")
        s.add_edge( "A@10", "A@20", Wait(20, tz) )
        s.add_edge( "A@20", "A@30", Wait(30, tz) )
        s.add_edge( "A", "A@10", Wait(10, tz) )
        s.add_edge( "A", "A@20", Wait(20, tz) )
        s.add_edge( "A", "A@30", Wait(30, tz) )
        s.add_edge( "A@10", "A", Wait(10, tz) )
        s.add_edge( "A@20", "A", Wait(20, tz) )
        s.add_edge( "A@30", "A", Wait(30, tz) )
        
        s.add_vertex("B")
        s.add_vertex("B@10")
        s.add_vertex("B@20")
        s.add_vertex("B@30")
        s.add_edge( "B@10", "B@20", Wait(20, tz) )
        s.add_edge( "B@20", "B@30", Wait(30, tz) )
        s.add_edge( "B", "B@10", Wait(10, tz) )
        s.add_edge( "B", "B@20", Wait(20, tz) )
        s.add_edge( "B", "B@30", Wait(30, tz) )
        s.add_edge( "B@10", "B", Wait(10, tz) )
        s.add_edge( "B@20", "B", Wait(20, tz) )
        s.add_edge( "B@30", "B", Wait(30, tz) )
        
        s.add_edge( "A@10", "B@20", TripHop( 10, 20, "A1", cal, tz, 0, "WKDY" ) )
        s.add_edge( "A@20", "B@30", TripHop( 20, 30, "A2", cal, tz, 0, "WKDY" ) )
        s.add_edge( "B@10", "A@20", TripHop( 10, 20, "B1", cal, tz, 0, "WKDY" ) )
        s.add_edge( "B@20", "A@30", TripHop( 20, 30, "B2", cal, tz, 0, "WKDY" ) )
        
        def func():
            spt = s.shortest_path_tree("A", None, State(1,0))
            spt.destroy()
            
        grind(func, 500000)
        
class DeadendStressTest(unittest.TestCase):
    
    def test_dag_destroy(self):
        """completely destroys DAG"""
        
        tz = Timezone()
        tz.add_period( TimezonePeriod( 0, 100000, 0 ) )
        cal = ServiceCalendar()
        cal.add_period( 0, 1*3600*24, ["A"] )
        
        s = Graph()
        s.add_vertex("A")
        s.add_vertex("B")
        s.add_edge( "A", "B", TripHop( 10, 20, "A1", cal, tz, 0, "A" ) )
        
        def func():
            spt = s.shortest_path_tree("A", "B", State(1,20))
            spt.destroy()
            
        grind(func, 100000)

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
                 #WaitStressTest,
                 #DAGStressTest,
                 #TripHopStressTest,
                 #DeadendStressTest,
                 ]

    for testable in testables:
        suite = tl.loadTestsFromTestCase(testable)
        unittest.TextTestRunner(verbosity=2).run(suite)