#!/usr/bin/env python

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
    os.makedirs('./data/%s' % discriminant)
except OSError:
    pass

starttime = datetime.datetime.strptime("2012-01-01", "%Y-%m-%d")

while starttime < datetime.datetime.now():
    endtime   = starttime + datetime.timedelta(7)

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
            users[user] = users.get(user, 0) + 1

        if i % 50 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()

    print " done reading", starttime.strftime("%Y-%m-%d")

    for user in users:
        print 'User: %20s  Actions: %4i' % (user, users[user])

    # and loop around
    starttime=endtime
    