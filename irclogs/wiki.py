import re
from datetime import datetime
from time import strptime, strftime
from pytz import timezone, UTC

from trac.core import *
from trac.wiki import IWikiSyntaxProvider
from trac.wiki.formatter import system_message
from trac.util.html import html

from irclogs.api import IRCChannelManager

class IrcLogWiki(Component):
    """Creates a link to the IRC log viewer for a particular date
       including the anchor to the message timestamp"""
    implements(IWikiSyntaxProvider) 

    date_re = re.compile(
            r'^((?P<channel>[^-]+)-?)?(UTC(?P<datetime>(?P<year>\d{4})' +
            r'-(?P<month>\d{2})-(?P<day>\d{2})(T(?P<time>\d{2}:\d{2}:\d{2})))?)?$')
    date_format = '%Y-%m-%dT%H:%M:%S'
    time_format = '%H:%M:%S'

    # IWikiSyntaxProvider methods
    def get_wiki_syntax(self):
        return []
    
    def get_link_resolvers(self):
        yield ('irclog', self._format_link)

    def _format_link(self, formatter, ns, target, label):
       m = self.date_re.match(target)
       if not m:
           return system_message('Invalid IRC Log Link: '
                     'Must be of the format channel-UTCYYYY-MM-DDTHH:MM:SS %s')
       if not m.group('datetime'):
           return html.a(label, title=label, href=formatter.href.irclogs(
               m.group('channel')))
       else:
           ch_mgr = IRCChannelManager(self.env)
           t = strptime(m.group('datetime'), self.date_format)
           dt = UTC.localize(datetime(*t[:6]))
           dt = ch_mgr.to_user_tz(formatter.req, dt)
           timestr = dt.strftime(self.time_format)
           return html.a(label, title=label, href=formatter.href.irclogs(
                     m.group('channel'), '%02d'%dt.year, '%02d'%dt.month, 
                     '%02d'%dt.day,) + '#%s'%timestr)
