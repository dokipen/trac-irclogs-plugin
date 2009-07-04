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

        self.simplegozerlines = (
            '2009-07-03 22:18:00 | <rcorsaro> !chatlog-on',
            '2009-07-03 22:19:00 | <gozerbot> chatlog enabled on (default,#test2)',
            '2009-07-03 22:20:00 | gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has left',
            '2009-07-03 22:21:00 | gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has joined',
            '2009-07-03 22:22:00 | rcorsaro (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving',
            '2009-07-03 22:23:00 | * rcorsaro2 is strong',
            '2009-07-03 22:24:00 | * rcorsaro feels strange',
            '2009-07-03 22:25:00 | gozerbot was kicked by rcorsaro2 (rcorsaro2)',
            '2009-07-03 22:26:00 | rcorsaro2 sets mode: -o gozerbot',
            '2009-07-03 22:27:00 | rcorsaro2 changes topic to "testing topic"',
            '2009-07-03 22:28:00 | rcorsaro (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2',
            '2009-07-03 22:29:00 | -rcorsaro- hello there',
            '* SOME SPECIAL MESSAGE *',
        )

        # supybot emulation on gozerbot
        self.supygozerlines = (
            '2009-07-03T22:18:00  <gozerbot> chatlog enabled on (default,#test2)',
            '2009-07-03T22:19:00  <rcorsaro> hello',
            '2009-07-03T22:20:00  *** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has left',
            '2009-07-03T22:21:00  *** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has joined',
            '2009-07-03T22:22:00  *** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving',
            '2009-07-03T22:23:00  * rcorsaro is strong',
            '2009-07-03T22:24:00  * rcorsaro is manly',
            '2009-07-03T22:25:00  *** rcorsaro_ was kicked by rcorsaro (rcorsaro)',
            '2009-07-03T22:26:00  *** rcorsaro sets mode: +o rcorsaro_',
            '2009-07-03T22:27:00  *** rcorsaro changes topic to "testing topic"',
            '2009-07-03T22:28:00  *** lsjdf (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2',
            '2009-07-03T22:29:00  -rcorsaro- hello there',
            '* SOME SPECIAL MESSAGE *',
        )

    def test_target_tz(self):
        tz = timezone('America/New_York')
        results = [i for i in self.out.parse_lines(
            self.supylines, 
            target_tz=tz
        )]

        def _date(d):
            t = strptime(d, "%Y%m%d%H%M%S")
            dt = datetime(*t[:6]).replace(tzinfo=tz)
            return tz.normalize(dt)

        self.assertEquals(_date('20080502212819'), results[0]['timestamp'])
        self.assertEquals(_date("20080502213022"), results[1]['timestamp'])
        self.assertEquals(_date("20080502213025"), results[2]['timestamp'])
        self.assertEquals(_date("20080502213026"), results[3]['timestamp'])
        self.assertEquals(_date("20080502213027"), results[4]['timestamp'])
        self.assertEquals(_date("20080502213127"), results[5]['timestamp'])
        self.assertEquals(_date("20080502213227"), results[6]['timestamp'])
        self.assertEquals(_date("20080502213327"), results[7]['timestamp'])
        self.assertEquals(_date("20080502213427"), results[8]['timestamp'])
        self.assertEquals(_date("20080502213527"), results[9]['timestamp'])
        self.assertEquals(_date("20080502213627"), results[10]['timestamp'])
        self.assertEquals(_date("20080502213727"), results[11]['timestamp'])

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
    
    def test_parse_simple_gozerbot(self):
        f = self.out.format('gozer')
        results = [i for i in self.out.parse_lines(self.simplegozerlines, f)]

        def _date(d):
            t = strptime(d, "%Y%m%d%H%M%S")
            return datetime(*t[:6]).replace(tzinfo=timezone('utc'))

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(_date("20090703221800"), results[0]['timestamp'])
        self.assertEquals('<rcorsaro> !chatlog-on', results[0]['message'])
        self.assertEquals('rcorsaro', results[0]['nick'])
        self.assertEquals('!chatlog-on', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(_date("20090703221900"), results[1]['timestamp'])
        self.assertEquals('<gozerbot> chatlog enabled on (default,#test2)', results[1]['message'])
        self.assertEquals('gozerbot', results[1]['nick'])
        self.assertEquals('chatlog enabled on (default,#test2)', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(_date("20090703222000"), results[2]['timestamp'])
        self.assertEquals('gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has left', results[2]['message'])
        self.assertEquals('gozerbot', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(_date("20090703222100"), results[3]['timestamp'])
        self.assertEquals('gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has joined', results[3]['message'])
        self.assertEquals('gozerbot', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(_date("20090703222200"), results[4]['timestamp'])
        self.assertEquals('rcorsaro (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving', results[4]['message'])
        self.assertEquals('rcorsaro', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(_date("20090703222300"), results[5]['timestamp'])
        self.assertEquals('* rcorsaro2 is strong', results[5]['message'])
        self.assertEquals('rcorsaro2', results[5]['nick'])
        self.assertEquals('is strong', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(_date("20090703222400"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro feels strange', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('feels strange', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(_date("20090703222500"), results[7]['timestamp'])
        self.assertEquals('gozerbot was kicked by rcorsaro2 (rcorsaro2)', results[7]['message'])
        self.assertEquals('rcorsaro2', results[7]['nick'])
        self.assertEquals('gozerbot', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(_date("20090703222600"), results[8]['timestamp'])
        self.assertEquals('rcorsaro2 sets mode: -o gozerbot', results[8]['message'])
        self.assertEquals('rcorsaro2', results[8]['nick'])
        self.assertEquals('-o gozerbot', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(_date("20090703222700"), results[9]['timestamp'])
        self.assertEquals('rcorsaro2 changes topic to "testing topic"', results[9]['message'])
        self.assertEquals('rcorsaro2', results[9]['nick'])
        self.assertEquals('testing topic', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(_date("20090703222800"), results[10]['timestamp'])
        self.assertEquals('rcorsaro (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2', results[10]['message'])
        self.assertEquals('rcorsaro', results[10]['nick'])
        self.assertEquals('rcorsaro2', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(_date("20090703222900"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[12]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[12]['message'])
    
    # gozerbot in supy emulation mode
    def test_parse_supy_gozerbot(self):
        results = [i for i in self.out.parse_lines(self.supygozerlines)]

        def _date(d):
            t = strptime(d, "%Y%m%d%H%M%S")
            return datetime(*t[:6]).replace(tzinfo=timezone('utc'))

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(_date("20090703221800"), results[0]['timestamp'])
        self.assertEquals('<gozerbot> chatlog enabled on (default,#test2)', results[0]['message'])
        self.assertEquals('gozerbot', results[0]['nick'])
        self.assertEquals('chatlog enabled on (default,#test2)', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(_date("20090703221900"), results[1]['timestamp'])
        self.assertEquals('<rcorsaro> hello', results[1]['message'])
        self.assertEquals('rcorsaro', results[1]['nick'])
        self.assertEquals('hello', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(_date("20090703222000"), results[2]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has left', results[2]['message'])
        self.assertEquals('rcorsaro_', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(_date("20090703222100"), results[3]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has joined', results[3]['message'])
        self.assertEquals('rcorsaro_', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(_date("20090703222200"), results[4]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving', results[4]['message'])
        self.assertEquals('rcorsaro_', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(_date("20090703222300"), results[5]['timestamp'])
        self.assertEquals('* rcorsaro is strong', results[5]['message'])
        self.assertEquals('rcorsaro', results[5]['nick'])
        self.assertEquals('is strong', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(_date("20090703222400"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro is manly', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('is manly', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(_date("20090703222500"), results[7]['timestamp'])
        self.assertEquals('*** rcorsaro_ was kicked by rcorsaro (rcorsaro)', results[7]['message'])
        self.assertEquals('rcorsaro', results[7]['nick'])
        self.assertEquals('rcorsaro_', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(_date("20090703222600"), results[8]['timestamp'])
        self.assertEquals('*** rcorsaro sets mode: +o rcorsaro_', results[8]['message'])
        self.assertEquals('rcorsaro', results[8]['nick'])
        self.assertEquals('+o rcorsaro_', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(_date("20090703222700"), results[9]['timestamp'])
        self.assertEquals('*** rcorsaro changes topic to "testing topic"', results[9]['message'])
        self.assertEquals('rcorsaro', results[9]['nick'])
        self.assertEquals('testing topic', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(_date("20090703222800"), results[10]['timestamp'])
        self.assertEquals('*** lsjdf (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2', results[10]['message'])
        self.assertEquals('lsjdf', results[10]['nick'])
        self.assertEquals('rcorsaro2', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(_date("20090703222900"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[12]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[12]['message'])

    def test_default_format(self):
        df = self.out.default_format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['path'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_supy_format(self):
        df = self.out.format('supy')
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['path'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_nonexistant_format(self):
        df = self.out.format('sdflkjlskjf')
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['path'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_gozer_format(self):
        df = self.out.format('gozer')
        self.assertEquals('/home/gozerbot/.gozerbot/', df['basepath'])
        self.assertEquals('logs/trac/%(channel)s.%Y%m%d.log', df['path'])
        self.assertEquals('%Y-%m-%d %H:%M:%S', df['timestamp_format'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileIRCLogProviderTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
