from stress_utils import get_mem_usage
from structures import *

"""
print get_mem_usage()

g = Graph()
for i in xrange(1000000):
    v = Vertex("bogus")
    del v
    
print get_mem_usage()
"""

def test_state_destroy():
    mperc, m0 = get_mem_usage()

    g = Graph()
    for i in xrange(1000000):
        s = State(0)
        s.destroy()
        
    mperc, m1 = get_mem_usage()
    
    print m0, m1
    assert m1 <= m0
    
if __name__=='__main__':
    test_state_delete()