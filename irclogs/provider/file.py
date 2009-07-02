"""
Parse logs from files into structured data.  inspired by Marius Gedminas'
port of Jeff Waugh perl script.
"""

# Copyright (c) 2009, Robert Corsaro

import re
from time import strptime
from datetime import datetime
from pytz import timezone

from trac.core import *
from trac.config import Option

from irclogs.api import IIRCLogsProvider

class FileIRCLogProvider(Component):
    """Provide logs from irc log files.  All default regex config parameters
    match the default Supybot log files, where defaults are provided.
    """

    implements(IIRCLogsProvider)

    format = Option('irclogs', 'format', 'supy', doc="Default format")

    timezone = Option('irclogs', 'timezone', 'utc',
        doc="""Default timezone that the files are logged in.  This is needed
        so we can convert the incoming date to the date in the irc
        log file names.  And find all files in the range. This can be 
        overridden by the format.
        """)

    basepath = Option('irclogs', 'basepath', '/var/lib/irclogs',
        doc="""Default basepath for logs.  Can be overridden by format.""")

    path = Option('irclogs', 'path', '%(channel)s/%(channel)s.%Y-%m-%d.log',
        doc="""
       Default format for complete path to log files.  Include parameters:
          %Y, %m, %d, etc. : all strftime formatting supported
          %(network)s      : network
          %(channel)s      : channel
       Example:
          %(channel)s/%(channel)s.%Y-%m-%d.log
          %(channel)s.%Y%m%d.log

       Can be overridden by format.""")

    timestamp_format = Option('irclogs', 'timestamp_format', '%Y-%m-%dT%H:%M:%S',
        doc="""Default format to use when parsing timestamp to datetime. Can 
        be overridden by format.""")

    timestamp_regex = Option('irclogs', 'timestamp_regex', 
        '(?P<timestamp>\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2})',
        doc="""Default partial regex used at the beginning of all other 
        regexes.  It is only used if explicitly included in the other regexes 
        as %(timestamp_regex)s

        ex. 2009-05-20T10:10:10
        ex. 2009-05-20 10:10:10

        Can be overriedden by format.""")

    comment_regex = Option('irclogs', 'comment_regex', 
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message><(?P<nick>[^>]+)>\s(?P<comment>.*))$', 
        doc="""Default match for COMMENT lines. 

        ex. 2009-05-20T10:10:10  <nick> how's it going?
        ex. 2009-05-20 10:10:10 | <nick> how's it going?
        
        Can be overridden by format.""")

    action_regex = Option('irclogs', 'action_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*\s(?P<nick>[^ ]+)\s(?P<action>.*))$',
        doc="""Default match for ACTION lines. 

        ex. 2009-05-20T10:10:10  * nick hits someone with a fish
        ex. 2009-05-20 10:10:10 | * nick hits someone with a fish

        Can be overridden by format.""")

    join_regex = Option('irclogs', 'join_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\shas\sjoined.*)$',
        doc="""Default match on JOIN lines.

        ex. 2009-05-20T10:10:10  *** nick has joined #channel
        ex. 2009-05-20 10:10:10 | nick has joined

        Can be overridden by format.""")

    part_regex = Option('irclogs', 'part_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+).*\shas\sleft.*)$',
        doc="""Default match on PART lines.

        ex. 2009-05-20T10:10:10  *** nick has left #channel
        ex. 2009-05-20 10:10:10 | nick has left

        Can be overridden by format.""")

    quit_regex = Option('irclogs', 'quit_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+).*\shas\squit.*)$',
        doc="""Default match QUIT lines.

        ex. 2009-05-20T10:10:10  *** nick has quit IRC
        ex. 2009-05-20 10:10:10 | nick has quit: I'm outta he--ya

        Can be overridden by format.""")

    kick_regex = Option('irclogs', 'kick_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<kicked>[^ ]+)\swas\skicked\sby\s(?P<nick>[^ ]+).*)$',
        doc="""Default match KICK lines.

        ex. 2009-05-20T10:10:10  *** kickedguy was kicked by nick
        ex. 2009-05-20 10:10:10 | kickedguy was kicked by nick

        Can be overridden by format.""")

    mode_regex = Option('irclogs', 'mode_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\ssets\smode:\s(?P<mode>.+))$',
        doc="""Default match on MODE lines.

        ex. 2009-05-20T10:10:10  *** nick sets mode: +v guy
        ex. 2009-05-20 10:10:10 | nick sets mode: +v guy

        Can be overridden by format.""")

    topic_regex = Option('irclogs', 'topic_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\schanges\stopic\sto\s"(?P<topic>.+)")$',
        doc="""Default match on TOPIC lines.

        ex. 2009-05-20T10:10:10  *** nick changes topic to "new topic"
        ex. 2009-05-20 10:10:10 | nick changes topic to "new topic"

        Can be overridden by format.""")

    nick_regex = Option('irclogs', 'nick_regex',
        '^%(timestamp_regex)s[ |:]*'\
                '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)(?:\sis)\s.*now\sknown\sas\s(?P<newnick>.*))$',
        doc="""Default match on NICK lines.

        ex. 2009-05-20T10:10:10  *** nick is now known as nick2
        ex. 2009-05-20 10:10:10 | nick is now known as nick2"

        Can be overridden by format.""")

    notice_regex = Option('irclogs', 'notice_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>-(?P<nick>[^-]+)-\s(?P<comment>.*))$',
        doc="""Default match on NOTICE lines.

        ex. 2009-05-20T10:10:10  -nick- hello everyone! 
        ex. 2009-05-20 10:10:10 | -nick- hello everyone!"

        Can be overridden by format.""")

    match_order = Option('irclogs', 'match_order',
            'comment part join quit action kick mode topic nick notice',
            doc="""Default order that lines are checked against.  This matters 
            if a line could match multiple regexes.  Can be overridden by 
            format.""")

    Option('irclogs', 'format.gozer.basepath', '/home/gozerbot/.gozerbot/')
    Option('irclogs', 'format.gozer.path', 'logs/trac/%(channel)s.%Y%m%d.log')
    Option('irclogs', 'format.gozer.timestamp_format', '%Y%m%d %H%M%S')

    def default_format(self):
        format = {
                'basepath': self.basepath,
                'path': self.path,
                'match_order': self.match_order,
                'timestamp_format': self.timestamp_format,
                'timestamp_regex': self.timestamp_regex,
        }
        match_order = re.split('[,|: ]+', format['match_order'])
        for mtype in match_order:
            regex_name = "%s_regex"%(mtype) 
            format[regex_name] = self.__getattribute__(regex_name)
        return format

    def format(self, name):
        pass

    def parse_lines(self, lines, format=None, tz=None):
        if not format: 
            format = self.default_format()
        if not tz:
            tz = timezone(self.timezone)

        def _map(x):
            regex_string = format['%s_regex'%(x)]
            regex_string = regex_string%({
                'timestamp_regex': format['timestamp_regex']
            })
            regex = re.compile(regex_string)
            return { 'type': x, 'regex': regex }
        match_order = re.split('[,|: ]+', format['match_order'])
        matchers = map(_map, match_order)

        def _parse_time(time):
            t = strptime(time, format['timestamp_format'])
            return datetime(*t[:6]).replace(tzinfo=tz)

        for line in lines:
            line = line.rstrip('\r\n')
            if not line:
                continue
            matched = False
            for matcher in matchers:
                msgtype = matcher['type']
                match_re = matcher['regex']
                m = match_re.match(line)
                if m:
                    result = m.groupdict()
                    if result['timestamp']:
                        timestamp = _parse_time(result['timestamp'])
                        result['timestamp'] = timestamp
                    result['type'] = msgtype
                    yield result
                    matched = True
                    break
            if not matched:
                yield {'type': 'other', 'message': line}

