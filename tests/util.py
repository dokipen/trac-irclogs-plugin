import unittest
from time import strptime
from datetime import datetime
from pytz import timezone

from trac.core import *
from trac.test import EnvironmentStub

class UtilTestCase(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()
        self.config = self.env.config

        self.config.set('irclogs', 'provider', 'file1')
        self.config.set('irclogs', 'channel', '#test1')
        self.config.set('irclogs', 'network', 'network1')

        self.config.set('irclogs', 'channel.test2.channel', '#test2')
        self.config.set('irclogs', 'channel.test2.provider', 'file2')
        self.config.set('irclogs', 'channel.test2.network', 'network2')

        self.config.set('irclogs', 'channel.test3.channel', '#test3')

        self.config.set('irclogs', 'channel.test4.blah', 'blah')

    def test_default_format(self):
        """
        df = self.out.default_format()
        self.assertEquals('/var/lib/irclogs', df['basepath'])
        self.assertEquals(['%(channel)s/%(channel)s.%Y-%m-%d.log'], df['paths'])
        self.assertEquals('%Y-%m-%dT%H:%M:%S', df['timestamp_format'])
        self.assertEquals('utc', df['timezone'])
        self.assert_(df['timestamp_regex'])
        self.assert_(df['match_order'])
        for m in re.split('[ |:,]+', df['match_order']):
            self.assert_(df['%s_regex'%(m)])
            re.compile(df['%s_regex'%(m)])
        """
        pass


    def test_get_channel_by_name(self):
        c = util.get_channel_by_name(self.config, 'crap')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        c = util.get_channel_by_name(self.config, None)
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        c = util.get_channel_by_name(self.config, 'test2')
        self.assertEqual('file2', c['provider'])
        self.assertEqual('#test2', c['channel'])
        self.assertEqual('network2', c['network'])
        self.assertEqual('test2', c['name'])

        c = util.get_channel_by_name(self.config, 'test3')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test3', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('test3', c['name'])

        c = util.get_channel_by_name(self.config, 'test4')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('blah', c['blah'])
        self.assertEqual('test4', c['name'])

    def test_get_channel_by_channel(self):
        c = util.get_channel_by_channel(self.config, '#test2')
        self.assertEqual('file2', c['provider'])
        self.assertEqual('#test2', c['channel'])
        self.assertEqual('network2', c['network'])
        self.assertEqual('test2', c['name'])

        c = util.get_channel_by_channel(self.config, '#test3')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test3', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual('test3', c['name'])

        c = util.get_channel_by_channel(self.config, '#test1')
        self.assertEqual('file1', c['provider'])
        self.assertEqual('#test1', c['channel'])
        self.assertEqual('network1', c['network'])
        self.assertEqual(None, c['name'])

        try:
            util.get_channel_by_channel(self.config, '#crazy')
            raise Exception('Expected exception')
        except Exception as e:
            self.assertEqual(('channel #crazy not found',), e.args)

        self.config.set('irclogs', 'channel.test6.channel', '#test1')
        try:
            util.get_channel_by_channel(self.config, '#test1')
            raise Exception('Expected exception')
        except Exception as e:
            self.assertEqual(('multiple channels match #test1',), e.args)

        self.config.set('irclogs', 'channel.test7.channel', '#test2')
        try:
            util.get_channel_by_channel(self.config, '#test2')
            raise Exception('Expected exception')
        except Exception as e:
            self.assertEqual(('multiple channels match #test2',), e.args)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UtilTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
