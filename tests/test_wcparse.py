# -*- coding: utf-8 -*-
"""Tests for `wcparse`."""
import unittest
import re
import copy
import wcmatch._wcparse as _wcparse


class TestWcparse(unittest.TestCase):
    """Test `wcparse`."""

    def test_hash(self):
        """Test hashing of search."""

        p1 = re.compile('test')
        p2 = re.compile('test')
        p3 = re.compile('test', re.X)
        p4 = re.compile(b'test')

        w1 = _wcparse.WcRegexp((p1,))
        w2 = _wcparse.WcRegexp((p2,))
        w3 = _wcparse.WcRegexp((p3,))
        w4 = _wcparse.WcRegexp((p4,))
        w5 = _wcparse.WcRegexp((p1,), (p3,))

        self.assertTrue(w1 == w2)
        self.assertTrue(w1 != w3)
        self.assertTrue(w1 != w4)
        self.assertTrue(w1 != w5)

        w6 = copy.copy(w1)
        self.assertTrue(w1 == w6)
        self.assertTrue(w6 in {w1})

    def test_preprocessor_sequence(self):
        """Test the integrity of the order of preprocessors."""

        results = _wcparse.expand(
            'test@(this{|that,|other})|*.py',
            _wcparse.BRACE | _wcparse.SPLIT | _wcparse.EXTMATCH
        )
        self.assertEqual(sorted(results), sorted(['test@(this|that)', 'test@(this|other)', '*.py', '*.py']))

    def test_compile_expansion_okay(self):
        """Test expansion is okay."""

        self.assertEqual(len(_wcparse.compile('{1..10}', _wcparse.BRACE)), 10)

    def test_compile_unique_optimization_okay(self):
        """Test that redundant patterns are reduced in compile."""

        self.assertEqual(len(_wcparse.compile('|'.join(['a'] * 10), _wcparse.SPLIT, 10)), 1)

    def test_translate_expansion_okay(self):
        """Test expansion is okay."""

        p1, p2 = _wcparse.translate('{1..10}', _wcparse.BRACE, 10)
        count = len(p1) + len(p2)
        self.assertEqual(count, 10)

    def test_translate_unique_optimization_okay(self):
        """Test that redundant patterns are reduced in translate."""
        p1, p2 = _wcparse.translate('|'.join(['a'] * 10), _wcparse.SPLIT, 10)
        count = len(p1) + len(p2)
        self.assertEqual(count, 1)

    def test_expansion_limt(self):
        """Test expansion limit."""

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile('{1..11}', _wcparse.BRACE, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile('|'.join(['a'] * 11), _wcparse.SPLIT, 10)

        with self.assertRaises(_wcparse.PatternLimitException):
            _wcparse.compile(
                '{{{},{}}}'.format('|'.join(['a'] * 6), '|'.join(['a'] * 5)),
                _wcparse.SPLIT | _wcparse.BRACE, 10
            )

    def test_expansion_no_limit_compile(self):
        """Test no expansion limit compile."""

        self.assertEqual(len(_wcparse.compile('{1..11}', _wcparse.BRACE, -1)), 11)

    def test_expansion_no_limit_translate(self):
        """Test no expansion limit translate."""

        p1, p2 = _wcparse.translate('{1..11}', _wcparse.BRACE, 0)
        count = len(p1) + len(p2)
        self.assertEqual(count, 11)
