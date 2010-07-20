from graphserver.core import *
import unittest

class TestStreet(unittest.TestCase):
    def test_street(self):
        s = Street("mystreet", 1.1)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert s.rise == 0
        assert s.fall == 0
        assert s.slog == 1
        assert s.way == 0
	assert s.external_id == 0
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' rise='0.000000' fall='0.000000' way='0' reverse='False'/>"

	s.external_id = 15
	assert Street.from_pointer( s.soul ).external_id == 15
        
        s.slog = 2500
        s.way = 232323
        assert s.slog == 2500
        assert s.way == 232323
        
    def test_street_elev(self):
        s = Street("mystreet", 1.1, 24.5, 31.2)
        assert s.name == "mystreet"
        assert s.length == 1.1
        assert round(s.rise,3) == 24.5
        assert round(s.fall,3) == 31.2
        assert s.to_xml() == "<Street name='mystreet' length='1.100000' rise='24.500000' fall='31.200001' way='0' reverse='False'/>"
        
    def test_destroy(self):
        s = Street("mystreet", 1.1)
        s.destroy()
        
        assert s.soul==None
        
    def test_street_big_length(self):
        s = Street("longstreet", 240000)
        assert s.name == "longstreet"
        assert s.length == 240000

        assert s.to_xml() == "<Street name='longstreet' length='240000.000000' rise='0.000000' fall='0.000000' way='0' reverse='False'/>"
        
    def test_walk(self):
        s = Street("longstreet", 2)
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        after = s.walk(State(0,0),wo)
        assert after.time == 2
        assert after.weight == 2
        assert after.dist_walked == 2
        assert after.prev_edge.type == 0
        assert after.prev_edge.name == "longstreet"
        assert after.num_agencies == 0
        
    def test_walk_slog(self):
        s = Street("longstreet", 2)
        s.slog = 10
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        after = s.walk(State(0,0),wo)
        assert after.time == 2
        assert after.weight == 20
        assert after.dist_walked == 2
        assert after.prev_edge.type == 0
        assert after.prev_edge.name == "longstreet"
        assert after.num_agencies == 0
        
    def test_walk_back(self):
        s = Street("longstreet", 2)
        
        wo = WalkOptions()
        wo.walking_speed = 1
        
        before = s.walk_back(State(0,100),wo)
        
        assert before.time == 98
        assert before.weight == 2
        assert before.dist_walked == 2.0
        assert before.prev_edge.type == 0
        assert before.prev_edge.name == "longstreet"
        assert before.num_agencies == 0
        
    def test_street_turn(self):
        wo = WalkOptions()
        wo.turn_penalty = 20
        wo.walking_speed = 1

        e0 = Street("a1", 10)
        e0.way = 42
        e1 = Street("a2", 10)
        e1.way = 43
        s0 = State(0,0)
        s0.prev_edge = e0
        
        s1 = e1.walk(s0, wo)
        assert s1.weight == 30
        
        
    def test_getstate(self):
        s = Street("longstreet", 2)
        
        assert s.__getstate__() == ('longstreet', 2.0, 0.0, 0.0, 1.0,0,False)
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestStreet)
    unittest.TextTestRunner(verbosity=2).run(suite)
