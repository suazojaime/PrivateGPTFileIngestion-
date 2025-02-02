import unittest

from packages import PackageDependency

class PackageDependencyTest(unittest.TestCase):

    def test_initFailsWhenNameIsNone(self):
        try:
            PackageDependency(name=None)
        except Exception:
            return
        self.assertTrue(False, "Create a package dependency without a name")

    def test_init(self):
        dependency = PackageDependency(name='foo')
        self.assertTrue(dependency.name == 'foo')
        self.assertTrue(dependency.version is None)
        self.assertTrue(dependency.target is None)

        dependency = PackageDependency(name='foo', version='1.0-SNAPSHOT')
        self.assertTrue(dependency.name == 'foo')
        self.assertTrue(dependency.version == '1.0-SNAPSHOT')
        self.assertTrue(dependency.target is None)

        dependency = PackageDependency(name='foo', version='1.0-SNAPSHOT', target='server')
        self.assertTrue(dependency.name == 'foo')
        self.assertTrue(dependency.version == '1.0-SNAPSHOT')
        self.assertTrue(dependency.target == 'server')

if __name__ == '__main__':
    unittest.main()
