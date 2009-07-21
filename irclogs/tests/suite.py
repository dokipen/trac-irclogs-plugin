import unittest
from irclogs.tests.api import *
from irclogs.tests.file_parser import *
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ApiTestCase, 'test'))
    suite.addTest(unittest.makeSuite(FileIRCLogProviderTestCase, 'test'))

    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
