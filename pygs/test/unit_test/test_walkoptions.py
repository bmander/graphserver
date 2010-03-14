import unittest
from graphserver.core import *

class TestWalkOptions(unittest.TestCase):
    def test_basic(self):
        wo = WalkOptions()
        
        assert wo
        
        assert wo.transfer_penalty == 0
        assert wo.turn_penalty == 0
        assert wo.walking_speed*100//1 == 607.0
        assert wo.walking_reluctance == 1.0
        assert wo.max_walk == 10000
        assert round(wo.walking_overage,3) == 0.1
        
        wo.transfer_penalty = 50
        assert wo.transfer_penalty == 50
        
        wo.turn_penalty = 3
        assert wo.turn_penalty == 3
        
        wo.walking_speed = 1.05
        assert round(wo.walking_speed*100) == 105.0
        
        wo.walking_reluctance = 2.0
        assert wo.walking_reluctance == 2.0
        
        wo.max_walk = 100
        assert wo.max_walk == 100
        
        wo.walking_overage = 1.0
        assert wo.walking_overage == 1.0
        
        wo.uphill_slowness = 1.5
        assert wo.uphill_slowness == 1.5
        
        wo.downhill_fastness = 3.4
        assert round(wo.downhill_fastness,3) == 3.4
        
        wo.hill_reluctance = 1.4
        assert round(wo.hill_reluctance,3) == 1.4
        
        wo.destroy()
        assert wo.soul == None
        
    def test_from_ptr(self):
        wo = WalkOptions()
        wo.transfer_penalty = 10
        wo1 = WalkOptions.from_pointer(wo.soul)
        assert wo.transfer_penalty == wo1.transfer_penalty
        assert wo1.soul == wo.soul
        wo.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestWalkOptions)
    unittest.TextTestRunner(verbosity=2).run(suite)