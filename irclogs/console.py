#
# Usage: python <script> <database directory> <directory to index>
# Example: 
#   python update_irc_search.py /tmp/irclogs.idx /var/oforge/irclogs/Channel
#

import os
import sys
import shutil
from pyndexter import Framework, READWRITE
from pyndexter.util import quote


def update_irc_search():
    args = sys.argv
    
    index_path = args[1]
    log_path = args[2]
    
    files = os.listdir(args[2])
    
    for file in files:
        try:
            if os.path.isdir("%s/%s.idx" % (index_path, file)):
                output = shutil.rmtree("%s/%s.idx" % (index_path, file))
            framework = Framework('builtin://%s/%s.idx' % 
                                  (quote(index_path), quote(file)), mode=READWRITE)
            framework.add_source('file://%s/%s' % (quote(log_path), quote(file)))
            framework.update()
            framework.close()
        except Exception, e:
            code, message = e
            print 'Error %s: %s' % (code, message)
