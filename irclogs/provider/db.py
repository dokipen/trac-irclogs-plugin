"""
Parse logs from db into structured data. 
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

ENCODED_FIELDS = ('network', 'channel', 'nick', 'type', 'message', 'comment')

class DBIRCLogProvider(Component):
    """
    Provide logs from irc log table.  
    [irclogs]
    format = gozer
    # or 
    channel.test.channel = #test
    channel.test.provider = db

    The database must contain a table named `chatlog`.  The table definiton 
    should match:
    CREATE TABLE chatlog (
        id      SERIAL PRIMARY KEY,
        time    DATETIME DEFAULT now(),
        network VARCHAR(256) NOT NULL,
        target  VARCHAR(256) NOT NULL,
        nick    VARCHAR(256) NOT NULL,
        type    VARCHAR(256) NOT NULL,
        msg     TEXT NOT NULL
    );

    If using the Gozerbot chatlog plugin, it will create this table 
    automatically in not already present.

    """

    implements(IIRCLogsProvider)

    # IRCLogsProvider interface
    def get_events_in_range(self, ch, start, end):
        global ENCODED_FIELDS

        ch_mgr = IRCChannelManager(self.env)
        self.log.debug(ch.settings())
        def_tzname = self.config.get('irclogs', 'timezone', 'utc')
        tzname = ch.setting('timezone', def_tzname)
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
            self.log.debug("""executing
              SELECT * FROM chatlog 
              WHERE network = %s AND target = %s AND time >= %s AND
                time < %s ORDER BY "time" """)
            self.log.debug("with %s, %s, %s, %s"%(ch.network() or '', ch.channel(), start, end))
            cur = cnx.cursor()
            cur.execute("""
              SELECT * FROM chatlog 
              WHERE network = %s AND target = %s AND time >= %s AND
                time < %s ORDER BY "time" """,(
                  ch.network() or '',
                  ch.channel(),
                  start,
                  end
              )
            )
            ignore_charset = False
            for l in cur:
                timestamp = l[1]
                timestamp = timestamp.replace(tzinfo=tz)
                dt = ttz.normalize(timestamp.astimezone(ttz))
                line = {
                    'timestamp': dt,
                    'network': l[2],
                    'channel': l[3],
                    'nick': l[4],
                    'type': l[5],
                    'message': l[6],
                    'comment': l[6],
                    'action': l[6].lstrip('* ')
                }
                ignore_charset = ignore_charset or isinstance(line['message'],
                                                              unicode)
                if (not ignore_charset) and ch.setting('charset'):
                    for k in ENCODED_FIELDS:
                        line[k] = unicode(line[k], ch.setting('charset'), 
                                          errors='ignore')
                        continue
                yield line
            cnx.close()
        except Exception, e:
            cnx.close()
            self.log.error(e)
            raise e
    
    def name(self):
        return 'db'
    # end IRCLogsProvider interface
    def _getdb(self, channel):
        dbm = IRCLogDatabaseManager(self.env)
        trac_db = self.config.get('trac', 'database')
        irc_db = self.config.get('irclogs', 'database', trac_db)
        chan_db = channel.setting('database', irc_db)
        dbm.set_database(chan_db)
        return dbm.get_connection()
        
                
class IRCLogDatabaseManager(DatabaseManager):
    """ Provide access to chatlog db """

    connection_uri = None

    def set_database(self, database):
        self.connection_uri = database
    
