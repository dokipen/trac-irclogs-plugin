import heapq
import itertools
import re
from pytz import UnknownTimeZoneError, timezone

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
            * comment : comment, notice
            * action : action
            * kicked : kick
            * mode: mode
            * topic: topic
            * newnick: nick
        """

    def name(self):
        """Returns the name of the provider as used in the configuration.
        ex.
        [irclogs]
        channel.#test2.provider = file
        """

class IIRCLogIndexer(Interface):
    """Object to index logs."""

    def update_index(self):
        """
        Update the index to now.
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

class IRCChannel(object):
    def __init__(self, chmgr, name=None):
        self._chmgr = chmgr
        self._name = name
        c = self._chmgr.config
        if not prefix_options('channel.%s.'%(name), c.options('irclogs')):
            self._name = None

    def settings(self):
        c = self._chmgr.config
        default_op = lambda x: re.match('^[^.]+$', x[0])
        retoptions = dict(filter(default_op, c.options('irclogs')))
        if self.name():
            options= prefix_options(
                    'channel.%s.'%(self.name()), c.options('irclogs'))
            retoptions.update(options)
        return retoptions

    def setting(self, name, default=None):
        return self.settings().get(name, default)

    def events_in_range(self, start, end):
        prov_name = self.provider()
        provider = self._chmgr.provider(prov_name)
        return provider.get_events_in_range(self, start, end)

    def name(self):
        return self._name

    def navbutton(self):
        return self.setting('navbutton', self.channel())

    def menuid(self):
        if self.name():
            mid = self.setting('menuid', "irclogs-%s"%self.name())
        else:
            mid = self.setting('menuid', "irclogs")
        return mid

    def provider(self):
        return self.setting('provider', "file")

    def channel(self):
        return self.setting('channel')

    def network(self):
        return self.setting('network')

    def format(self):
        retval = {}
        config = self._chmgr.config
        default_options = [i for i in config.options('irclogs')] 
        retval.update(default_options)
        dformat_options = prefix_options('format.%s'%self.setting('format'),
                default_options)
        retval.update(dformat_options)
        custom_options= prefix_options(
                'channel.%s.'%(self.name()), config.options('irclogs'))
        retval.update(custom_options)
        return retval

    def perm(self):
        return self.setting('perm', 'IRCLOGS_VIEW')

class IRCChannelManager(Component):
    """
    Get channels.
    """
    providers = ExtensionPoint(IIRCLogsProvider)
    indexers = ExtensionPoint(IIRCLogIndexer)

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

    charset = Option('irclogs', 'charset', 'utf-8',
        doc="""Default charset that logs are retrieved in.""")

    def channels(self):
        """
        Yield all channels
        """
        for chname in self.channel_names():
            yield self.channel(chname)

    def channel_names(self):
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

    def provider(self, name):
        """
        Return the log provider for the channel object.
        """
        for p in self.providers:
            if name == p.name():
                return p
        raise Exception(
                "IRCLogsProvider named %s not found."%(name))

    def channel(self, name):
        """
        Get channel by name.
        """
        return IRCChannel(self, name)

    def to_user_tz(self, req, datetime):
        deftz = self.config.get('trac', 'default_timezone', 'UTC')
        usertz = req.session.get('tz', deftz)
        try:
            utz = timezone(usertz)
        except UnknownTimeZoneError:
            self.log.warn("input timezone %s not supported, irclogs will be "\
                    "parsed as UTC")
            tzname = 'UTC'
            utz = timezone(tzname)
        return utz.normalize(datetime.astimezone(utz))
