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
from pytz import timezone
import os.path
import itertools
import operator
import heapq

from trac.core import *
from trac.config import Option, ListOption

from irclogs.api import IIRCLogsProvider

# this is used for comparison only, and never included in yielded
# values
OLDDATE = datetime(1977,8,3,0,0,0,tzinfo=timezone('utc'))

def merge_iseq(iterables, key=operator.lt):
    """Thanks kniht!  Wrapper for heapq.merge that allows specifying a key.
    http://bitbucket.org/kniht/scraps/src/tip/python/merge_iseq.py
    """
    def keyed(v):
        return key(v), v
    iterables = map(lambda x: itertools.imap(keyed, x), iterables)
    for item in heapq.merge(*iterables):
        yield item[1]

class FileIRCLogProvider(Component):
    """Provide logs from irc log files.  All default regex config parameters
    match the default Supybot log files, where defaults are provided.
    """

    implements(IIRCLogsProvider)

    # not to be confused with default_format(), which doesn't consider
    # a named format.
    format = Option('irclogs', 'format', 'supy', 
            doc="The name of the default format to use.")

    network = Option('irclogs', 'network', 
            doc="""Default network.
            This is only used as a replacement var in the path option.
            """)

    timezone = Option('irclogs', 'timezone', 'utc',
        doc="""Default timezone that the files are logged in.  This is needed
        so we can convert the incoming date to the date in the irc
        log file names.  And find all files in the range. This can be 
        overridden by the format.
        """)

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

    Option('irclogs', 'format.gozer.basepath', '/home/gozerbot/.gozerbot/')
    ListOption('irclogs', 'format.gozer.paths', 
            ['logs/simple/%(channel)s.%Y%m%d.slog', 
                'logs/simple/%(channel_name)s.%Y%m%d.slog'])
    Option('irclogs', 'format.gozer.timestamp_format', '%Y-%m-%d %H:%M:%S')

    def _get_prefix_options(self, prefix):
        """Helper method to get options out of the config object.  Gets all
        options that start with prefix, and also removes prefix portion."""
        if not prefix.endswith('.'):
            prefix = "%s."%(prefix)
        options = self.config.options('irclogs')

        # pair[0] is the  name and pair[1] is the value
        _filter = lambda pair: pair[0].startswith(prefix)
        _map = lambda pair: (re.sub('^%s'%(prefix), '', pair[0]), pair[1])
        return dict(map(_map, filter(_filter, options)))

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
        basepath = channel['format']['basepath']
        for date in dates:
            filepaths = []
            for path in channel['format']['paths']:
                fileformat = os.path.join(basepath, path)
                fileformat = date.strftime(fileformat)
                fileformat = fileformat%({
                    'channel': channel['channel'],
                    'network': channel.get('network'),
                    'channel_name': channel['channel'][1:],
                })
                self.log.error(fileformat)
                filepaths.append(fileformat)
            yield filepaths

    def get_events_in_range(self, channel_name, start, end):
        """Channel is the config channel name.  start and end are datetimes
        in the users tz.  If the start and end times have different timezones,
        you're fucked."""
        self.log.error(channel_name)
        channel = self.channel(channel_name)
        self.log.error(channel)
        tz = timezone(channel['format'].get('timezone', 'utc'))
        dates = self._get_file_dates(start, end, tz)
        filesets = self._get_files(channel, dates)
        # target tz
        # convert to pytz timezone
        ttz = timezone(start.tzname())

        def _get_lines():
            for fileset in filesets:
                # only existing files
                files = filter(lambda x: os.path.exists(x), fileset)
                if len(files) > 0:
                    files = [file(f) for f in files]
                    parsers = list(
                            [self.parse_lines(f, format=channel['format'], tz=tz, target_tz=ttz) for f in files])
                    def _key(x):
                        print x
                        return x.get('timestamp', OLDDATE)
                    for l in merge_iseq(parsers, key=_key): #(lambda x: x['timestamp'])):
                        yield l
                    [f.close() for f in files]

        for line in _get_lines():
            if line['timestamp']:
                if line['timestamp'] > start or line['timestamp'] < end:
                    yield line
                
    def channel(self, name):
        """Get channel data by name.
        
        ex.
        {
          'channel': '#mychannel',
          'format': {
            'basepath': '/var/logs/irclogs',
            'paths': ['%(network)s/%(channel)s-%Y%m%d.log', '%(network)s/%(channel)s-%Y%m%d.slog'],
            'match_order': ('message', 'action', 'topic'),
            'timestamp_regex': '^(?P<timestamp>blahblah)',
            'message_regex': '^%(timestamp_regex) (?P<message>blahblah)$',
            'action_regex': '^%(timestamp_regex) * (?P<message>blahblah)',
            etc...
          },
          'network': 'Freenode'
        }

        Network is usually none, but could be used with an irclogger that logs
        on to multi-networks.  It is only used as a positional parameter in 
        format.paths.
        """
        default = {'format': self.format, 'network': self.network}

        # we only want options for this channel
        options = self._get_prefix_options('channel.%s'%(name))
        default.update(options)
        default['format'] = self.format(default['format'])
        return default

    def default_format(self):
        """All default format options.  A potential bug is if the default
        format match_order doesn't include a $name_regex, but a custom 
        format does, and the $name_regex is specified in the defaults.  In 
        this case it would never be read."""
        format = {
                'basepath': self.basepath,
                'paths': self.paths,
                'match_order': self.match_order,
                'timestamp_format': self.timestamp_format,
                'timestamp_regex': self.timestamp_regex,
                'timezone': self.timezone,
        }
        # grab the match order, and then all the assoc. regexs
        match_order = re.split('[,|: ]+', format['match_order'])
        for mtype in match_order:
            regex_name = "%s_regex"%(mtype) 
            format[regex_name] = self.__getattribute__(regex_name)
        return format

    def format(self, name):
        """Named formats override default options.  Default options are 
        declared in the config file on the first level.

        [irclogs]
        basepath = /var/irclogs/
        timestamp_regex = 'blah'

        format options are prefixed with 'format.$name.'.

        [irclogs]
        format.gozer.basepath = /home/gozerbot/.gozerbot/logs/trac/
        format.gozer.timestamp_regex = 'otherblah'

        This method will return all options for a named format."""
        format_options = self._get_prefix_options('format.%s'%(name))
        ret_format = self.default_format()
        ret_format.update(format_options)
        return ret_format

    def parse_lines(self, lines, format=None, tz=None, target_tz=None):
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

          * tz: optional timezone of logfile timestamps.  Will use 
                self.timezone if None.
          * target_tz: optional target timezone.  This is the timezone of the 
                return data timedate objects.  Will not convert to target_tz 
                if None.
        """
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
            dt = datetime(*t[:6]).replace(tzinfo=tz)
            if target_tz:
                dt = target_tz.normalize(dt.astimezone(target_tz))
            return dt

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

