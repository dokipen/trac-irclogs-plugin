"""
Parse logs from files into structured data.  This is based on Marius Gedminas'
port of Jeff Waugh perl script.
"""

# Copyright (c) 2009, Robert Corsaro
# Copyright (c) 2005--2008, Marius Gedminas 
# Copyright (c) 2000, Jeffrey W. Waugh

# Trac port:
#   Robert Corsaro <rcorsaro@optaros.com>
# Python port:
#   Marius Gedminas <marius@pov.lt>
# Original Author:
#   Jeff Waugh <jdub@perkypants.org>
# Contributors:
#   Rick Welykochy <rick@praxis.com.au>
#   Alexander Else <aelse@uu.net>
#   Ian Weller <ianweller@gmail.com>
#
# Released under the terms of the GNU GPL
# http://www.gnu.org/copyleft/gpl.html

# Differences:
#
# Just parsing code is stripped out for this trac module and many
# parameters are now configurable.  Defaults should work with Supybot logs.
import re

from trac.core import *
from trac.config import Option

from irclogs.api import IIRCLogsProvider

class FileIRCLogProvider(Component):
    """Provide logs from irc log files.  All default regex config parameters
    match the default Supybot log files, where defaults are provided.
    """

    implements(IIRCLogsProvider)

    log_timezone = Option('irclogs', 'file_log_timezone', 'utc',
        doc="""Timezone that the files are logged in.  This is needed
        so we can convert the incoming date to the date in the irc
        log file names.  And find all files in the range.""")

    path_format = Option('irclogs', 'file_path_format', None,
        doc="""
       Format for complete path to log files.  Include parameters:
          %Y, %m, %d, etc. : all strftime formatting supported
          %(network)s      : network
          %(channel)s      : channel
       Example:
          /var/irclogs/ChannelLogger/%(channel)s/%(channel)s.%Y-%m-%d.log
          """)

    time_format = Option('irclogs', 'time_format', '%Y-%m-%dT%H%M%S',
        doc="""Format to use when parsing timestamp in log files.
        For gozerbot logs, change the 'T' to ' ' (space).""")

    timestamp_regex = Option('irclogs', 'timestamp_regex', 
        '(?P<timestamp>\d{4}-\d{2}-\d{2}.\d{2}:\d{2}:\d{2})',
        doc="""Partial regex used at the beginning of all other regexes. 
        It is only used if explicitly included in the other regexes as
        %(timestamp_regex)s

        ex. 2009-05-20T10:10:10
        ex. 2009-05-20 10:10:10
        """)

    comment_regex = Option('irclogs', 'nick_regex', 
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message><(?P<nick>[^>]+)>\s(?P<comment>.*))$', 
        doc="""Matches COMMENT lines. 

        ex. 2009-05-20T10:10:10  <nick> how's it going?
        ex. 2009-05-20 10:10:10 | <nick> how's it going?
        """)

    action_regex = Option('irclogs', 'action_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*\s(?P<nick>[^ ]+)\s(?P<action>.*))$',
        doc="""Matches ACTION lines. 

        ex. 2009-05-20T10:10:10  * nick hits someone with a fish
        ex. 2009-05-20 10:10:10 | * nick hits someone with a fish
        """)

    join_regex = Option('irclogs', 'join_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\shas\sjoined.*)$',
        doc="""Matches JOIN lines.

        ex. 2009-05-20T10:10:10  *** nick has joined #channel
        ex. 2009-05-20 10:10:10 | nick has joined
        """)

    part_regex = Option('irclogs', 'part_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+).*\shas\sleft.*)$',
        doc="""Matches PART lines.

        ex. 2009-05-20T10:10:10  *** nick has left #channel
        ex. 2009-05-20 10:10:10 | nick has left
        """)

    quit_regex = Option('irclogs', 'quit_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+).*\shas\squit.*)$',
        doc="""Matches QUIT lines.

        ex. 2009-05-20T10:10:10  *** nick has quit IRC
        ex. 2009-05-20 10:10:10 | nick has quit: I'm outta he--ya
        """)

    kick_regex = Option('irclogs', 'kick_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<kicked>[^ ]+)\swas\skicked\sby\s(?P<nick>[^ ]+).*)$',
        doc="""Matches KICK lines.

        ex. 2009-05-20T10:10:10  *** kickedguy was kicked by nick
        ex. 2009-05-20 10:10:10 | kickedguy was kicked by nick
        """)

    mode_regex = Option('irclogs', 'mode_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\ssets\smode:\s(?P<mode>.+))$',
        doc="""Matches MODE lines.

        ex. 2009-05-20T10:10:10  *** nick sets mode: +v guy
        ex. 2009-05-20 10:10:10 | nick sets mode: +v guy
        """)

    topic_regex = Option('irclogs', 'topic_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s(?P<nick>[^ ]+)\schanges\stopic\sto\s"?(?P<topic>.+)"?)$',
        doc="""Matches TOPIC lines.

        ex. 2009-05-20T10:10:10  *** nick changes topic to "new topic"
        ex. 2009-05-20 10:10:10 | nick changes topic to "new topic"
        """)

    nick_regex = Option('irclogs', 'nickchange_regex',
            '^%(timestamp_regex)s\s{2}(?P<message>\*{3}\s(?P<nick>.*)\s.*now\sknown\sas(?P<newnick>.*))$',
            doc="""Matches NICK
            """)
    notice_regex = Option('irclogs', 'notice_regex', "timestamp  -nick- message")

    match_order = Option('irclogs', 'match_order',
            'comment part join quit action kick mode topic',
            doc="""Order that lines are checked against.  This matters if a 
            line could match multiple regexes.""")

    def parse_lines(self, lines):
        match_list = re.split('[,|: ]+', self.match_order)
        def _map(x):
            regex_string = self.__getattribute__('%s_regex'%(x,))
            regex_string = regex_string%({
                'whoha': 'hello',
                'timestamp_regex': self.timestamp_regex
            })
            regex = re.compile(regex_string)
            return {
                    'type': x, 
                    'regex': regex
            }
       
        def _parse_time(time):
            return 1

        matchers = map(_map, match_list)

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

