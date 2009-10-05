# -*- coding: utf-8 -*-
import unittest
from time import strptime
from datetime import datetime, timedelta
from pytz import timezone, UTC
from StringIO import StringIO
import os
import operator
import shutil

from trac.core import *
from trac.test import EnvironmentStub, Mock
from trac.web.api import Request

from irclogs.search import *
from irclogs.api import IRCChannelManager, IRCChannel

class RequestStub(object):
    def __init__(self):
        self.session = {'tz': 'UTC'}

class SearchTestCase(unittest.TestCase):
    def setUp(self):
        self.indexdir = os.tempnam()
        self.env = EnvironmentStub()
        self.config = self.env.config
        self.config.set('irclogs', 'search_db_path', self.indexdir)
        self.config.set('irclogs', 'last_index', None)
        self.chmgr = IRCChannelManager(self.env)
        def events(start, end):
            self.assertTrue(start < end)
            self.dt = start
            dt = self.dt
            delta = timedelta(seconds=1)
            for i in range(0, 20):
                yield {
                    'timestamp': dt,
                    'network': u'freenode',
                    'channel': u'#trac',
                    'nick': u'doki_pen',
                    'type': u'comment',
                    'comment': u'hello %d'%i
                }
                dt += delta
        def fake_channels():
            obj = IRCChannel(self.env)
            obj.events_in_range = events
            yield obj

        def fake_channel(name):
            obj = IRCChannel(self.env)
            obj.events_in_range = events
            return obj

        self.chmgr.channels = fake_channels
        self.chmgr.channel = fake_channel
        self.out = WhooshIrcLogsIndex(self.env)

    def tearDown(self):
        shutil.rmtree(self.indexdir)

    def _make_environ(self, scheme='http', server_name='example.org',
                      server_port=80, method='GET', script_name='/trac',
                      **kwargs):
        environ = {'wsgi.url_scheme': scheme, 'wsgi.input': StringIO(''),
                   'REQUEST_METHOD': method, 'SERVER_NAME': server_name,
                   'SERVER_PORT': server_port, 'SCRIPT_NAME': script_name}
        environ.update(kwargs)
        return environ

    def test_index_and_search(self):
        self.out.update_index()
        req = Request(self._make_environ(), None)
        req.session = {'tz': 'UTC'}
        req.perm = Mock(has_permission= lambda x: True)
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(20, len(results))
        self.assertEqual(self.dt.hour, results[0][2].hour)
        req.session = {'tz': 'America/New_York'}
        req.perm = Mock(has_permission= lambda x: True)
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(20, len(results))
        est = timezone('America/New_York')
        expect_dt = est.normalize(self.dt.astimezone(est))
        sorted_results = sorted(results, key=operator.itemgetter(2))
        self.assertEqual(expect_dt, sorted_results[0][2])

    def test_timezones(self):
        self.out.config.set('irclogs', 'timezone', 'America/New_York')
        self.out.update_index()
        req = Request(self._make_environ(), None)
        req.session = {'tz': 'America/New_York'}
        req.perm = Mock(has_permission= lambda x: True)
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(20, len(results))
        self.assertEqual((self.dt.hour-5+24)%24, results[0][2].hour)

    def test_update(self):
        self.out.update_index()
        req = Request(self._make_environ(), None)
        req.session = {'tz': 'UTC'}
        req.perm = Mock(has_permission= lambda x: True)
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(20, len(results))
        self.out.update_index()
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(40, len(results))
        self.out.update_index()
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(60, len(results))
        self.out.update_index()
        results = [i for i in self.out.get_search_results(req, ('hello',), ('irclogs',))]
        self.assertEqual(80, len(results))

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SearchTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
