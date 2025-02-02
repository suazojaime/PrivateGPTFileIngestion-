import unittest
import doctest
import mstarapplib 

def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(mstarapplib))
    return tests


if __name__ == '__main__':
    unittest.main()

