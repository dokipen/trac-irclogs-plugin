# -*- coding: utf-8 -*-
import os
import re
import calendar
import pytz
import time

from time import strptime
from trac.util.datefmt import localtz
from datetime import datetime
from calendar import month_name

from trac.core import *
from trac.perm import IPermissionRequestor
from trac.config import Option, ListOption
from trac.web.chrome import INavigationContributor, ITemplateProvider, \
                            add_stylesheet, add_script
from trac.web.main import IRequestHandler
from trac.util.html import escape, html, Markup
from trac.util.datefmt import utc

from genshi.builder import tag
from irclogs.api import *

def generate_nojs_calendar(req, context, entries):
    weeks = []
    for week in calendar.monthcalendar(context['year'], context['month']):
        w = []
        for day in week:
            if day:
                w.append({
                    'caption':  day,
                    'href':     req.href('irclogs', context['channel'],
                                         context['year'],
                                         '%02d' % context['month'], 
                                         '%02d' % day),
                    # today is the selected day, not today..yuk
                    'today':    day == context['day'],
                    'has_log':  True
                })
            else:
                w.append({
                    'empty':    True
                })
        weeks.append(w)

    next_month_year = context['year']
    next_month = context['month'] + 1
    if next_month > 12:
        next_month_year += 1
        next_month = 1
    if context['day'] > -1:
        next_month_href = req.href('irclogs', context['channel'], 
                next_month_year, '%02d' % next_month, '%02d' % context['day'])
    else:
        next_month_href = req.href('irclogs', context['channel'],
                next_month_year, '%02d' % next_month)

    prev_month_year = context['year']
    prev_month = context['month'] - 1
    if prev_month < 1:
        prev_month_year -= 1
        prev_month = 12
    if context['day'] > -1:
        prev_month_href = req.href('irclogs', context['channel'], 
                prev_month_year, '%02d' % prev_month, '%02d' % context['day'])
    else:
        prev_month_href = req.href('irclogs', context['channel'],
                prev_month_year, '%02d' % prev_month)

    return {
        'weeks':        weeks,
        'year':         {
            'caption':      context['year'],
            'href':         req.href('irclogs', context['channel'], context['year'])
        },
        'month':        {
            'caption':      context['month_name'],
            'href':         req.href('irclogs', context['channel'], context['year'], 
                '%02d' % context['month'])
        },
        'next_year':    {
            'caption':      str(context['year'] + 1),
            'href':         req.href('irclogs', context['channel'], context['year'] + 1)
        },
        'prev_year':    {
            'caption':      str(context['year'] - 1),
            'href':         req.href('irclogs', context['channel'], context['year'] - 1)
        },
        'next_month':   {
            'caption':      '%02d' % next_month,
            'href':         next_month_href
        },
        'prev_month':   {
            'caption':      '%02d' % prev_month,
            'href':         prev_month_href
        },
    }

