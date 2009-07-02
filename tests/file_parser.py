import unittest
from time import strptime
from datetime import datetime
from pytz import timezone

from trac.core import *
from trac.test import EnvironmentStub

from irclogs.provider.file import *

class FileIRCLogProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()
        self.out = FileIRCLogProvider(self.env)
        self.supylines = (
            '2008-05-03T02:28:19  <rcorsaro> will it work if I install it?',
            '2008-05-03T02:30:22  <dgynn> ok.  i copied it over',
            '2008-05-03T02:30:25  *** dgynn has left #etf',
            '2008-05-03T02:30:26  *** dgynn has joined #etf',
            '2008-05-03T02:30:27  *** dgynn has quit IRC',
            '2008-05-03T02:31:27  * cbalan feels lonely...',
            '2008-05-03T02:32:27  * rcorsaro nods',
            '2008-05-03T02:33:27  *** vmiliano was kicked by dgynn (dgynn)',
            '2008-05-03T02:34:27  *** rcorsaro sets mode: +o cbalan',
            '2008-05-03T02:35:27  *** dgynn changes topic to "Enterprise Tools and Frameworks"',
            '2008-05-03T02:36:27  *** rcorsaro is now known as bobby-robert',
            '2008-05-03T02:37:27  -rcorsaro- hello there',
            '* SOME SPECIAL MESSAGE *',
        )

    def test_parse_supybot(self):
        results = [i for i in self.out.parse_lines(self.supylines)]

        def _date(d):
            t = strptime(d, "%Y%m%d%H%M%S")
            return datetime(*t[:6]).replace(tzinfo=timezone('utc'))

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(_date("20080503022819"), results[0]['timestamp'])
        self.assertEquals('<rcorsaro> will it work if I install it?', results[0]['message'])
        self.assertEquals('rcorsaro', results[0]['nick'])
        self.assertEquals('will it work if I install it?', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(_date("20080503023022"), results[1]['timestamp'])
        self.assertEquals('<dgynn> ok.  i copied it over', results[1]['message'])
        self.assertEquals('dgynn', results[1]['nick'])
        self.assertEquals('ok.  i copied it over', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(_date("20080503023025"), results[2]['timestamp'])
        self.assertEquals('*** dgynn has left #etf', results[2]['message'])
        self.assertEquals('dgynn', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(_date("20080503023026"), results[3]['timestamp'])
        self.assertEquals('*** dgynn has joined #etf', results[3]['message'])
        self.assertEquals('dgynn', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(_date("20080503023027"), results[4]['timestamp'])
        self.assertEquals('*** dgynn has quit IRC', results[4]['message'])
        self.assertEquals('dgynn', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(_date("20080503023127"), results[5]['timestamp'])
        self.assertEquals('* cbalan feels lonely...', results[5]['message'])
        self.assertEquals('cbalan', results[5]['nick'])
        self.assertEquals('feels lonely...', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(_date("20080503023227"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro nods', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('nods', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(_date("20080503023327"), results[7]['timestamp'])
        self.assertEquals('*** vmiliano was kicked by dgynn (dgynn)', results[7]['message'])
        self.assertEquals('dgynn', results[7]['nick'])
        self.assertEquals('vmiliano', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(_date("20080503023427"), results[8]['timestamp'])
        self.assertEquals('*** rcorsaro sets mode: +o cbalan', results[8]['message'])
        self.assertEquals('rcorsaro', results[8]['nick'])
        self.assertEquals('+o cbalan', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(_date("20080503023527"), results[9]['timestamp'])
        self.assertEquals('*** dgynn changes topic to "Enterprise Tools and Frameworks"', results[9]['message'])
        self.assertEquals('dgynn', results[9]['nick'])
        self.assertEquals('Enterprise Tools and Frameworks', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(_date("20080503023627"), results[10]['timestamp'])
        self.assertEquals('*** rcorsaro is now known as bobby-robert', results[10]['message'])
        self.assertEquals('rcorsaro', results[10]['nick'])
        self.assertEquals('bobby-robert', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(_date("20080503023727"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[12]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[12]['message'])
    
    def test_gozer_options(self):
        print [i for i in self.out.config.sections()]

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileIRCLogProviderTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
