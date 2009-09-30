import unittest
from time import strptime
from datetime import datetime
from pytz import timezone
import re

from trac.core import *
from trac.test import EnvironmentStub

from irclogs.provider.file import FileIRCLogProvider
from irclogs.api import merge_iseq, IRCChannelManager

class FileIRCLogProviderTestCase(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()
        self.out = FileIRCLogProvider(self.env)
        self.chmgr = IRCChannelManager(self.env)
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
            '2008-08-15T02:37:27  -rcorsaro- goodbye there',
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
        tz = 'America/New_York'
        tzo = timezone(tz)
        results = [i for i in self.out.parse_lines(
            self.supylines, 
            self.chmgr.channel(None),
            target_tz=tzo
        )]

        
        self.assertEquals(self._date('20080502222819', tz), results[0]['timestamp'])
        self.assertEquals(self._date("20080502223022", tz), results[1]['timestamp'])
        self.assertEquals(self._date("20080502223025", tz), results[2]['timestamp'])
        self.assertEquals(self._date("20080502223026", tz), results[3]['timestamp'])
        self.assertEquals(self._date("20080502223027", tz), results[4]['timestamp'])
        self.assertEquals(self._date("20080502223127", tz), results[5]['timestamp'])
        self.assertEquals(self._date("20080502223227", tz), results[6]['timestamp'])
        self.assertEquals(self._date("20080502223327", tz), results[7]['timestamp'])
        self.assertEquals(self._date("20080502223427", tz), results[8]['timestamp'])
        self.assertEquals(self._date("20080502223527", tz), results[9]['timestamp'])
        self.assertEquals(self._date("20080502223627", tz), results[10]['timestamp'])
        self.assertEquals(self._date("20080502223727", tz), results[11]['timestamp'])
        self.assertEquals(self._date("20080502223727", tz), results[11]['timestamp'])

    def _date(self, d, tz='utc'):
        t = strptime(d, "%Y%m%d%H%M%S")
        tz = timezone(tz)
        dt = tz.localize(datetime(*t[:6]))
        return tz.normalize(dt)


    def test_parse_supybot(self):
        f = self.chmgr.channel(None)
        results = [i for i in self.out.parse_lines(self.supylines, f)]

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(self._date("20080503022819"), results[0]['timestamp'])
        self.assertEquals('<rcorsaro> will it work if I install it?', results[0]['message'])
        self.assertEquals('rcorsaro', results[0]['nick'])
        self.assertEquals('will it work if I install it?', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(self._date("20080503023022"), results[1]['timestamp'])
        self.assertEquals('<dgynn> ok.  i copied it over', results[1]['message'])
        self.assertEquals('dgynn', results[1]['nick'])
        self.assertEquals('ok.  i copied it over', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(self._date("20080503023025"), results[2]['timestamp'])
        self.assertEquals('*** dgynn has left #etf', results[2]['message'])
        self.assertEquals('dgynn', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(self._date("20080503023026"), results[3]['timestamp'])
        self.assertEquals('*** dgynn has joined #etf', results[3]['message'])
        self.assertEquals('dgynn', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(self._date("20080503023027"), results[4]['timestamp'])
        self.assertEquals('*** dgynn has quit IRC', results[4]['message'])
        self.assertEquals('dgynn', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(self._date("20080503023127"), results[5]['timestamp'])
        self.assertEquals('* cbalan feels lonely...', results[5]['message'])
        self.assertEquals('cbalan', results[5]['nick'])
        self.assertEquals('feels lonely...', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(self._date("20080503023227"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro nods', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('nods', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(self._date("20080503023327"), results[7]['timestamp'])
        self.assertEquals('*** vmiliano was kicked by dgynn (dgynn)', results[7]['message'])
        self.assertEquals('dgynn', results[7]['nick'])
        self.assertEquals('vmiliano', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(self._date("20080503023427"), results[8]['timestamp'])
        self.assertEquals('*** rcorsaro sets mode: +o cbalan', results[8]['message'])
        self.assertEquals('rcorsaro', results[8]['nick'])
        self.assertEquals('+o cbalan', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(self._date("20080503023527"), results[9]['timestamp'])
        self.assertEquals('*** dgynn changes topic to "Enterprise Tools and Frameworks"', results[9]['message'])
        self.assertEquals('dgynn', results[9]['nick'])
        self.assertEquals('Enterprise Tools and Frameworks', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(self._date("20080503023627"), results[10]['timestamp'])
        self.assertEquals('*** rcorsaro is now known as bobby-robert', results[10]['message'])
        self.assertEquals('rcorsaro', results[10]['nick'])
        self.assertEquals('bobby-robert', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(self._date("20080503023727"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[13]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[13]['message'])
    
    def test_parse_simple_gozerbot(self):
        self.out.config.set('irclogs', 'channel.test.format', 'gozer')
        f = self.chmgr.channel('test')
        results = [i for i in self.out.parse_lines(self.simplegozerlines, f)]

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(self._date("20090703221800"), results[0]['timestamp'])
        self.assertEquals('<rcorsaro> !chatlog-on', results[0]['message'])
        self.assertEquals('rcorsaro', results[0]['nick'])
        self.assertEquals('!chatlog-on', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(self._date("20090703221900"), results[1]['timestamp'])
        self.assertEquals('<gozerbot> chatlog enabled on (default,#test2)', results[1]['message'])
        self.assertEquals('gozerbot', results[1]['nick'])
        self.assertEquals('chatlog enabled on (default,#test2)', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(self._date("20090703222000"), results[2]['timestamp'])
        self.assertEquals('gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has left', results[2]['message'])
        self.assertEquals('gozerbot', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(self._date("20090703222100"), results[3]['timestamp'])
        self.assertEquals('gozerbot (gozerbot@opt-FAD2E711.bos.east.verizon.net) has joined', results[3]['message'])
        self.assertEquals('gozerbot', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(self._date("20090703222200"), results[4]['timestamp'])
        self.assertEquals('rcorsaro (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving', results[4]['message'])
        self.assertEquals('rcorsaro', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(self._date("20090703222300"), results[5]['timestamp'])
        self.assertEquals('* rcorsaro2 is strong', results[5]['message'])
        self.assertEquals('rcorsaro2', results[5]['nick'])
        self.assertEquals('is strong', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(self._date("20090703222400"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro feels strange', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('feels strange', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(self._date("20090703222500"), results[7]['timestamp'])
        self.assertEquals('gozerbot was kicked by rcorsaro2 (rcorsaro2)', results[7]['message'])
        self.assertEquals('rcorsaro2', results[7]['nick'])
        self.assertEquals('gozerbot', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(self._date("20090703222600"), results[8]['timestamp'])
        self.assertEquals('rcorsaro2 sets mode: -o gozerbot', results[8]['message'])
        self.assertEquals('rcorsaro2', results[8]['nick'])
        self.assertEquals('-o gozerbot', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(self._date("20090703222700"), results[9]['timestamp'])
        self.assertEquals('rcorsaro2 changes topic to "testing topic"', results[9]['message'])
        self.assertEquals('rcorsaro2', results[9]['nick'])
        self.assertEquals('testing topic', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(self._date("20090703222800"), results[10]['timestamp'])
        self.assertEquals('rcorsaro (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2', results[10]['message'])
        self.assertEquals('rcorsaro', results[10]['nick'])
        self.assertEquals('rcorsaro2', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(self._date("20090703222900"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[12]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[12]['message'])
    
    # gozerbot in supy emulation mode
    def test_parse_supy_gozerbot(self):
        f = self.chmgr.channel(None)
        results = [i for i in self.out.parse_lines(self.supygozerlines, f)]

        self.assertEquals('comment', results[0]['type'])
        self.assertEquals(self._date("20090703221800"), results[0]['timestamp'])
        self.assertEquals('<gozerbot> chatlog enabled on (default,#test2)', results[0]['message'])
        self.assertEquals('gozerbot', results[0]['nick'])
        self.assertEquals('chatlog enabled on (default,#test2)', results[0]['comment'])

        self.assertEquals('comment', results[1]['type'])
        self.assertEquals(self._date("20090703221900"), results[1]['timestamp'])
        self.assertEquals('<rcorsaro> hello', results[1]['message'])
        self.assertEquals('rcorsaro', results[1]['nick'])
        self.assertEquals('hello', results[1]['comment'])

        self.assertEquals('part', results[2]['type'])
        self.assertEquals(self._date("20090703222000"), results[2]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has left', results[2]['message'])
        self.assertEquals('rcorsaro_', results[2]['nick'])

        self.assertEquals('join', results[3]['type'])
        self.assertEquals(self._date("20090703222100"), results[3]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has joined', results[3]['message'])
        self.assertEquals('rcorsaro_', results[3]['nick'])

        self.assertEquals('quit', results[4]['type'])
        self.assertEquals(self._date("20090703222200"), results[4]['timestamp'])
        self.assertEquals('*** rcorsaro_ (Robert@opt-FAD2E711.bos.east.verizon.net) has quit: Quit: leaving', results[4]['message'])
        self.assertEquals('rcorsaro_', results[4]['nick'])

        self.assertEquals('action', results[5]['type'])
        self.assertEquals(self._date("20090703222300"), results[5]['timestamp'])
        self.assertEquals('* rcorsaro is strong', results[5]['message'])
        self.assertEquals('rcorsaro', results[5]['nick'])
        self.assertEquals('is strong', results[5]['action'])

        self.assertEquals('action', results[6]['type'])
        self.assertEquals(self._date("20090703222400"), results[6]['timestamp'])
        self.assertEquals('* rcorsaro is manly', results[6]['message'])
        self.assertEquals('rcorsaro', results[6]['nick'])
        self.assertEquals('is manly', results[6]['action'])

        self.assertEquals('kick', results[7]['type'])
        self.assertEquals(self._date("20090703222500"), results[7]['timestamp'])
        self.assertEquals('*** rcorsaro_ was kicked by rcorsaro (rcorsaro)', results[7]['message'])
        self.assertEquals('rcorsaro', results[7]['nick'])
        self.assertEquals('rcorsaro_', results[7]['kicked'])

        self.assertEquals('mode', results[8]['type'])
        self.assertEquals(self._date("20090703222600"), results[8]['timestamp'])
        self.assertEquals('*** rcorsaro sets mode: +o rcorsaro_', results[8]['message'])
        self.assertEquals('rcorsaro', results[8]['nick'])
        self.assertEquals('+o rcorsaro_', results[8]['mode'])

        self.assertEquals('topic', results[9]['type'])
        self.assertEquals(self._date("20090703222700"), results[9]['timestamp'])
        self.assertEquals('*** rcorsaro changes topic to "testing topic"', results[9]['message'])
        self.assertEquals('rcorsaro', results[9]['nick'])
        self.assertEquals('testing topic', results[9]['topic'])

        self.assertEquals('nick', results[10]['type'])
        self.assertEquals(self._date("20090703222800"), results[10]['timestamp'])
        self.assertEquals('*** lsjdf (rcorsaro@opt-CF2BE53B.org) is now known as rcorsaro2', results[10]['message'])
        self.assertEquals('lsjdf', results[10]['nick'])
        self.assertEquals('rcorsaro2', results[10]['newnick'])

        self.assertEquals('notice', results[11]['type'])
        self.assertEquals(self._date("20090703222900"), results[11]['timestamp'])
        self.assertEquals('-rcorsaro- hello there', results[11]['message'])
        self.assertEquals('rcorsaro', results[11]['nick'])
        self.assertEquals('hello there', results[11]['comment'])

        self.assertEquals('other', results[12]['type'])
        self.assertEquals('* SOME SPECIAL MESSAGE *', results[12]['message'])

    def test_default_format(self):
        df = self.chmgr.channel('blah').format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_supy_format(self):
        self.out.config.set('irclogs', 'channel.test.format', 'supy')
        df = self.chmgr.channel('test').format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_nonexistant_format(self):
        df = self.chmgr.channel('sdflkjlskjf').format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_gozer_format(self):
        self.out.config.set('irclogs', 'channel.test.format', 'gozer')
        #import pdb; pdb.set_trace()
        df = self.chmgr.channel('test').format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals(['logs/%(network)s/simple/%(channel)s.%Y%m%d.slog',
            'logs/%(network)s/simple/%(channel_name)s.%Y%m%d.slog'], df['paths'])
        self.assertEquals('%Y-%m-%d %H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_none_format(self):
        df = self.chmgr.channel(None).format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', df['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])

    def test_channel(self):
        self.out.config.set('irclogs', 'channel.test.channel', '#test')
        self.out.config.set('irclogs', 'channel.test.format', '')
        ch = self.chmgr.channel('test')
        format = ch.format()
        self.assert_(ch)
        self.assertEquals('#test', ch.channel())
        self.assertEquals('/var/lib/irclogs', format['basepath'])
        self.assertEquals('%(channel)s/%(channel)s.%Y-%m-%d.log', format['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', format['timestamp_format'])
        self.assertEquals('utc', format['timezone'])
        self.assert_(format['timestamp_regex'])
        self.assert_(format['match_order'])
        for m in re.split('[ |:,]+', format['match_order']):
            self.assert_(format['%s_regex'%(m)])
            re.compile(format['%s_regex'%(m)])

    def test_channel_funny_name(self):
        self.out.config.set('irclogs', 'channel.mingya.channel', '#test')
        self.out.config.set('irclogs', 'channel.mingya.format', '')
        ch = self.chmgr.channel('mingya')
        self.assert_(ch)

    def test_channel_with_supy_format(self):
        self.out.config.set('irclogs', 'channel.test.channel', '#test')
        self.out.config.set('irclogs', 'channel.test.format', 'supy')
        ch = self.chmgr.channel('test')
        self.assert_(ch)

    def test_channel_with_gozer_format(self):
        self.out.config.set('irclogs', 'channel.test.channel', '#test')
        self.out.config.set('irclogs', 'channel.test.format', 'gozer')
        ch = self.chmgr.channel('test')
        self.assert_(ch)

    def test_get_file_dates(self):
        s = self._date("20090101050500")
        e = self._date("20090104050500")
        days = list(self.out._get_file_dates(s,e))
        self.assertEquals(4, len(days));
        self.assertEquals(s.date(), days[0]);
        self.assertEquals(e.date(), days[3]);

    def test_get_file_dates_tz(self):
        s = self._date("20090102010000", "America/New_York")
        e = self._date("20090104010000", "America/New_York")
        days = list(self.out._get_file_dates(s,e))
        self.assertEquals(3, len(days));
        self.assertEquals(self._date("20090102060000").date(), days[0]);
        self.assertEquals(self._date("20090104060000").date(), days[2]);

        s = self._date("20090102010000", "America/New_York")
        e = self._date("20090104200000", "America/New_York")
        days = list(self.out._get_file_dates(s,e))
        self.assertEquals(4, len(days));
        self.assertEquals(self._date("20090102060000").date(), days[0]);
        self.assertEquals(self._date("20090105060000").date(), days[3]);

    def test_merge_iseq(self):
        parsers = []
        self.out.config.set('irclogs', 'channel.test.format', 'gozer')
        df = self.chmgr.channel('test')
        for f in (
                (self.supygozerlines, self.chmgr.channel(None)), 
                (self.simplegozerlines, df), 
                (self.supylines, self.chmgr.channel(None))):
            parsers.append(self.out.parse_lines(f[0], channel=f[1]))
        def _key(x):
            return x.get('timestamp', datetime(1970,1,1,0,0,0, tzinfo=timezone('utc')))
        lines = list(merge_iseq(parsers, key=_key))
        self.assertEquals(40, len(lines))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FileIRCLogProviderTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
