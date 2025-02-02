import unittest

from packageMatchers import createPackageMatcher

class PackageMatchersTest(unittest.TestCase):
    
    def test_matchExact(self):
        matcher = createPackageMatcher('foo:1.0')
        self.assertTrue(matcher.matches('foo:1'))
        self.assertTrue(matcher.matches('foo:1.0'))
        self.assertTrue(matcher.matches('foo:1.0.0'))
        self.assertFalse(matcher.matches('foo:1.0.1'))
        self.assertFalse(matcher.matches('foo.1.1'))
        self.assertFalse(matcher.matches('foo.2'))
        self.assertFalse(matcher.matches('bar:1.0'))

    def test_matchCompatible(self):
        matcher = createPackageMatcher(source='foo:1.0', matchingType='compatible')
        self.assertTrue(matcher.matches('foo:1.0'))
        self.assertTrue(matcher.matches('foo:1'))
        self.assertTrue(matcher.matches('foo:1.0.0'))
        self.assertTrue(matcher.matches('foo:1.0.1'))
        self.assertFalse(matcher.matches('foo.1.1'))
        self.assertFalse(matcher.matches('foo.2'))
        self.assertFalse(matcher.matches('bar:1.0'))

if __name__ == '__main__':
    unittest.main()
