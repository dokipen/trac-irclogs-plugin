# -*- coding: utf-8 -*-
import os
import re
import calendar
from datetime import datetime
from trac.core import *
from trac.perm import IPermissionRequestor
from trac.config import Option
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_stylesheet
from trac.web.main import IRequestHandler
from trac.util.html import escape, html, Markup
from trac.util.text import to_unicode


class IrclogsPlugin(Component):
    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor)
    _url_re = re.compile(r'^/irclogs(/(?P<year>\d{4})(/(?P<month>\d{2})'
                         r'(/(?P<day>\d{2}))?)?)?/?$')
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
                       doc='If not empty an button with this value as caption '
                           'is added to the navigation bar, pointing to the '
                           'irc plugin')

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

    def _render_lines(self, iterable):
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
            result.append({
                'date':         d['date'],
                'time':         d['time'],
                'mode':         mode,
                'text':         text,
                'nickname':     nick,
                'nickcls':      'nick-%d' % (sum(ord(c) for c in nick) % 8)
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
            'year':         year,
            'month':        month,
            'weeks':        weeks,
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

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        if self.navbutton.strip():
            return 'irclogs'

    def get_navigation_items(self, req):
        if req.perm.has_permission('IRCLOGS_VIEW'):
            title = self.navbutton.strip()
            if title:
                yield 'mainnav', 'irclogs', html.A(title, href=req.href.irclogs())

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

    def process_request(self, req):
        req.perm.assert_permission('IRCLOGS_VIEW')
        add_stylesheet(req, 'irclogs/style.css')

        file_re = self._get_file_re()

        context = {}
        entries = {}
        files = os.listdir(self.path)
        files.sort()
        for fn in files:
            m = file_re.search(fn)
            if m is None:
                continue
            d = m.groupdict()
            y = entries.setdefault(int(d['year']), {})
            m = y.setdefault(int(d['month']), {})
            m[int(d['day'])] = True

        if req.args['year'] is None:
            years = entries.keys()
            years.sort()
            context['years'] = [{
                'caption':      y,
                'href':         req.href('irclogs', y)
            } for y in years]
            context['viewmode'] = 'years'
        elif req.args['month'] is None:
            months = entries.get(int(req.args['year']), {}).keys()
            months.sort()
            context['months'] = [{
                'caption':      m,
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
            context['month'] = req.args['month']
            context['viewmode'] = 'days'

        context['cal'] = self._generate_calendar(req, entries)

        if req.args['day'] is not None:
            logfile = self._get_filename(req.args['year'], req.args['month'],
                                         req.args['day'])
            context['day'] = req.args['day']
            context['month'] = req.args['month']
            context['year'] = req.args['year']
            context['viewmode'] = 'day'

            if not os.path.exists(logfile):
                context['missing'] = True
            else:
                context['missing'] = False
                f = file(logfile)
                try:
                    context['lines'] = self._render_lines(self._to_unicode(f))
                finally:
                    f.close()

        return 'irclogs.html', context, None

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('irclogs', resource_filename(__name__, 'htdocs'))]
