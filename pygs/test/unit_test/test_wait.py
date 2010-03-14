from graphserver.core import Wait, Timezone, TimezonePeriod, State, WalkOptions
import unittest

class TestWait(unittest.TestCase):
    def test_wait(self):
        waitend = 100
        tz = Timezone()
        tz.add_period(TimezonePeriod(0,100000,0))
        w = Wait(waitend, tz)
        assert w.end == waitend
        assert w.timezone.soul == tz.soul
        assert w.to_xml() == "<Wait end='100' />"

        s = State(1,0)
        sprime = w.walk(s, WalkOptions())
        assert sprime.time == 100
        assert sprime.weight == 100

        s = State(1, 150)
        sprime = w.walk_back(s, WalkOptions())
        assert sprime.time == 100
        assert sprime.weight == 50
        
        s = State(1, 86400)
        sprime = w.walk(s, WalkOptions())
        assert sprime.time == 86500
        assert sprime.weight == 100

        w.destroy()
        
        tz = Timezone()
        tz.add_period(TimezonePeriod(0,100000,-20))
        w = Wait(100, tz)
        assert w.end == 100
        assert w.timezone.soul == tz.soul
        s = State(1, 86400)
        sprime = w.walk(s, WalkOptions())
        assert sprime.weight == 120
        
    def test_august(self):
        # noon, -7 hours off UTC, as America/Los_Angeles in summer
        tz = Timezone.generate("America/Los_Angeles")
        w = Wait(43200, tz)
        
        # one calendar, noon august 27, America/Los_Angeles
        s = State(1, 1219863600)
        
        assert w.walk(s, WalkOptions()).time == 1219863600
        
        # one calendar, 11:55 AM August 27 2008, America/Los_Angeles
        s = State(1, 1219863300)
        assert w.walk(s, WalkOptions()).time == 1219863600
        assert w.walk(s, WalkOptions()).weight == 300
        
    def test_getstate(self):
        # noon, -7 hours off UTC, as America/Los_Angeles in summer
        tz = Timezone.generate("America/Los_Angeles")
        w = Wait(43200, tz)
        
        assert w.__getstate__() == (43200, tz.soul)
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestWait)
    unittest.TextTestRunner(verbosity=2).run(suite)
