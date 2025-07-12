import unittest

from graphserver.core import Link, State, WalkOptions


class TestLink(unittest.TestCase):
    def link_test(self):
        ln = Link()
        assert ln
        assert str(ln) == "<Link name='LINK'/>"

    def test_destroy(self):
        ln = Link()
        ln.destroy()

        assert ln.soul is None

    def test_name(self):
        ln = Link()
        assert ln.name == "LINK"

    def test_walk(self):
        ln = Link()

        after = ln.walk(State(1, 0), WalkOptions())

        assert after.time == 0
        assert after.weight == 0
        assert after.dist_walked == 0
        assert after.prev_edge.type == 3
        assert after.prev_edge.name == "LINK"
        assert after.num_agencies == 1

    def test_walk_back(self):
        ln = Link()

        before = ln.walk_back(State(1, 0), WalkOptions())

        assert before.time == 0
        assert before.weight == 0
        assert before.dist_walked == 0.0
        assert before.prev_edge.type == 3
        assert before.prev_edge.name == "LINK"
        assert before.num_agencies == 1

    def test_getstate(self):
        ln = Link()
        assert ln.__getstate__() == tuple([])


if __name__ == "__main__":
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestLink)
    unittest.TextTestRunner(verbosity=2).run(suite)
