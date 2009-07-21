import unittest
from time import strptime
from datetime import datetime
from pytz import timezone

from trac.core import *
from trac.test import EnvironmentStub

from irclogs.api import *

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()
        self.out = IRCChannelManager(self.env)
        self.config = self.env.config

        self.config.set('irclogs', 'provider', 'file1')
        self.config.set('irclogs', 'channel', '#test1')
        self.config.set('irclogs', 'network', 'network1')

        self.config.set('irclogs', 'channel.test2.channel', '#test2')
        self.config.set('irclogs', 'channel.test2.provider', 'file2')
        self.config.set('irclogs', 'channel.test2.network', 'network2')

        self.config.set('irclogs', 'channel.test3.channel', '#test3')

        self.config.set('irclogs', 'channel.test4.blah', 'blah')

    def test_get_channel_by_name(self):
        c = self.out.get_channel_by_name('crap')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        c = self.out.get_channel_by_name(None)
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        c = self.out.get_channel_by_name('test2')
        self.assertEqual('file2', c['provider'])
        self.assertEqual('#test2', c['channel'])
        self.assertEqual('network2', c['network'])
        self.assertEqual('test2', c['name'])

        c = self.out.get_channel_by_name('test3')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test3', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('test3', c['name'])

        c = self.out.get_channel_by_name('test4')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('blah', c['blah'])
        self.assertEqual('test4', c['name'])

    def test_get_channel_by_channel(self):
        c = self.out.get_channel_by_channel('#test2')
        self.assertEqual('file2', c['provider'])
        self.assertEqual('#test2', c['channel'])
        self.assertEqual('network2', c['network'])
        self.assertEqual('test2', c['name'])

        c = self.out.get_channel_by_channel('#test3')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test3', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('test3', c['name'])

        c = self.out.get_channel_by_channel('#test1')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        try:
            self.out.get_channel_by_channel('#crazy')
            raise Exception('Expected exception')
        except Exception, e:
            self.assertEqual(('channel #crazy not found',), e.args)

        self.config.set('irclogs', 'channel.test6.channel', '#test1')
        try:
            self.out.get_channel_by_channel('#test1')
            raise Exception('Expected exception')
        except Exception, e:
            self.assertEqual(('multiple channels match #test1',), e.args)

        self.config.set('irclogs', 'channel.test7.channel', '#test2')
        try:
            self.out.get_channel_by_channel('#test2')
            raise Exception('Expected exception')
        except Exception, e:
            self.assertEqual(('multiple channels match #test2',), e.args)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ApiTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
