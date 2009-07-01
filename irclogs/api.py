from trac.core import *

class IIRCLogsProvider(Interface):
    """An interface for different sources of irc logs.  DB and file 
    implementations are provided."""

    def get_events_in_range(self, start, end):
        """Yeilds events, in order, within the range, enclusive.

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
            * 



        """


