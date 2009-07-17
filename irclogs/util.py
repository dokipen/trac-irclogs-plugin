import heapq
import itertools
import re

def merge_iseq(iterables, key):
    """Thanks kniht!  Wrapper for heapq.merge that allows specifying a key.
    http://bitbucket.org/kniht/scraps/src/tip/python/merge_iseq.py
    """
    def keyed(v):
        return key(v), v
    iterables = map(lambda x: itertools.imap(keyed, x), iterables)
    for item in heapq.merge(*iterables):
        yield item[1]

def get_prefix_options(prefix, c):
    """Helper method to get options out of the config object.  Gets all
    options that start with prefix, and also removes prefix portion."""
    if not prefix.endswith('.'):
        prefix = "%s."%(prefix)
    options = c.options('irclogs')

    # pair[0] is the  name and pair[1] is the value
    _filter = lambda pair: pair[0].startswith(prefix)
    _map = lambda pair: (re.sub('^%s'%(prefix), '', pair[0]), pair[1])
    return dict(map(_map, filter(_filter, options)))

def get_channel_by_name(c, name):
    retoptions = {
        'channel': c.get('irclogs', 'channel'),
        'network': c.get('irclogs', 'network'),
        'provider': c.get('irclogs', 'provider'),
        'name': name,
    }
    if name:
        options = get_prefix_options('channel.%s.'%(name), c)
        if not options:
            retoptions['name'] = None
        retoptions.update(options)
    return retoptions

channel_re = re.compile('^channel\.(?P<channel>[^.]+)\.channel$')
def get_channel_by_channel(c, channel):
    ops = c.options('irclogs')
    vals = filter(lambda x: (channel_re.match(x[0]) and x[1] == channel), ops)
    if not vals:
        if c.get('irclogs', 'channel') == channel:
            return get_channel_by_name(c, None)
        raise Exception('channel %s not found'%(channel))
    default_channel = get_channel_by_name(c, None)
    if len(vals) > 1 or vals[0][1] == default_channel['channel']:
        raise Exception('multiple channels match %s'%(channel))
    m = channel_re.match(vals[0][0])
    return get_channel_by_name(c, m.group('channel'))

