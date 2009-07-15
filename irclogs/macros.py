import os
import re
from time import strptime
from datetime import datetime, timedelta
from pytz import timezone

from trac.web.chrome import add_stylesheet, add_script, Chrome
from trac.wiki.macros import WikiMacroBase
from trac.wiki.formatter import system_message
from trac.wiki.api import parse_args
from web_ui import IrcLogsView

class IrcLogLiveMacro(WikiMacroBase):
    """Displays a live in-page feed of the current IRC log.  
    Can take 3 parameters:
     * channel
     * polling frequency (seconds) default to 60
     * number of messages displayed - defaults to 10
    """
    def expand_macro(self, formatter, name, content):
        print 'fuck you'
        args, kw = parse_args(content)
        self.log.error(args)
        channel = args and args[0] 
        poll_frequency = int(args and args[1] or 60)*1000
        count = int(args and args[1] or 10)

        if not (channel and poll_frequency and count):
            return system_message('Incorrect arguments: ' 
                'Must be of the format (channel, poll frequency seconds, lines to display)')

        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        add_script(formatter.req, 'irclogs/js/jquery.timer.js')

        data = Chrome(self.env).populate_data(formatter.req, {
             'channel': channel,
             'poll_frequency': poll_frequency,
             'count': count
        })
        return Chrome(self.env).load_template('macro_live.html').\
                                    generate(**data)

class IrcLogQuoteMacro(WikiMacroBase):
    """Display contents of a logged IRC chat.  Takes parameters 
    of the UTC timestamp of the message and the number of messages to show.
    `[[IrcLogsQuote(channel, UTCYYYY-MM-DDTHH:MM:SS, message_count]])`
    
    To get the UTC timestamp, click on the time displayed in the IRC 
    log view page and copy the anchor from your browsers location bar.
    """

    date_re = re.compile('^UTC(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})T(?P<time>\d{2}:\d{2}:\d{2})')
    date_format = "UTC%Y-%m-%dT%H:%M:%S"
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)
        channel = args and args[0].strip()
        utc_dt = args and args[1].strip()
        if not (utc_dt and channel):
            return system_message('IrcLogQuote: arguments required (channel,'\
                    ' timestamp(UTCYYYY-MM-DDTHH:MM:SS), seconds)')
        self.log.error(args)
        self.log.error(kw)
        d = self.date_re.match(utc_dt.strip())
        if not d:
            return system_message('IrcLogQuote: Invalid timestamp format')
        offset = int(args and len(args)>2 and args[2] or 10)

        irclogs = IrcLogsView(self.env)        
        start = datetime(*strptime(utc_dt, self.date_format)[:6], 
                tzinfo=timezone('utc'))
        end = start + timedelta(seconds=offset)
        provider = irclogs.get_provider(channel)
        lines = provider.get_events_in_range(channel, start, end)
        lines = filter(irclogs._hide_nicks, map(irclogs._map_lines, lines))

        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        data = Chrome(self.env).populate_data(
            formatter.req, 
            {
                'channel': channel,
                'lines': lines,
                'year': '%04d'%(start.year),
                'month': '%02d'%(start.month),
                'day': '%02d'%(start.day),
                'time': start.strftime("%H:%M:%S")
            }
        )
        return Chrome(self.env).load_template('macro_quote.html') \
                                    .generate(**data)

