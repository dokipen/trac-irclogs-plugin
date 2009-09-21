import os
import re
from time import strptime
from datetime import datetime, timedelta
from pytz import timezone

from trac.web.chrome import add_stylesheet, add_script, Chrome
from trac.wiki.macros import WikiMacroBase
from trac.wiki.formatter import system_message
from trac.wiki.api import parse_args
from irclogs.web_ui import IrcLogsView
from irclogs.api import IRCChannelManager

class IrcLogLiveMacro(WikiMacroBase):
    """Displays a live in-page feed of the current IRC log.  
    Can take 3 parameters:
     * channel: channel
     * polling_frequency: (seconds) default to 60
     * count: number of messages displayed - defaults to 10

    """
    def expand_macro(self, formatter, name, content):
        _, kw = parse_args(content)
        channel_name = kw.get('channel')
        poll_frequency = int(kw.get('poll_frequency', 60))*1000
        count = int(kw.get('count', 10))

        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        add_script(formatter.req, 'irclogs/js/jquery.timer.js')

        data = Chrome(self.env).populate_data(formatter.req, {
             'channel': channel_name,
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
        _, kw = parse_args(content)
        channel_name = kw.get('channel')
        utc_dt = kw.get('datetime')
        if not utc_dt:
            return system_message('IrcLogQuote: arguments required '\
                '(channel=channel, datetime=timestamp(UTCYYYY-MM-DDTHH:MM:SS), '\
                'offset=seonds)')
        d = self.date_re.match(utc_dt.strip())
        if not d:
            return system_message('IrcLogQuote: Invalid timestamp format')
        offset = int(kw.get('offset', 10))

        irclogs = IrcLogsView(self.env)        
        ch_mgr = IRCChannelManager(self.env)
        start = datetime(*strptime(utc_dt, self.date_format)[:6])
        start = start.replace(tzinfo=timezone('utc'))
        start = ch_mgr.to_user_tz(formatter.req, start)
        end = start + timedelta(seconds=offset)
        channel = ch_mgr.channel(channel_name)
        formatter.req.perm.assert_permission(channel.perm())
        lines = channel.events_in_range(start, end)
        lines = filter(lambda x: not x.get('hidden'), 
                map(irclogs._map_lines, lines))
        rows = map(irclogs._render_line, lines)

        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        data = Chrome(self.env).populate_data(
            formatter.req, 
            {
                'channel': channel_name,
                'lines': lines,
                'year': '%04d'%(start.year),
                'month': '%02d'%(start.month),
                'day': '%02d'%(start.day),
                'time': start.strftime("%H:%M:%S"),
                'rows': rows
            }
        )
        return Chrome(self.env).load_template('macro_quote.html') \
                                    .generate(**data)

