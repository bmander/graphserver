from graphserver.core import *
import unittest
import StringIO
import sys

class TestPyPayload(unittest.TestCase):
    def _minimal_graph(self):
        g = Graph()
        
        g.add_vertex( "Seattle" )
        g.add_vertex( "Portland" )
        return g
    
    def test_basic(self):
        p = NoOpPyPayload(1.1)
        
    def test_cast(self):
        g = self._minimal_graph()
        e = NoOpPyPayload(1.2)
        
        ed = g.add_edge( "Seattle", "Portland", e )
        assert e == ed.payload
        ep = ed.payload # uses EdgePayload.from_pointer internally.
        assert e == ep
        assert ep.num == 1.2
    
        
    
    def test_walk(self):
        class IncTimePayload(GenericPyPayload):
            def walk_impl(self, state, walkopts):
                state.time = state.time + 10
                state.weight = 5
                return state
            
            def walk_back_impl(self, state, walkopts):
                state.time = state.time - 10
                state.weight = 0
                return state
            
        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", IncTimePayload())
        assert(isinstance(ed.payload,IncTimePayload))
        s = State(1,1)
        assert s.time == 1
        s1 = ed.walk(s, WalkOptions())
        assert s1
        assert s.time == 1
        assert s1.soul != s.soul
        assert s1.time == 11
        assert s1.weight == 5
        s2 = ed.walk_back(s1, WalkOptions())
        assert s2
        assert s2.time == 1
        assert s2.weight == 0
        g.destroy()
        
    def test_failures(self):
        class ExceptionRaiser(GenericPyPayload):
            def walk_bad_stuff(self, state, walkopts):
                raise Exception("I am designed to fail.")
            walk_impl = walk_bad_stuff
            walk_back_impl = walk_bad_stuff

        g = self._minimal_graph()
        ed = g.add_edge( "Seattle", "Portland", ExceptionRaiser())
                
        # save stdout so we can set it back the way we found it
        stderrsave = sys.stderr
        
        # get a string-file to catch things placed into stdout
        stderr_catcher = StringIO.StringIO()
        
        sys.stderr = stderr_catcher
                
        # this will barf into stdout
        ed.walk(State(1,0), WalkOptions())
        
        # the last line of the exception traceback just blurted out should be ...
        stderr_catcher.seek(0)
        self.assertEqual( stderr_catcher.read().split("\n")[-2] , "Exception: I am designed to fail." )

        # set up a new buffer to catch a traceback
        stderr_catcher = StringIO.StringIO()
        sys.stderr = stderr_catcher
        
        # blurt into it
        ed.walk_back(State(1,0), WalkOptions())
        
        # check that the last line of the traceback looks like we expect
        stderr_catcher.seek(0)
        self.assertEqual( stderr_catcher.read().split("\n")[-2] , "Exception: I am designed to fail." )
        
        g.destroy()
        
        sys.stderr = stderrsave
        
    def test_basic_graph(self):
        class MovingWalkway(GenericPyPayload):
            def walk_impl(self, state, walkopts):
                state.time = state.time + 10
                state.weight = 5
                return state
            
            def walk_back_impl(self, state, walkopts):
                state.time = state.time - 10
                state.weight = 0
                return state
        
        g = self._minimal_graph()
        g.add_edge( "Seattle", "Portland", MovingWalkway())
        spt = g.shortest_path_tree("Seattle", "Portland", State(0,0), WalkOptions())
        assert spt
        assert spt.__class__ == ShortestPathTree
        assert spt.get_vertex("Portland").state.weight==5
        assert spt.get_vertex("Portland").state.time==10

        spt.destroy()
        g.destroy()
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestPyPayload)
    unittest.TextTestRunner(verbosity=2).run(suite)
