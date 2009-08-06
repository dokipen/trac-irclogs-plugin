# -*- coding: utf-8 -*-
import os
import re
import calendar
import pytz
import time

from time import strptime
from trac.util.datefmt import localtz
from datetime import datetime, timedelta
from calendar import month_name
from itertools import imap, ifilter

from trac.core import *
from trac.perm import IPermissionRequestor
from trac.config import Option, ListOption
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_stylesheet, add_script, add_link
from trac.web.main import IRequestHandler
from trac.web.href import Href
from trac.util.html import escape, html, Markup
from trac.util.datefmt import utc

from genshi.builder import tag
from irclogs.api import *
from irclogs.nojs import generate_nojs_calendar

class IrcLogsView(Component):
    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor)
    _url_re = re.compile(
            r'^/irclogs(/(?P<channel>[^/]+))?'
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

    show_msg_types = ListOption('irclogs', 'show_msg_types', 
                     [u'comment', u'action'],
                     doc='There are message types to show by default')


    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('irclogs', resource_filename(__name__, 'htdocs'))]

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        ch_mgr = IRCChannelManager(self.env)
        for ch in ch_mgr.get_channel_names():
            yield 'irclogs-%s'%(ch)

    def get_navigation_items(self, req):
        if req.perm.has_permission('IRCLOGS_VIEW'):
            ch_mgr = IRCChannelManager(self.env)
            for channel_name in ch_mgr.get_channel_names():
                channel = ch_mgr.get_channel_by_name(channel_name)
                href = req.href.irclogs(channel['name'])
                if not channel['name']:
                    href = req.href.irclogs()
                l = html.a(channel['navbutton'], href=href)
                yield 'mainnav', channel['menuid'], l 

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

    def _map_lines(self, l):
        if l.get('nick') in self.hidden_users:
            l.update({'hidden': True})
        if l['type'] == 'comment':
            l['nickcls'] = 'nick-%d' % (sum(ord(c) for c in l['nick']) % 8)
        return l

    def _render_line(self, line):
        hidden = line['type'] in self.show_msg_types and ' ' or 'hidden'
        line.update({
            'time': line.get('timestamp') and line['timestamp'].time() or '',
            'message': escape(line['message']),
            'comment': escape(line.get('comment')),
            'action': escape(line.get('action')),
            'hidden': hidden,
        })
        if line['type'] == 'comment':
            return ('<tr class="%(type)s %(hidden)s"><td class="time">[%(time)s]' + \
                   '</td><td class="left %(nickcls)s">&lt;%(nick)s&gt;' + \
                   '</td><td class="right">%(comment)s</td></tr>')%line 
        if line['type'] == 'action':
            return ('<tr class="%(type)s %(hidden)s"><td class="time">[%(time)s]' + \
                   '</td><td class="left">*</td><td class="right">' + \
                   '%(action)s</td></tr>')%line
        else: 
            return ('<tr class="%(type)s %(hidden)s"><td class="time">[%(time)s]' + \
                   '</td><td class="left"></td><td class=' + \
                   '"right">%(message)s</td></tr>')%line

    def process_request(self, req):
        req.perm.assert_permission('IRCLOGS_VIEW')
        add_stylesheet(req, 'irclogs/css/jquery-ui.css')
        add_stylesheet(req, 'irclogs/css/ui.datepicker.css')
        add_stylesheet(req, 'irclogs/css/irclogs.css')
        add_script(req, 'irclogs/js/jquery-ui.js')
        # crappy hack because there isn't a way to make alternate stylesheets
        # this is basically add_stylesheet's code changed slightly
        def _alt_css(req, filename, title):
            href = req.href
            if not filename.startswith('/'):
                href = href.chrome
            mt="text/css"
            rel="alternate stylesheet"
            add_link(req, rel, href(filename), title=title, mimetype=mt)
        _alt_css(req, 'irclogs/css/irclogs-brief.css', 'Brief');

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
        ch_mgr = IRCChannelManager(self.env)

        # TODO: do this for each channel, instead of hardcode
        channel = ch_mgr.get_channel_by_name(context['channel'])
        provider = ch_mgr.get_provider(channel)
        oneday = timedelta(days=1)
        start = datetime(context['year'], context['month'], context['day'], 
                0, 0, 0, tzinfo=req.tz)
        # cheezy hack to give us enough lines as long as the channel is 
        # somewhat active.  Without this we get a shortage of feed lines
        # at day break.
        end = start + oneday
        if req.args.get('feed') == 'feed':
            start = start - oneday
        lines = provider.get_events_in_range(context['channel'], start, end)

        context['viewmode'] = 'day'
        context['current_date'] = '%02d/%02d/%04d'%(context['month'], 
                context['day'], context['year'])
        context['int_month'] = context['month']-1
        context['lines'] = ifilter(
            lambda x: not x.get('hidden'), 
            imap(self._map_lines, lines)
        )

        if req.args.get('feed') == 'feed':
            limit = int(req.args.get('feed_count', 10))
            context['lines'] = list(context['lines'])[-limit:]
            context['rows'] = imap(self._render_line, context['lines'])
            return 'irclogs_feed.html', context, None 
        else:
            context['rows'] = imap(self._render_line, context['lines'])
            return 'irclogs.html', context, None
