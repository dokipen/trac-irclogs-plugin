from trac.util.datefmt import localtz
from trac.core import *
from trac.search import ISearchSource
from trac.config import Option

from irclogs import util

try:
    from pyndexter import Framework, READWRITE
    from pyndexter.util import quote

    import pytz
    import web_ui


    class IrcLogsSearch(Component):
        implements(ISearchSource)

        def get_search_filters(self, req):
            if not req.perm.has_permission('IRCLOGS_VIEW'):
                return []
            return [('irclogs', 'IRC Logs', True)]


        def get_search_results(self, req, terms, filters):
            def _cut_line(text, size):
                if len(text) > size:
                    return text[:size] + '...'
                return text
            if not 'irclogs' in filters:
                return
            
            irclogs = web_ui.IrcLogsView(self.env)
            
            framework = Framework('builtin://%s.idx'%(
                quote(irclogs.search_db_path)), mode=READWRITE)
            framework.add_source('file://%s' % quote(irclogs.path))
            tz = req.tz
            utc = pytz.utc
            unicode_terms = []
            for term in terms:
                unicode_terms.append(unicode(term))

            for hit in framework.search(' '.join(terms)):
                path = hit.uri.path
                server_dt = self.find_anchor(irclogs, hit.current.content, terms)

                if server_dt is None:
                    continue

                utc_dt = utc.normalize(server_dt.astimezone(utc))
                user_dt = tz.normalize(server_dt.astimezone(tz))
                user_time = user_dt.strftime("%H:%M:%S")
                anchor = utc_dt.strftime("#UTC%Y-%m-%dT%H:%M:%S")
                year, month, day, hour, minute, second = \
                    path[-14:-10], path[-9:-7], path[-6:-4], user_time[0:2], \
                    user_time[3:5], user_time[6:8]
                timestamp = user_dt.replace(tzinfo=localtz)
                yield req.href('/irclogs/%s/%s/%s' % (year, month, day)) + anchor, \
                               'IRC: logs for %s-%s-%s' % \
                               (year, month, day), \
                               timestamp, 'irclog', \
                               hit.excerpt(unicode_terms)
            framework.close()

        def find_anchor(self, irclogs, text, terms):
            dummy = lambda: {}
            pos = 0
            for l in text.split('\n'):
                for t in terms:
                    if t in l:
                        d = getattr(irclogs._line_re.search(l), 
                                    'groupdict', dummy)()
                        server_dt = irclogs._get_tz_datetime(d['date'], d['time'])
                        return server_dt
                    continue
                continue
            return None

        def index_logs(self):
            irclogs = web_ui.IrcLogsView(self.env)
            framework = Framework('builtin://%s/%s.idx' % 
                                  (quote(irclogs.search_db_path)))
            framework.add_source('file://%s' % quote(irclogs.path))
            framework.update()
            framework.close()
except ImportError:
    class IrcLogsSearch(Component):
        implements(ISearchSource)
        def get_search_filters(self, req):
            raise Exception("""irclog search not supported because 
            pyndexter failed to load.  Please install pyndexter or disable 
            irclogs.search.irclogssearch in trac.ini""")

        def get_search_results(self, req, terms, filters):
            raise Exception("""irclog search not supported because 
            pyndexter failed to load.  Please install pyndexter or disable 
            irclogs.search.irclogssearch in trac.ini""")
            
