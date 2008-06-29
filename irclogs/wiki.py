import re

from trac.core import *
from trac.wiki import IWikiSyntaxProvider
from trac.wiki.formatter import system_message
from trac.util.html import html

class IrcLogWiki(Component):
    """Creates a link to the IRC log viewer for a particular date
       including the anchor to the message timestamp"""
    implements(IWikiSyntaxProvider) 

    date_re = re.compile(r'^UTC(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})')

    # IWikiSyntaxProvider methods
    def get_wiki_syntax(self):
        return []
    
    def get_link_resolvers(self):
        yield ('irclog', self._format_link)

    def _format_link(self, formatter, ns, target, label):
       m = self.date_re.match(target)
       if not m:
           return system_message('Invalid IRC Log Link: '
                         'Must be of the format UTCYYYY-MM-DDTHH:MM:SS %s')
       return html.a(label, title=label, 
                     href=formatter.href.irclogs(m.group('year'),
                                                 m.group('month'),
                                                 m.group('day'),) + 
                            '#%s' % target)
