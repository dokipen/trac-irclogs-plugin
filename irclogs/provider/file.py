"""
Parse logs from files into structured data.  Inspired by Marius Gedminas'
port of Jeff Waugh perl script.

TODO: something about defining formats and channels.

One of the challenges of implementing this class is timezones.  Displaying
logs for a certain day, midnight to midnight, is different for users depending
on their timezone.   We must translate the requested timezone to the timezone
of the log files, find a date range of files to read, and filter out and lines
that don't fall in the range.

Another challenge is that some systems make multiple, parrellel log files.  
Gozerbot simple logging creates one log file for messages and another for
other events.  We must merge these files into a common set of lines before 
yielding them back to the caller.  The caller should get all lines in order.
To make matters worse, some lines don't have timestamps.  We must assign
these lines a best guess timestamp equal to the previously logged line.
"""

# Copyright (c) 2009, Robert Corsaro

import re
from time import strptime, strftime
from datetime import datetime, timedelta
from pytz import timezone, UnknownTimeZoneError
import os.path
import itertools
import operator
import heapq

from trac.core import *
from trac.config import Option, ListOption

from irclogs.api import *

# this is used for comparison only, and never included in yielded
# values
OLDDATE = datetime(1977,8,3,0,0,0,tzinfo=timezone('utc'))

class FileIRCLogProvider(Component):
    """Provide logs from irc log files.  All default regex config parameters
    match the default Supybot log files, where defaults are provided.
    The gozerbot log format is also supported out of the box by setting 
    [irclogs]
    format = gozer
    # or 
    channel.test.format = gozer
    """

    implements(IIRCLogsProvider)

    # not to be confused with default_format(), which doesn't consider
    # a named format.
    format = Option('irclogs', 'format', 'supy', 
            doc="The name of the default format to use.")

    basepath = Option('irclogs', 'basepath', '/var/lib/irclogs',
        doc="""Default basepath for logs.  Can be overridden by format.""")

    paths = ListOption('irclogs', 'paths', '%(channel)s/%(channel)s.%Y-%m-%d.log',
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
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+).*\shas\sjoined.*)$',
        doc="""Default match on JOIN lines.

        ex. 2009-05-20T10:10:10  *** nick has joined #channel
        ex. 2009-05-20 10:10:10 | nick has joined

        Can be overridden by format.""")

    part_regex = Option('irclogs', 'part_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+).*\shas\sleft.*)$',
        doc="""Default match on PART lines.

        ex. 2009-05-20T10:10:10  *** nick has left #channel
        ex. 2009-05-20 10:10:10 | nick has left

        Can be overridden by format.""")

    quit_regex = Option('irclogs', 'quit_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+).*\shas\squit.*)$',
        doc="""Default match QUIT lines.

        ex. 2009-05-20T10:10:10  *** nick has quit IRC
        ex. 2009-05-20 10:10:10 | nick has quit: I'm outta he--ya

        Can be overridden by format.""")

    kick_regex = Option('irclogs', 'kick_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<kicked>[^ ]+)\swas\skicked\sby\s(?P<nick>[^ ]+).*)$',
        doc="""Default match KICK lines.

        ex. 2009-05-20T10:10:10  *** kickedguy was kicked by nick
        ex. 2009-05-20 10:10:10 | kickedguy was kicked by nick

        Can be overridden by format.""")

    mode_regex = Option('irclogs', 'mode_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+)\ssets\smode:\s(?P<mode>.+))$',
        doc="""Default match on MODE lines.

        ex. 2009-05-20T10:10:10  *** nick sets mode: +v guy
        ex. 2009-05-20 10:10:10 | nick sets mode: +v guy

        Can be overridden by format.""")

    topic_regex = Option('irclogs', 'topic_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+)\schanges\stopic\sto\s"(?P<topic>.+)")$',
        doc="""Default match on TOPIC lines.

        ex. 2009-05-20T10:10:10  *** nick changes topic to "new topic"
        ex. 2009-05-20 10:10:10 | nick changes topic to "new topic"

        Can be overridden by format.""")

    nick_regex = Option('irclogs', 'nick_regex',
        '^%(timestamp_regex)s[ |:]*'\
        '(?P<message>\*{0,3}\s?(?P<nick>[^ ]+).*\sis\snow\sknown\sas\s(?P<newnick>.*))$',
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

    # gozer format
    ListOption('irclogs', 'format.gozer.paths', 
            ['logs/%(network)s/simple/%(channel)s.%Y%m%d.slog', 
                'logs/%(network)s/simple/%(channel_name)s.%Y%m%d.slog'])
    Option('irclogs', 'format.gozer.timestamp_format', '%Y-%m-%d %H:%M:%S')

    # bip format
    ListOption('irclogs', 'format.bip.paths', '%(network)s/%Y-%m/%(channel)s.%d.log')
    Option('irclogs', 'format.bip.timestamp_format', '%d-%m-%Y %H:%M:%S')
    Option('irclogs', 'format.bip.timestamp_regex', '(?P<timestamp>\d{2}-\d{2}-\d{4}.\d{2}:\d{2}:\d{2})')
    Option('irclogs', 'format.bip.comment_regex', '^%(timestamp_regex)s\s(?P<message>[<>]\s(?P<nick>[^!]+)(![^\s]*)?:\s(?P<comment>.*))$')
    Option('irclogs', 'format.bip.join_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<nick>[^!]+)(![^\s]*)?\shas\sjoined\s.*)$')
    Option('irclogs', 'format.bip.part_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<nick>[^!]+)(![^\s]*)?\shas\sleft\s.*)$')
    Option('irclogs', 'format.bip.quit_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<nick>[^!]+)(![^\s]*)?\shas\squit\s\["?(?P<quitmsg>.*)"?\].*)$')
    Option('irclogs', 'format.bip.nick_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<nick>[^\s]+)\sis\snow\sknown\sas\s(?P<newnick>.*))$')
    Option('irclogs', 'format.bip.topic_regex',   '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<nick>[^!]+)(![^\s]+)?\schanged\stopic\sof\s[^\s]+\sto:\s(?P<topic>.*))$')
    Option('irclogs', 'format.bip.mode_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\smode/[^\s]+\s\[(?P<mode>[^\]]+)\]\sby\s(?P<nick>[^!]+)(!.*)?)$')
    Option('irclogs', 'format.bip.kick_regex',    '^%(timestamp_regex)s\s(?P<message>-!-\s(?P<kicked>[^\s]+)\shas\sbeen\skicked\sby\s(?P<nick>[^!]+)(![^\s]+)?\s\[(?P<kickmsg>[^\]]+)\])$')
    Option('irclogs', 'format.bip.action_regex',  '^%(timestamp_regex)s\s(?P<message>[<>]\s*\s(?P<nick>[^!\s]+)(![^\s]+)?\s(?P<action>.*))$')
    Option('irclogs', 'format.bip.notice_regex',  '%(timestamp_regex)s\s(?P<message>TODO)$')

    # IRCLogsProvider interface
    def get_events_in_range(self, channel_name, start, end):
        """Channel is the config channel name.  start and end are datetimes
        in the users tz.  If the start and end times have different timezones,
        you're fucked."""
        channel = self.channel(channel_name)
        tzname = channel.get('timezone', 'utc')
        try:
            tz = timezone(tzname)
        except UnknownTimeZoneError:
            self.log.warn("input timezone %s not supported, irclogs will be "\
                    "parsed as UTC")
            tzname = 'UTC'
            tz = timezone(tzname)
        dates = self._get_file_dates(start, end, tz)
        filesets = self._get_files(channel, dates)
        # target tz
        # convert to pytz timezone
        try:
            ttz = timezone(start.tzname())
        except UnknownTimeZoneError:
            self.log.warn("timezone %s not supported, irclog output will be "\
                    "%s"%(start.tzname(), tzname))
            ttz = tz


        def _get_lines():
            for fileset in filesets:
                # only existing files
                files = filter(lambda x: os.path.exists(x), fileset)
                if len(files) > 0:
                    files = [file(f) for f in files]
                    parsers = list(
                        [self.parse_lines(f, format=channel, \
                            target_tz=ttz) for f in files])
                    def _key(x):
                        return x.get('timestamp', OLDDATE)
                    for l in merge_iseq(parsers, _key): 
                        yield l
                    [f.close() for f in files]

        for line in _get_lines():
            if line.get('timestamp'):
                if line['timestamp'] >= start and line['timestamp'] < end:
                    yield line
            else:
                yield line
    
    def get_name(self):
        return 'file'
    # end IRCLogsProvider interface
                
    def _get_file_dates(self, start, end, file_tz='utc'):
        """Get files that are within the start-end range, taking into
        account that the file timezone can be different from the start-end
        timezones."""
        if type(file_tz) == str:
            file_tz = timezone(file_tz)
        normal_start = start.astimezone(file_tz)
        file_tz.normalize(normal_start)
        normal_end = end.astimezone(file_tz)
        file_tz.normalize(normal_end)

        # get dates for files
        yield normal_start.date()
        d = normal_start
        oneday = timedelta(days=1)
        while d < normal_end:
            d = d + oneday
            yield d.date()
        if d.day != normal_end.day:
            yield normal_end.date()

    def _get_files(self, channel, dates):
        """Assumes dates are already normalized for the file formats
        timezone. Generator returns a list of files for each date.

        psuedo example:
        
        for fileset in _get_files([1/2, 1/3, 1/4]):
            print "> %s"%(str(fileset))

        > [file-1.2-a.log, file-1.2-b.log]
        > [file-1.3-a.log, file-1.3-b.log]
        > [file-1.4-a.log, file-1.4-b.log]
        """
        basepath = channel['basepath']
        for date in dates:
            filepaths = []
            paths = channel['paths']
            if not isinstance(paths, list):
                paths = list((paths,))
            for path in paths:
                fileformat = os.path.join(basepath, path)
                fileformat = date.strftime(fileformat)
                fileformat = fileformat%({
                    'channel': channel['channel'],
                    'network': channel.get('network'),
                    'channel_name': channel['channel'][1:],
                })
                filepaths.append(fileformat)
                self.log.debug("parsing %s"%(fileformat))
            yield filepaths

    def channel(self, name):
        """ 
        Gets channel by name and replaces format string with format 
        data.
        """
        ch_mgr = IRCChannelManager(self.env)
        # kind of goofy, but we want to use 
        # format for the default values and 
        # we don't know the format until we
        # get the channel.
        ch = ch_mgr.get_channel_by_name(name)
        format = prefix_options('format.%s'%ch['format'], 
                self.config.options('irclogs'))
        ch = ch_mgr.get_channel_by_name(name, format)
        return ch

    def parse_lines(self, lines, format=None, target_tz=None):
        """Parse irc log lines into structured data.  format should
        contain all information about parsing the lines.
          * lines: all irc lines, any generator or list will do
          * format: optional dict, will use default_format() if None
              * match_order:      order of regexes to check for line.
              * *_regex:          the regexes referenced by match_order.
              * timestamp_format: format used by strptime to parse timestamp.
              * timestamp_regex:  regex used to parse timestamp out of line,
                                  this is reference by the optionally included
                                  in the other _regex parameters as 
                                  %(timestamp_regex)s and is seperate as a 
                                  convenience.

          * target_tz: optional target timezone.  This is the timezone of the 
                return data timedate objects.  Will not convert to target_tz 
                if None.
        """
        if not format: 
            format = self.default_format()
        try:
            tz = timezone(format['timezone'])
        except UnknownTimeZoneError:
            self.log.warn("input timezone %s not supported, irclogs will be "\
                "parsed as UTC")
            tz = timezone('utc')

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
            dt = datetime(*t[:6]).replace(tzinfo=tz)
            if target_tz:
                dt = target_tz.normalize(dt.astimezone(target_tz))
            return dt

        for line in lines:
            line = line.rstrip('\r\n')
            if format.get('charset'):
                # we must ignore errors because irc is nuts
                line = unicode(line, format['charset'], errors='ignore')
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

