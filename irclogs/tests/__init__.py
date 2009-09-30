import unittest

def suite():
    from irclogs.tests import search, file_parser, api
    suite = unittest.TestSuite()
    suite.addTest(api.suite())
    suite.addTest(file_parser.suite())
    suite.addTest(search.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')

