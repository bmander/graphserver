import unittest

from graphserver.core import ListNode


class TestListNode(unittest.TestCase):
    def test_list_node(self):
        ln = ListNode()

        assert ln


if __name__ == "__main__":
    tl = unittest.TestLoader()

    suite = tl.loadTestsFromTestCase(TestListNode)
    unittest.TextTestRunner(verbosity=2).run(suite)
