from graphserver.core import *
import unittest

class TestListNode(unittest.TestCase):
    def test_list_node(self):
        l = ListNode()
                
        assert l
        
if __name__ == '__main__':
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestListNode)
    unittest.TextTestRunner(verbosity=2).run(suite)