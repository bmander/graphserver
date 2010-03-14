from graphserver.core import Link, State, WalkOptions
import unittest

class TestLink(unittest.TestCase):
    def link_test(self):
        l = Link()
        assert l
        assert str(l)=="<Link name='LINK'/>"
        
    def test_destroy(self):
        l = Link()
        l.destroy()
        
        assert l.soul==None
        
    def test_name(self):
        l = Link()
        assert l.name == "LINK"
        
    def test_walk(self):
        l = Link()
        
        after = l.walk(State(1,0), WalkOptions())
        
        assert after.time==0
        assert after.weight==0
        assert after.dist_walked==0
        assert after.prev_edge.type == 3
        assert after.prev_edge.name == "LINK"
        assert after.num_agencies == 1
        
    def test_walk_back(self):
        l = Link()
        
        before = l.walk_back(State(1,0), WalkOptions())
        
        assert before.time == 0
        assert before.weight == 0
        assert before.dist_walked == 0.0
        assert before.prev_edge.type == 3
        assert before.prev_edge.name == "LINK"
        assert before.num_agencies == 1
        
    def test_getstate(self):
        l = Link()
        assert l.__getstate__() == tuple([])
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestLink)
    unittest.TextTestRunner(verbosity=2).run(suite)