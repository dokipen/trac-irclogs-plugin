import heapq
import itertools
import re

from trac.core import *
from trac.config import Option

class IIRCLogsProvider(Interface):
    """An interface for different sources of irc logs.  DB and file 
    implementations are provided."""

    def get_events_in_range(self, channel_name, start, end):
        """Yeilds events, in order, within the range, enclusive.  Channel is 
        the channel name in config, and not the actual channel name.

          {
              'time': timestamp,
              'type': string,
              'message': string,
              .. type specific entries ..
          }

          type is (comment|action|join|part|quit|kick|mode|topic|nick|server|other).
          addtional parameters with their associated types:
            * nick : comment,action,join,part,quit,kick,mode,topic,nick
            * comment : comment
            * action : action
            * kicked : kick



        """

    def get_name(self):
        """Returns the name of the provider as used in the configuration.
        ex.
        [irclogs]
        channel.#test2.provider = file
        """


def merge_iseq(iterables, key):
    # key values so we can decide what to sort by
    def keyed(v):
        return key(v), v
    iterables = map(lambda x: itertools.imap(keyed, x), iterables)
    """
    This is commented out because it only works on 2.6.  Trying for 2.4
      compatibility like trac.
    ""Thanks kniht!  Wrapper for heapq.merge that allows specifying a key.
    http://bitbucket.org/kniht/scraps/src/tip/python/merge_iseq.py
    ""
    for item in heapq.merge(*iterables):
        yield item[1]
    """
    # start 2.4 hackathon taken from
    # http://code.activestate.com/recipes/491285/
    heappop, siftup, _StopIteration = heapq.heappop, heapq._siftup, StopIteration

    h = []
    h_append = h.append
    for it in map(iter, iterables):
        try:
            next = it.next
            h_append([next(), next])
        except _StopIteration:
            pass
    heapq.heapify(h)

    while(1):
        try:
            while 1:
                v, next = s = h[0] # raises IndexError when h is empty
                yield v[1]         # this is a little different since we keyed
                                   #   the values
                s[0] = next()      # raises StopIteration when exhausted
                siftup(h, 0)       # restore heap condition
        except _StopIteration:
            heappop(h)              # remove empty iter
        except IndexError:
            return

def prefix_options(prefix, options):
    """Helper method to get options out of the config object.  Gets all
    options that start with prefix, and also removes prefix portion."""
    if not prefix.endswith('.'):
        prefix = "%s."%(prefix)

    # pair[0] is the  name and pair[1] is the value
    _filter = lambda pair: pair[0].startswith(prefix)
    _map = lambda pair: (re.sub('^%s'%(prefix), '', pair[0]), pair[1])
    return dict(map(_map, filter(_filter, options)))

class IRCChannelManager(Component):
    """
    Get channels.
    """
    providers = ExtensionPoint(IIRCLogsProvider)

    channel_re = re.compile('^channel\.(?P<channel>[^.]+)\.channel$')

    channel = Option('irclogs', 'channel', 
            doc="""Default channel.  Can be overriden by channel""")

    network = Option('irclogs', 'network', 
            doc="""Default network.  Can be overriden by channel""")

    timezone = Option('irclogs', 'timezone', 'utc',
        doc="""Default timezone that irc is logged in.  This is needed
        so we can convert the incoming date to the date in the irc
        log.  This can be overridden by the file format.
        """)

    def get_channel_names(self):
        """
        Yield all channel names.  None means that there is a default 
        channel.
        """
        CHANNEL_RE = re.compile('^channel\.(?P<name>[^.]+)\..*$')
        def _name(x):
            m = CHANNEL_RE.match(x)
            if m:
                return m.groupdict()['name']
            else:
                None
        ops = self.config.options('irclogs')
        # set makes uniq
        for c in filter(None, set(map(_name, map(lambda x: x[0], ops)))):
            yield c
        if self.config.get('irclogs', 'channel'):
            yield None

    def get_provider(self, channel):
        """
        Return the log provider for the channel object.
        """
        name = channel['name']
        prov_name = self.config.get('irclogs', 'channel.%s.provider'%(name))
        if not prov_name:
            prov_name = self.config.get('irclogs', 'provider', 'file')
        for p in self.providers:
            if prov_name == p.get_name():
                return p
        raise Exception(
                "%s IRCLogsProvider for channel %s not found."%(name, channel))

    def get_channel_by_name(self, name):
        """
        Get channel data by name.
        
        ex.
        {
          'channel': '#mychannel',
          'format': 'supy',
          'network': 'Freenode',
          'provider': 'file',
          'name': 'test'  # None for default
        }

        Network is usually none, but could be used with an irclogger that logs
        on to multi-networks.  It is only used as a positional parameter in 
        format.paths or the networks column for db backend.
        """
        c = self.config
        retoptions = {
            'channel': c.get('irclogs', 'channel'),
            'network': c.get('irclogs', 'network'),
            'provider': c.get('irclogs', 'provider'),
            'name': name,
        }
        if name:
            options= prefix_options('channel.%s.'%(name), c.options('irclogs'))
            if not options:
                retoptions['name'] = None
            retoptions.update(options)
        if not retoptions.get('navbutton'):
            retoptions['navbutton'] = retoptions['channel']
        if name:
            retoptions['menuid'] = 'irclogs-%s'%name
        else:
            retoptions['menuid'] = 'irclogs'
        return retoptions

    def get_channel_by_channel(self, channel):
        c = self.config
        ops = c.options('irclogs')
        vals = filter(lambda x: (channel_re.match(x[0]) \
                and x[1] == channel), ops)
        if not vals:
            if c.get('irclogs', 'channel') == channel:
                return get_channel_by_name(None)
            raise Exception('channel %s not found'%(channel))
        default_channel = get_channel_by_name(None)
        if len(vals) > 1 or vals[0][1] == default_channel['channel']:
            raise Exception('multiple channels match %s'%(channel))
        m = channel_re.match(vals[0][0])
        return get_channel_by_name(m.group('channel'))
