from graphserver.core import *
import unittest

class TestElapseTime(unittest.TestCase):
    def test_new(self):
        s = ElapseTime(120)
        assert s.seconds == 120
        assert s.to_xml() == "<ElapseTime seconds='120' />"
        
    def test_destroy(self):
        s = ElapseTime(1)
        s.destroy()
        
        assert s.soul==None
        
    def test_big_seconds(self):
        s = ElapseTime(240000)
        assert s.seconds == 240000

        assert s.to_xml() == "<ElapseTime seconds='240000' />"
        
    def test_walk(self):
        s = ElapseTime(2)
        
        after = s.walk(State(0,0),WalkOptions())
        assert after.time == 2
        assert after.weight == 2
        assert after.dist_walked == 0
        assert after.prev_edge.type == 14
        assert after.num_agencies == 0
        
    def test_walk_back(self):
        s = ElapseTime(2)
        
        before = s.walk_back(State(0,100),WalkOptions())
        
        assert before.time == 98
        assert before.weight == 2
        assert before.dist_walked == 0
        assert before.prev_edge.type == 14
        assert before.num_agencies == 0
        
    def test_getstate(self):
        s = ElapseTime(2)
        
        assert s.__getstate__() == 2
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestElapseTime)
    unittest.TextTestRunner(verbosity=2).run(suite)