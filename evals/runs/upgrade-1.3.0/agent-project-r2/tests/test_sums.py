import unittest
from sums import total

class TotalTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(total([2, 3]), 5)

    def test_negative(self):
        self.assertEqual(total([-2, -3]), -5)

    def test_zeros(self):
        self.assertEqual(total([0, 0, 0]), 0)

    def test_mixed(self):
        self.assertEqual(total([4, 0, -7, 2]), -1)

    def test_empty(self):
        self.assertEqual(total([]), 0)

    def test_input_unchanged(self):
        items = [4, 0, -7, 2]
        original = items.copy()

        total(items)

        self.assertEqual(items, original)
