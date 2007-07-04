# -*- coding: utf-8 -*-
import os
import re
import calendar
from datetime import datetime
from trac.config import Option
from trac.core import *
from trac.perm import IPermissionRequestor
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_stylesheet
from trac.web.main import IRequestHandler
from trac.util import escape, Markup
from trac.util.text import to_utf8
from trac.Search import ISearchSource


dummy = lambda: {}

class IrclogsPlugin(Component):
    implements(INavigationContributor, ITemplateProvider, IRequestHandler, \
               IPermissionRequestor, ISearchSource)
#    _url_re = re.compile(r'^/irclogs(/\d{4}\d{2}\d{2})?$')
#  2006-05-10 00:10:33 |  a
# Orig line regex
#    _line_re = re.compile('%sT%s  (%s)$' % (
    _url_re = re.compile(r'^/irclogs(/(?P<year>\d{4})(/(?P<month>\d{2})'
                         r'(/(?P<day>\d{2}))?)?)?(#.*)?/?$'
                        )
    _line_re = re.compile('%s %s \|  (%s)$' % (
        r'(?P<date>\d{4}-\d{2}-\d{2})',
        r'(?P<time>\d{2}:\d{2}:\d{2})',
        '|'.join([
            r'(<(?P<c_nickname>.*?)> (?P<c_text>.*?))',
            r'(\* (?P<a_nickname>.*?) (?P<a_text>.*?))',
            r'(\*\*\* (?P<s_nickname>.*?) (?P<s_text>.*?))'
        ]))
    )
# Orig regex
#    _file_re = re.compile(r'^\#[a-z]+\.(?P<year>\d{4})-(?P<month>\d{2})'
#                          r'-(?P<day>\d{2})\.log$')
    _file_re = re.compile(r'^\#[a-z]+\.(?P<year>\d{4})(?P<month>\d{2})'
                          r'(?P<day>\d{2})\.log$')

    path = Option('irclogs', 'path', doc='Path to logs')
    indexer = Option('irclogs', 'indexer', doc='Pyndexter indexer URI')
    prefix = Option('irclogs', 'prefix', doc='File prefix')

    anchor_set = None

    def _render_lines(self, iterable, req):
        result = []
        for line in iterable:
            rdict = {}
            d = getattr(self._line_re.search(line), 'groupdict', dummy)()
            for mode in ('channel', 'action', 'server'):
                prefix = mode[0]
                text = d.get('%s_text' % prefix)
                if not text is None:
                    nick = d['%s_nickname' % prefix]
                    break
            else:
                continue
            rdict['date'] = d['date']
            rdict['time'] = d['time']
            rdict['mode'] = mode
            rdict['text'] = to_utf8(text)
            rdict['nickname'] = nick
            rdict['class'] = 'nick-%d' % (sum(ord(c) for c in nick) % 8)
            result.append(rdict)
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
                        'href':     self.env.href('irclogs', year,
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
            next_month_href = self.env.href('irclogs', next_month_year,
                                            '%02d' % next_month, '%02d' % today)
        else:
            next_month_href = self.env.href('irclogs', next_month_year,
                                            '%02d' % next_month)

        prev_month_year = year
        prev_month = int(month) - 1
        if prev_month < 1:
            prev_month_year -= 1
            prev_month = 12
        if today > -1:
            prev_month_href = self.env.href('irclogs', prev_month_year,
                                            '%02d' % prev_month, '%02d' % today)
        else:
            prev_month_href = self.env.href('irclogs', prev_month_year,
                                            '%02d' % prev_month)

        return {
            'year':         year,
            'month':        month,
            'weeks':        weeks,
            'next_year':    {
                'caption':      str(year + 1),
                'href':         self.env.href('irclogs', year + 1)
            },
            'prev_year':    {
                'caption':      str(year - 1),
                'href':         self.env.href('irclogs', year - 1)
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

    # ISearchSource
    def get_search_filters(self, req):
        if not req.perm.has_permission('IRCLOGS_VIEW'):
            return []
        return [('irclogs', 'IRC Logs', True),]

    def find_anchor(self, text, terms):
        pos = 0
        for l in text.lower().split('\n'):
            for t in terms:
                if t in l: 
                    d = getattr(self._line_re.search(l), 'groupdict', dummy)()            
                    return '#T%s' % str(d['time'])
                continue
            continue
        return ''

    def get_search_results(self, req, terms, filters):
        def _cut_line(text, size):
            """Cut the line down appending ... if the line is larger """
            if len(text) > size:
                return text[:size] + ' ...'
            return text

        if not 'irclogs' in filters:
            return

        import time
        from datetime import datetime
        from pyndexter import Framework, READONLY
        from pyndexter.util import quote
        framework = Framework(self.indexer, stemmer='porter://', mode=READONLY)
        framework.add_source('file://%s?include=*.log' % quote(self.path))
        try:
            for hit in framework.search(' '.join(terms)):
                path = hit.uri.path
                anchor = self.find_anchor(hit.current.content, terms)
                year, month, day = path[-12:-8], path[-8:-6], path[-6:-4]
                timestamp = time.mktime(datetime(int(year), int(month), int(day)).timetuple())
                yield (req.href('/irclogs/%s/%s/%s' % (year, month, day)) + anchor, 
                       '%s logs for %s-%s-%s' % (self.prefix, year, month, day), 
                       timestamp, 
                       'irclog', 
                       unicode(hit.excerpt(terms)))
        except Exception, e:
            self.log.debug('pyndexter has a big fat bug.  Give alect crap about it.', exc_info=e)
            return

    # INavigationContributor methods
    def get_active_navigation_item(self, req):
        return 'irclogs'

    def get_navigation_items(self, req):
        if not req.perm.has_permission('IRCLOGS_VIEW'):
            return
        yield 'mainnav', 'irclogs', Markup('<a href="%s">IRC Logs</a>' \
                                    % escape(self.env.href.irclogs()))

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
        path = os.path.abspath(self.path)
        prefix = self.prefix
        add_stylesheet(req, 'irclogs/style.css')

        entries = {}
        files = os.listdir(path)
        files.sort()
        for fn in files:
            m = self._file_re.search(fn)
            if m is None:
                continue
            d = m.groupdict()
            y = entries.setdefault(int(d['year']), {})
            m = y.setdefault(int(d['month']), {})
            m[int(d['day'])] = True

        if req.args['year'] is None:
            years = entries.keys()
            years.sort()
            req.hdf['years'] = [{
                'caption':      y,
                'href':         self.env.href('irclogs', y)
            } for y in years]
            req.hdf['viewmode'] = 'years'
        elif req.args['month'] is None:
            months = entries.get(int(req.args['year']), {}).keys()
            months.sort()
            req.hdf['months'] = [{
                'caption':      m,
                'href':         self.env.href('irclogs', req.args['year'],
                                              '%02d' % m)
            } for m in months]
            req.hdf['year'] = req.args['year']
            req.hdf['viewmode'] = 'months'
        elif req.args['day'] is None:
            year = entries.get(int(req.args['year']), {})
            days = year.get(int(req.args['month']), {}).keys()
            days.sort()
            req.hdf['days'] = [{
                'caption':      d,
                'href':         self.env.href('irclogs', req.args['year'],
                                              req.args['month'], '%02d' % d)
            } for d in days]
            req.hdf['year'] = req.args['year']
            req.hdf['month'] = req.args['month']
            req.hdf['viewmode'] = 'days'

        req.hdf['cal'] = self._generate_calendar(req, entries)

        # Detail View
        if not req.args['day'] is None:
            logfile = os.path.join(path, '%s.%s%s%s.log' % (
                prefix,
                req.args['year'],
                req.args['month'],
                req.args['day']
            ))
            if not os.path.exists(logfile):
                raise TracError('Logfile not found')
            f = file(logfile)
            req.hdf['day'] = req.args['day']
            req.hdf['month'] = req.args['month']
            req.hdf['year'] = req.args['year']
            req.hdf['lines'] = self._render_lines(f, req)
            f.close()
            return 'irclogs_show.cs', None

        # Index View
        return 'irclogs_index.cs', None

    # ITemplateProvider methods
    def get_templates_dirs(self):
        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename
        return [('irclogs', resource_filename(__name__, 'htdocs'))]
