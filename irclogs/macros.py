import os
import re
from datetime import datetime
from trac.web.chrome import add_stylesheet, add_script, Chrome
from trac.wiki.macros import WikiMacroBase
from trac.wiki.formatter import system_message
from trac.wiki.api import parse_args
from web_ui import IrcLogsView

class IrcLogLiveMacro(WikiMacroBase):
    """Displays a live in-page feed of the current IRC log.  
    Can take 2 parameters:
     * polling frequency (seconds) default to 60
     * number of messages displayed - defaults to 10
    """
    def expand_macro(self, formatter, name, content):

        args, kw = parse_args(content)
        poll_frequency = args and args[0] or 60
        count = args and args[1] or 10

        if not (0==len(args) or 2==len(args)):
            return system_message('Incorrect arguments: ' 
                'Must be of the format (poll frequency, lines to display)')

        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        add_script(formatter.req, 'irclogs/js/jquery.timer.js')

        data = Chrome(self.env).populate_data(formatter.req, 
                                    {'poll_frequency':int(poll_frequency)*1000,
                                     'count':count})
        return Chrome(self.env).load_template('macro_live.html') \
                                    .generate(**data)

class IrcLogQuoteMacro(WikiMacroBase):
    """Display contents of a logged IRC chat.  Takes parameters 
    of the UTC timestamp of the message and the number of messages to show.
    `[[IrcLogsQuote(UTCYYYY-MM-DDTHH:MM:SS,message_count]])`
    
    To get the UTC timestamp, click on the time displayed in the IRC 
    log view page and copy the anchor from your browsers location bar.
    """

    date_re = re.compile(r'^UTC(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
                         'T(?P<time>\d{2}:\d{2}:\d{2})')
    
    def expand_macro(self, formatter, name, content):
        args, kw = parse_args(content)
        utc_dt = args and args[0] or None
        if not utc_dt:
            return system_message('IrcLogQuote: Timestamp required')
        d = self.date_re.match(utc_dt)
        if not d:
            return system_message('IrcLogQuote: Invalid timestamp format')
        offset = int(args and len(args)>1 and args[1] or 10)

        irclogs =  IrcLogsView(self.env)        
        logfile = irclogs._get_filename(d.group('year'),
                                        d.group('month'),
                                        d.group('day'))
        if (not os.path.isfile(logfile)):
            return system_message('IrcLogQuote: No log file for this date')
        iterable = irclogs._to_unicode(file(logfile))
        lines = irclogs._render_lines(iterable, formatter.req.tz)

        filtered_lines = [line for line in lines 
                                if unicode(line['utc_dt']) >= utc_dt
                                    and line['mode'] == 'channel'
                                    and line['hidden_user'] != 'hidden_user']
        
        add_stylesheet(formatter.req, 'irclogs/css/irclogs.css')
        data = Chrome(self.env).populate_data(formatter.req, 
                                    {'lines':filtered_lines[:offset],
                                     'excerpt_date':d.groupdict(),
                                     'utc_dt':utc_dt})
        return Chrome(self.env).load_template('macro_quote.html') \
                                    .generate(**data)
    
