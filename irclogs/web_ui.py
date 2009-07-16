# -*- coding: utf-8 -*-
import os
import re
import calendar
import pytz
import time

from time import strptime
from trac.util.datefmt import localtz
from datetime import datetime
from calendar import month_name

from trac.core import *
from trac.perm import IPermissionRequestor
from trac.config import Option, ListOption
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_stylesheet, add_script
from trac.web.main import IRequestHandler
from trac.util.html import escape, html, Markup
from trac.util.text import to_unicode
from trac.util.datefmt import utc

from genshi.builder import tag
from irclogs.api import *
from irclogs.nojs import generate_nojs_calendar

class IrcLogsView(Component):
    providers = ExtensionPoint(IIRCLogsProvider)

    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor)
    _url_re = re.compile(
            r'^/irclogs/(?P<channel>\w+)'
            r'(/(?P<year>\d{4})(/(?P<month>\d{2})'
            r'(/(?P<day>\d{2}))?)?)?(/(?P<feed>feed)'
            r'(/(?P<feed_count>\d+?))?)?/?$')
    charset = Option('irclogs', 'charset', 'utf-8',
                     doc='Channel charset')

    search_db_path = Option('irclogs', 'search_db_path', 
                            '/tmp/irclogs.idx', 
                     doc="""A path to the directory where the search index 
                           resides.  Example: /tmp/irclogs.idx""")

    hidden_users = ListOption('irclogs', 'hidden_users', '', 
                     doc='A list of users that should be hidden by default')

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('irclogs', resource_filename(__name__, 'htdocs'))]

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        for ch in self._get_channels():
            yield 'irclogs-%s'%(ch)

    def get_navigation_items(self, req):
        if req.perm.has_permission('IRCLOGS_VIEW'):
            for ch in self._get_channels():
                ops = dict(self.config.options('irclogs'))
                chan = ops['channel.%s.channel'%(ch)]
                navbutton = ops.get('channel.%s.navbutton'%(ch), chan)
                l = html.a(navbutton, href=req.href.irclogs(ch))
                yield 'mainnav', 'irclogs-%s'%(ch), l

    # IPermissionHandler methods
    def get_permission_actions(self):
        return ['IRCLOGS_VIEW']

    # IRequestHandler methods
    def match_request(self, req):
        m = self._url_re.search(req.path_info)
        if m is None:
            return False
        req.args.update(m.groupdict())
        return True

    def _get_channels(self):
        CHANNEL_RE = re.compile('^channel\.(?P<name>[^.]+)\..*$')
        def _name(x):
            m = CHANNEL_RE.match(x)
            if m:
                return m.groupdict()['name']
            else:
                None
        ops = self.config.options('irclogs')
        # set makes uniq
        return filter(None, set(map(_name, map(lambda x: x[0], ops))))

    def get_provider(self, channel):
        # TODO: generalize
        name = self.config.get('irclogs', 'channel.%s.provider'%(channel))
        if not name:
            name = self.config.get('irclogs', 'provider', 'file')
        for p in self.providers:
            if name == p.get_name():
                return p
        raise Exception(
                "%s IRCLogsProvider for channel %s not found."%(name, channel))
            
    def _map_lines(self, l):
        if l.get('nick'):
            l['nick'] = to_unicode(l['nick'], self.charset)
        if l.get('nick') in self.hidden_users:
            l.update({'hidden': True})
        if l['type'] == 'comment':
            l['nickcls'] = 'nick-%d' % (sum(ord(c) for c in l['nick']) % 8)
        if l['message']:
            l['message'] = to_unicode(l['message'], self.charset)
        return l

    def _hide_nicks(self, l):
        return not l.get('hidden')

    def process_request(self, req):
        req.perm.assert_permission('IRCLOGS_VIEW')
        add_stylesheet(req, 'irclogs/css/jquery-ui.css')
        add_stylesheet(req, 'irclogs/css/ui.datepicker.css')
        add_stylesheet(req, 'irclogs/css/irclogs.css')
        add_script(req, 'irclogs/js/jquery-ui.js')

        context = {}
        entries = {}
        today = datetime.now()
        context['channel'] = req.args['channel'] 
        context['calendar'] = req.href.chrome('common', 'ics.png')
        context['year'] = int(req.args.get('year') or today.year)
        context['day'] = int(req.args.get('day') or today.day)
        context['month'] = int(req.args.get('month') or today.month)
        context['month_name'] = month_name[context['month']]
        context['firstDay'] = 3
        context['firstMonth'] = 8
        context['firstYear'] = 1977
        context['nojscal'] = generate_nojs_calendar(req, context, entries)

        # TODO: do this for each channel, instead of hardcode
        provider = self.get_provider(context['channel'])
        start = datetime(context['year'], context['month'], context['day'], 
                0, 0, 0, tzinfo=req.tz)
        end = datetime(context['year'], context['month'], context['day']+1, 
                0, 0, 0, tzinfo=req.tz)
        lines = provider.get_events_in_range(context['channel'], start, end)

        context['viewmode'] = 'day'
        context['current_date'] = '%02d/%02d/%04d'%(context['month'], 
                context['day'], context['year'])
        context['int_month'] = context['month']-1
        context['lines'] = filter(
            self._hide_nicks, 
            map(self._map_lines, lines)
        )

        # handle if display type is html or an external feed
        if req.args['feed'] is not None:
            if len(context['lines']) > 0:
                context['lines'] = context['lines'] \
                        [-int(req.args.get('feed_count',10)):]
            return 'irclogs_feed.html', context, None 
        else:
            return 'irclogs.html', context, None
