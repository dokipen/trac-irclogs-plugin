#
# Usage: python <script> <database directory> <directory to index>
# Example: 
#   python update_irc_search.py /tmp/irclogs.idx /var/oforge/irclogs/Channel
#
import sys

def update_irc_search():
    args = sys.argv
    if len(args) < 2:
        print 'Usage: %s <environment path>'%(args[0])
    else:
        from trac.env import Environment
        from irclogs import api
        env = Environment(sys.argv[1])
        chmgr = api.IRCChannelManager(env)
        for indexer in chmgr.indexers:
            indexer.update_index()

