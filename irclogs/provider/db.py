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

from irclogs.api import IIRCLogsProvider
from irclogs import util

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
        ch = util.get_channel_by_name(self.config, channel_name)
        cnx = self._getdb(ch)
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
                yield {
                    'timestamp': l[1],
                    'network': l[2],
                    'channel': l[3],
                    'nick': l[4],
                    'type': l[5],
                    'message': l[6],
                    'comment': l[6]
                }
            cnx.close()
        except Exception as e:
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
    
