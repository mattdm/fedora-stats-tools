#!/usr/bin/env python

# input: a fedmsg topic which has ['meta']['usernames']
#
# output: a CSV file with fields:
#
# date, users1, users9, users40, usersrest, msgs1, msgs9, msgs40, msgsrest
#
# where and 1, 9, 40, rest correspond to activity from the cohort of 
# users in the top 1%, next 9%, next 40% or rest in that quarter (where
# quarter is a sliding 13-week window) and users is the count of users in
# that cohort that week while msgs is overall work. display the user count
# as a stacked (filled) line graph, and the msgs as a stacked percentage
# chart
#
# todo: create those graphs here in addition to CSV

import utils

import fedmsg.meta
import fedmsg.config
config = fedmsg.config.load_config()
fedmsg.meta.make_processors(**config)



import time
import datetime
import logging
import os
import sys


import collections

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.ERROR)

epoch = datetime.datetime.utcfromtimestamp(0)

discriminant = sys.argv[-1]
if __file__.split('/')[-1] in discriminant:
    print "usage: '$ ./weekly-user-activity.py TOPIC'"
    sys.exit(1)

print "operating with discriminant", discriminant

verboten = [
    'org.fedoraproject.prod.buildsys.rpm.sign',
    'org.fedoraproject.prod.buildsys.repo.init',
    'org.fedoraproject.prod.buildsys.tag',
    'org.fedoraproject.prod.buildsys.untag',
]

try:
    os.makedirs('./data')
except OSError:
    pass

starttime = datetime.datetime.strptime("2012-01-01", "%Y-%m-%d")


WeekActions = collections.namedtuple('WeekActions',['week','useractions'])

# 13 weeks = 1 quarter (rolling)
ring        = collections.deque(maxlen=13)


while starttime < datetime.datetime.now():
    endtime   = starttime + datetime.timedelta(7)
    weekinfo  = WeekActions(starttime, {})

    print "Working on %s / %s" % (discriminant, starttime.strftime("%Y-%m-%d"))

    messages = utils.grep(
        rows_per_page=100,
        meta='usernames',
        start=int((starttime-epoch).total_seconds()),
        end=int((endtime - epoch).total_seconds()),
        order='asc',  # Start at the beginning, end at now.
        topic=discriminant,
        # Cut this stuff out, because its just so spammy.
        not_user=['koschei', 'anonymous'],
        not_topic=verboten,
    )

    users = {}
    for i, msg in enumerate(messages):
        # sanity check
        if msg['topic'] in verboten:
            raise "hell"

        for user in msg['meta']['usernames']:
            if not '@' in user: # some msgs put email for anon users
               weekinfo.useractions[user] = weekinfo.useractions.get(user, 0) + 1

        if i % 50 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()

    print " done reading", starttime.strftime("%Y-%m-%d")
    
    ring.append(weekinfo)

    # okay, so, bear with me here. Comments are for explaining confusing
    # conceptual things in code, right? okay, hold on to your seats.
    # The goal is to write the average for the quarter _around_ this week
    # but since we're doing tihs on the fly rather than reading into the
    # future, this loop tracks the latest with "starttime", but we're actually
    # gonna write lines from 7 weeks earlier, because finally we have the
    # needed info. so, we want the middle week, which is index 6 into the ring
    try:
         ring[6].week.strftime("%Y-%m-%d")
    except IndexError:
        pass
    

    # and loop around
    starttime=endtime
    