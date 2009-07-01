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

class IrcLogsView(Component):
    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor)
    _url_re = re.compile(r'^/irclogs(/(?P<year>\d{4})(/(?P<month>\d{2})'
                         r'(/(?P<day>\d{2}))?)?)?(/(?P<feed>feed)(/(?P<feed_count>\d+?))?)?/?$')
# TODO: make the line format somewhat configurable
# Uncomment the following line if using a pipe as a divider and a space
# between the date adn time.  Make sure to comment out the existing
# _line_re.
#    _line_re = re.compile('%s %s \|  (%s)$' % (
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
    navbutton = Option('irclogs', 'navigation_button', '',
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
                yield 'mainnav', 'irclogs', html.a(title, href=req.href.irclogs())

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

    def _to_unicode(self, iterable):
        for line in iterable:
            yield to_unicode(line, self.charset)

    def _get_file_re(self):
        return re.compile(r'^%s$' % re.escape(self.file_format)
              .replace('\\%Y', '(?P<year>\d{4})')
              .replace('\\%m', '(?P<month>\d{2})')
              .replace('\\%d', '(?P<day>\d{2})')
        )

    def _get_filename(self, year, month, day):
        return os.path.join(self.path, self.file_format
                .replace('%Y', str(year))
                .replace('%m', str(month))
                .replace('%d', str(day))
        )

    def _render_lines(self, iterable, tz=None):
        dummy = lambda: {}
        result = []
        for line in iterable:
            d = getattr(self._line_re.search(line), 'groupdict', dummy)()
            for mode in ('channel', 'action', 'server'):
                prefix = mode[0]
                text = d.get('%s_text' % prefix)
                if not text is None:
                    nick = d['%s_nickname' % prefix]
                    break
            else:
                continue
            
            if nick in self.hidden_users:
                hidden = "hidden_user"
            else:
                hidden = ""

            if not tz is None:
                utc = pytz.utc
                server_dt = self._get_tz_datetime(d['date'], d['time'])
                local_dt = tz.normalize(server_dt.astimezone(tz))
                local_time = local_dt.strftime("%H:%M:%S")
                local_date = local_dt.strftime("%Y-%m-%d")
                utc_dt = utc.normalize(server_dt.astimezone(utc)). \
                    strftime("UTC%Y-%m-%dT%H:%M:%S")
            else:
                local_date = d['date']
                local_time = d['time']
                utc_dt = d['time']

            result.append({
                'date':         local_date,
                'hidden_user':  hidden,
                'time':         local_time,
                'utc_dt':       utc_dt,
                'mode':         mode,
                'text':         text,
                'nickname':     nick,
                'nickcls':      'nick-%d' % (sum(ord(c) for c in nick) % 8),
            })
        return result

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

    def _get_tz_datetime(self, date, time):
        return datetime(*strptime(date + "T" +  time, 
                                  "%Y-%m-%dT%H:%M:%S")[0:6]). \
                                  replace(tzinfo=localtz)

    def process_request(self, req):
        req.perm.assert_permission('IRCLOGS_VIEW')
        add_stylesheet(req, 'irclogs/style.css')
        add_stylesheet(req, 'irclogs/datePicker.css')
        add_script(req, 'irclogs/date.js')
        add_script(req, 'irclogs/jquery.datePicker.js')
        add_script(req, 'irclogs/irclogs.js')
        file_re = self._get_file_re()

        context = {}
        entries = {}
        context['cal'] = self._generate_calendar(req, entries)

        # list all log files to know what dates are available

        try:
            files = os.listdir(self.path)
        except OSError, e:
            code, message = e
            context['error'] = True
            context['message'] = '%s: %s' % (message, e.filename)
            return 'irclogs.html', context, None
        
        if len(files) == 0:
           context['error'] = True
           context['message'] = 'No logs exist yet. ' \
                                'Contact your system administrator.'
           return 'irclogs.html', context, None
        
        files.sort()
        first_found = True
        for fn in files:
            m = file_re.search(fn)
            if m is None:
                continue 
            d = m.groupdict()
            y = entries.setdefault(int(d['year']), {})
            m = y.setdefault(int(d['month']), {})
            m[int(d['day'])] = True
            if first_found is True:
                context['start_date'] = '%s/%s/%s' % (d['month'], 
                                                      d['day'],
                                                      d['year'])
                first_found = False

        # default to today if no date is selected
        # or build lists of available dates if no date is given
        if req.args['year'] is None:
            today = datetime.now()
            req.args['year'] = today.year
            req.args['month'] = '%02d' % today.month
            req.args['day'] = '%02d' % today.day
        elif req.args['month'] is None:
            months = entries.get(int(req.args['year']), {}).keys()
            months.sort()
            context['months'] = [{
                'caption':      month_name[m],
                'href':         req.href('irclogs', req.args['year'],
                                         '%02d' % m)
            } for m in months]
            context['year'] = req.args['year']
            context['viewmode'] = 'months'
        elif req.args['day'] is None:
            year = entries.get(int(req.args['year']), {})
            days = year.get(int(req.args['month']), {}).keys()
            days.sort()
            context['days'] = [{
                'caption':      d,
                'href':         req.href('irclogs', req.args['year'],
                                         req.args['month'], '%02d' % d)
            } for d in days]
            context['year'] = req.args['year']
            context['month'] = month_name[int(req.args['month'])]
            context['viewmode'] = 'days'

        # generate calendar according to log files found


        # if day is given, read logfile and build irc log for display

        if req.args['day'] is not None:
            logfile = self._get_filename(req.args['year'], req.args['month'],
                                         req.args['day'])
            context['day'] = req.args['day']
            context['month'] = req.args['month']
            context['month_name'] = month_name[int(req.args['month'])]
            context['year'] = req.args['year']
            context['viewmode'] = 'day'
            context['current_date'] = '%s/%s/%s' % (req.args['month'], 
                                                    req.args['day'], 
                                                    req.args['year'])
            context['int_month'] = int(req.args['month'])-1

            if not os.path.exists(logfile):
                context['missing'] = True
            else:
                context['missing'] = False
                f = file(logfile)
                try:
                    context['lines'] = self._render_lines(self._to_unicode(f),
                                                          req.tz)
                finally:
                    f.close()

        # handle if display type is html or an external feed
        if req.args['feed'] is not None:
            if not context['missing']:
                context['lines'] = context['lines'] \
                                    [:int(req.args.get('feed_count',10))]
            return 'irclogs_feed.html', context, None 
        else:
            return 'irclogs.html', context, None
