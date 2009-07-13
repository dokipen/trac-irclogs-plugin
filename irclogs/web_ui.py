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

class IrcLogsView(Component):
    providers = ExtensionPoint(IIRCLogsProvider)

    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor)
    _url_re = re.compile(r'^/irclogs(/(?P<year>\d{4})(/(?P<month>\d{2})'
                         r'(/(?P<day>\d{2}))?)?)?(/(?P<feed>feed)(/(?P<feed_count>\d+?))?)?/?$')
    _line_re = re.compile('%sT%s  (%s)$' % (
        r'(?P<date>\d{4}-\d{2}-\d{2})',
        r'(?P<time>\d{2}:\d{2}:\d{2})',
        '|'.join([
            r'(<(?P<c_nickname>.*?)> (?P<c_text>.*?))',
            r'(\* (?P<a_nickname>.*?) (?P<a_text>.*?))',
            r'(\*\*\* (?P<s_nickname>.*?) (?P<s_text>.*?))'
        ]))
    )
    charset = Option('irclogs', 'charset', 'utf-8',
                     doc='Channel charset')
    file_format = Option('irclogs', 'file_format', '#channel.%Y-%m-%d.log',
                     doc='Format of a logfile for a given day. Must '
                             'include %Y, %m and %d. Example: '
                             '#channel.%Y-%m-%d.log')
    path = Option('irclogs', 'path', '',
                  doc='The path where the irc logfiles are')
    navbutton = Option('irclogs', 'navbutton', 'irc logs',
                     doc="""If not empty an button with this value as caption 
                            is added to the navigation bar, pointing to the 
                            irc plugin""")
    prefix = Option('irclogs', 'prefix', '', doc='IRC Channel name')

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
        if self.navbutton.strip():
            return 'irclogs'

    def get_navigation_items(self, req):
        if req.perm.has_permission('IRCLOGS_VIEW'):
            title = self.navbutton.strip()
            if title:
                yield 'mainnav', 'irclogs-test2', html.a(title, href=req.href.irclogs())
                yield 'mainnav', 'irclogs-test3', html.a(title, href=req.href.irclogs())

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

    def _render_lines(self, iterable):
        def _map(line):
            if line['nick'] in self.hidden_users:
                line.update({'hidden': 'hidden_user'})
            if line['message']:
                line['message'] = to_unicode(line['message'], self.charset)
            return line
        return map(_map, iterable)

    def _generate_calendar(self, req, entries):
        if not req.args['year'] is None:
            year = int(req.args['year'])
        else:
            year = datetime.now().year
        if not req.args['month'] is None:
            month = int(req.args['month'])
        else:
            month = datetime.now().month
        if not req.args['day'] is None:
            today = int(req.args['day'])
        else:
            today = -1
        this_month_entries = entries.get(year, {}).get(month, {})

        weeks = []
        for week in calendar.monthcalendar(year, month):
            w = []
            for day in week:
                if not day:
                    w.append({
                        'empty':    True
                    })
                else:
                    w.append({
                        'caption':  day,
                        'href':     req.href('irclogs', year,
                                             '%02d' % month, '%02d' % day),
                        'today':    day == today,
                        'has_log':  day in this_month_entries
                    })
            weeks.append(w)

        next_month_year = year
        next_month = int(month) + 1
        if next_month > 12:
            next_month_year += 1
            next_month = 1
        if today > -1:
            next_month_href = req.href('irclogs', next_month_year,
                                       '%02d' % next_month, '%02d' % today)
        else:
            next_month_href = req.href('irclogs', next_month_year,
                                       '%02d' % next_month)

        prev_month_year = year
        prev_month = int(month) - 1
        if prev_month < 1:
            prev_month_year -= 1
            prev_month = 12
        if today > -1:
            prev_month_href = req.href('irclogs', prev_month_year,
                                       '%02d' % prev_month, '%02d' % today)
        else:
            prev_month_href = req.href('irclogs', prev_month_year,
                                       '%02d' % prev_month)

        return {
            'weeks':        weeks,
            'year':         {
                'caption':      year,
                'href':         req.href('irclogs', year)
            },
            'month':        {
                'caption':      month_name[month],
                'href':         req.href('irclogs', year, '%02d' % month)
            },
            'next_year':    {
                'caption':      str(year + 1),
                'href':         req.href('irclogs', year + 1)
            },
            'prev_year':    {
                'caption':      str(year - 1),
                'href':         req.href('irclogs', year - 1)
            },
            'next_month':   {
                'caption':      '%02d' % next_month,
                'href':         next_month_href
            },
            'prev_month':   {
                'caption':      '%02d' % prev_month,
                'href':         prev_month_href
            },
        }

    def get_provider(self, name):
        # TODO: generalize
        for p in self.providers:
            return p
            
    def process_request(self, req):
        req.perm.assert_permission('IRCLOGS_VIEW')
        add_stylesheet(req, 'irclogs/css/jquery-ui.css')
        add_stylesheet(req, 'irclogs/css/ui.datepicker.css')
        add_stylesheet(req, 'irclogs/css/irclogs.css')
        add_script(req, 'irclogs/js/jquery-ui.js')

        context = {}
        entries = {}
        today = datetime.now()
        context['cal'] = self._generate_calendar(req, entries)
        context['calendar'] = req.href.chrome('common', 'ics.png')
        context['year'] = int(req.args.get('year', today.year))
        context['day'] = int(req.args.get('day', today.day))
        context['month'] = int(req.args.get('month', today.month))
        context['month_name'] = month_name[context['month']]
        context['firstDay'] = 3
        context['firstMonth'] = 8
        context['firstYear'] = 1977

        # TODO: do this for each channel, instead of hardcode
        channel = 'test2'
        provider = self.get_provider('file')
        lines = provider.get_events_in_range(channel, datetime(context['year'], context['month'], context['day'], 0, 0, 0, tzinfo=req.tz), datetime(context['year'], context['month'], context['day']+1, 0, 0, 0, tzinfo=req.tz))

        context['viewmode'] = 'day'
        context['current_date'] = '%02d/%02d/%04d'%(context['month'], context['day'], context['year'])
        context['int_month'] = context['month']-1

        context['lines'] = self._render_lines(lines)

        # handle if display type is html or an external feed
        if req.args['feed'] is not None:
            if not context['missing']:
                context['lines'] = context['lines'] \
                                    [:int(req.args.get('feed_count',10))]
            return 'irclogs_feed.html', context, None 
        else:
            return 'irclogs.html', context, None
