# -*- coding: utf-8 -*-
import unittest
from time import strptime
from datetime import datetime
from pytz import timezone, UTC

from trac.core import *
from trac.test import EnvironmentStub, Mock

from irclogs.api import IRCChannelManager 

class ApiTestCase(unittest.TestCase):
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
        self.out = IRCChannelManager(self.env)

    def test_get_channel_by_name(self):
        c = self.out.channel('crap')
        self.assertEqual('file1', c.provider())
        self.assertEqual('#test1', c.channel())
        self.assertEqual('network1', c.network())
        self.assertEqual(None, c.name())

        c = self.out.channel(None)
        self.assertEqual('file1', c.provider())
        self.assertEqual('#test1', c.channel())
        self.assertEqual('network1', c.network())
        self.assertEqual(None, c.name())

        c = self.out.channel('test2')
        self.assertEqual('file2', c.provider())
        self.assertEqual('#test2', c.channel())
        self.assertEqual('network2', c.network())
        self.assertEqual('test2', c.name())

        c = self.out.channel('test3')
        self.assertEqual('file1', c.provider())
        self.assertEqual('#test3', c.channel())
        self.assertEqual('network1', c.network())
        self.assertEqual('test3', c.name())

        c = self.out.channel('test4')
        self.assertEqual('file1', c.provider())
        self.assertEqual('#test1', c.channel())
        self.assertEqual('network1', c.network())
        self.assertEqual('blah', c.settings()['blah'])
        self.assertEqual('test4', c.name())

    def test_user_tz(self):
        req = Mock(session={'tz': 'America/New_York'})
        self.assertEqual('America/New_York', req.session.get('tz'))
        dt = UTC.localize(datetime.today())
        udt = self.out.to_user_tz(req, dt)
        self.assertEqual('America/New_York', str(udt.tzinfo))

    def test_tz_conversion(self):
        NYC = timezone('America/New_York')
        nydt = NYC.localize(datetime(2009, 8, 15, 12, 0, 0), None)
        udt = UTC.normalize(nydt.astimezone(UTC))
        nydt2 = NYC.normalize(udt.astimezone(NYC))
        self.assertEqual(nydt, nydt2)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ApiTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
