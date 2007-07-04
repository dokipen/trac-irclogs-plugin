#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 John Hampton <pacopablo@pacopablo.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: John Hampton <pacopablo@pacopablo.com>

from pyndexter import *
from pyndexter.util import TimingFilter, quote

VERSION='0.2'

def index_logs():
    """Run the indexing"""
    framework = Framework('builtin:///var/pacopablo/trac/casa_de_pacopablo/indexes/irclogs.idx?cache=true', stemmer='porter://')
framework.add_source('file://%s?include=*.log' % quote('/home/pacopablo/irc/trac/logs/ChannelLogger/freenode/#trac/'))

framework.update(filter=TimingFilter(progressive=True))

framework.close()



def doArgs():
    """ Look if you can't guess what this function does, just give up now. """
    global VERSION
  
    version = "%%prog %s" % VERSION
    usage ="usage: %prog [options] [site]"
    description="%prog is used to index the irclogs for searching."
  
    parser = OptionParser(usage=usage, version=version, description=description)
  
    parser.add_option("-f", "--file", dest="idxfile", type="string",
                        help="Path to index database file",
                        metavar="<path>")
    parser.add_option("-i", "--include", dest="include", type="string",
                        help="File include filter",
                        metavar="<path>")
    parser.add_option("-t", "--type", dest="idxtype", type="string",
                        help="Type of indexer to use",
                        metavar="<indexer>", default='builtin')
    parser.add_option("", "--nocache", dest="nocache", action="store_true",
                        help="Disable indexer caching",
                        default=False)

    (options, args) = parser.parse_args()

