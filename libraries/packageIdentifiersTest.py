import unittest

from packages import PackageIdentifier, createPackageIdentifier


class PackageIdentifiersTest(unittest.TestCase):

    def test_initFailsWhenSourceIsNone(self):
        try:
            PackageIdentifier(None)
        except Exception:
            return
        self.assertTrue(False, 'Created PackageIdentifier when source=None')

    def test_init(self):
        id = PackageIdentifier(name='foo')
        self.assertEquals(id.name, 'foo')
        self.assertEquals(id.version, None)

        id = PackageIdentifier(name='foo', version='1.2.3-SNAPSHOT')
        self.assertEquals(id.name, 'foo')
        self.assertEquals(id.version, '1.2.3-SNAPSHOT')

    def test_convertPackageIdentifierToString(self):
        self.assertEquals(str(createPackageIdentifier('foo')), 'foo')
        self.assertEquals(str(createPackageIdentifier('foo:1.2.3')), 'foo:1.2.3')
        self.assertEquals(str(createPackageIdentifier('foo:1.2.3-SNAPSHOT')), 'foo:1.2.3-SNAPSHOT')
        self.assertEquals(str(createPackageIdentifier('mstar:2017.1-M1-1')), 'mstar:2017.1-M1-1')

    def test_createPackageIdentifier(self):
        table = [\
            {'source':'foo', 'name':'foo', 'version':None}, \
            {'source':'foo:1.0', 'name':'foo', 'version':'1.0'}, \
            {'source':'foo:1.0-SNAPSHOT', 'name':'foo', 'version':'1.0-SNAPSHOT'}, \
            {'source':PackageIdentifier(name='foo'), 'name':'foo', 'version':None}, \
            {'source':PackageIdentifier(name='foo', version='1.2.3'), 'name':'foo', 'version':'1.2.3'}, \
            {'source':{'name':'foo'}, 'name':'foo', 'version':None}, \
            {'source':{'name':'foo', 'version':'1.0-SNAPSHOT'}, 'name':'foo', 'version':'1.0-SNAPSHOT'}, \
            {'source':u'foo:1.0-SNAPSHOT', 'name':'foo', 'version':'1.0-SNAPSHOT'}, \
            ]

        for row in table:
            (source,name,version) = (row['source'],row['name'], row['version'])
            id = createPackageIdentifier(source)
            self.assertEquals(id.name, name, 'Invalid name for source %s: expected %s but found %s' 
                              % (source, name, id.name))
            self.assertEquals(id.version, version, 'Invalid version for source %s: expected %s but found %s'
                              % (source, version, id.version))

    def test_createPackageIdentifierFailsWhenInvalidString(self):
        table = [':1', ':1.0', ':1.0-SNAPSHOT', 'foo:x', 'foo:1.x', 'foo:1.0:2.0']
        for string in table:
            try:
                createPackageIdentifier(string)
            except Exception:
                continue
            self.assertTrue(False, "Create package identifier from invalid string '%s'" % string)

if __name__ == '__main__':
    unittest.main()
