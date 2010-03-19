from graphserver.vector import Vector
import unittest

class TestVector(unittest.TestCase):
    def test_basic(self):
        # basic test
        vec = Vector(expand_delta=40)

        assert vec.num_elements == 0
        assert vec.num_alloc == 50
        assert vec.expand_delta == 40

        vec.expand( 50 )

        assert vec.num_alloc == 100

        vec.add( 11 )
        assert vec.get( 0 ) == 11
        vec.add( 15 )
        assert vec.get( 0 ) == 11
        assert vec.get( 1 ) == 15

        del(vec)

    def test_expand(self):
        # expand test

        vec = Vector(init_size=1, expand_delta=10)
        assert vec.num_alloc == 1
        assert vec.num_elements == 0

        vec.add( 3 )
        assert vec.num_alloc == 1
        assert vec.num_elements == 1
        assert vec.get(0) == 3

        vec.add( 5 )
        assert vec.num_alloc == 11
        assert vec.num_elements == 2
        assert vec.get(0) == 3
        assert vec.get(1) == 5
        
if __name__ == '__main__':

    unittest.main()