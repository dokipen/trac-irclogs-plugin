"""
Parse logs from db into structured data. 

TODO: something about defining formats and channels.
"""

# Copyright (c) 2009, Robert Corsaro

import re
from time import strptime, strftime
from datetime import datetime, timedelta
from pytz import timezone, UnknownTimeZoneError

from trac.core import *
from trac.config import Option
from trac.db.api import DatabaseManager

from irclogs.api import IIRCLogsProvider, IRCChannelManager

class DBIRCLogProvider(Component):
    """
    Provide logs from irc log table.  
    [irclogs]
    format = gozer
    # or 
    channel.test.channel = #test
    channel.test.provider = db
    """

    implements(IIRCLogsProvider)

    # IRCLogsProvider interface
    def get_events_in_range(self, channel_name, start, end):
        ch_mgr = IRCChannelManager(self.env)
        ch = ch_mgr.get_channel_by_name(channel_name)
        def_tzname = self.config.get('irclogs', 'timezone', 'utc')
        tzname = ch.get('timezone', def_tzname)
        try:
            tz = timezone(tzname)
        except UnknownTimeZoneError:
            self.log.warn("input timezone %s not supported, irclogs will be "\
                    "parsed as UTC")
            tzname = 'UTC'
            tz = timezone(tzname)
        cnx = self._getdb(ch)
        try:
            ttz = timezone(start.tzname())
        except UnknownTimeZoneError:
            self.log.warn("timezone %s not supported, irclog output will be "\
                    "%s"%(start.tzname(), tzname))
            ttz = tz

        try:
            cur = cnx.cursor()
            cur.execute("""
              SELECT * FROM chatlog 
              WHERE network = %s AND target = %s AND time >= %s AND
                time < %s """,(
                  ch.get('network'),
                  ch.get('channel'),
                  start,
                  end
              )
            )
            for l in cur:
                timestamp = l[1]
                timestamp = timestamp.replace(tzinfo=tz)
                dt = ttz.normalize(timestamp.astimezone(ttz))
                if ch.get('charset'):
                    for i in range(2, len(l)):
                        l[i] = unicode(l[i], ch['charset'])

                yield {
                    'timestamp': dt,
                    'network': l[2],
                    'channel': l[3],
                    'nick': l[4],
                    'type': l[5],
                    'message': l[6],
                    'comment': l[6]
                }
            cnx.close()
        except Exception, e:
            cnx.close()
            self.log.error(e)
            raise e
    
    def get_name(self):
        return 'db'
    # end IRCLogsProvider interface
    def _getdb(self, channel):
        dbm = IRCLogDatabaseManager(self.env)
        trac_db = self.config.get('trac', 'database')
        irc_db = self.config.get('irclogs', 'database', trac_db)
        chan_db = channel.get('database', irc_db)
        dbm.set_database(chan_db)
        return dbm.get_connection()
        
                
class IRCLogDatabaseManager(DatabaseManager):
    """ Provide access to chatlog db """

    connection_uri = None

    def set_database(self, database):
        self.connection_uri = database
    
