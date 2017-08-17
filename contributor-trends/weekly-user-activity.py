#!/usr/bin/env python

# input: a fedmsg topic which has ['meta']['usernames']
#
# output: a CSV file with fields:
#
# date, msgs1, msgs9, msgs40, msgsrest, users1, users9, users40, userrest, newusers, actionsnew, actionsmonth, actionsyear, actionsolder, newspammers, spamactions, botactions, relengactions
#
# where and 1, 9, 40, rest correspond to activity from the cohort of 
# users in the top 1%, next 9%, next 40% or rest in that quarter (where
# quarter is a sliding 13-week window) and users is the count of users in
# that cohort that week while msgs is overall work. display the user count
# as a stacked (filled) line graph, and the msgs as a stacked percentage
# chart
#
# spam actions is the count of actions performed that week by accounts
# tagged (at the _current_ time) as malicious accounts
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

import string
import re

import collections
#import pprint

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.ERROR)

spammers = [line.rstrip('\n') for line in open('badpeople.list')]
bots     = [line.rstrip('\n') for line in open('bots.list')]

epoch = datetime.datetime.utcfromtimestamp(0)

discriminant = sys.argv[-1]
if __file__.split('/')[-1] in discriminant:
    print "usage: '$ ./weekly-user-activity.py TOPIC'"
    sys.exit(1)
    
if not re.match("^[a-z\.]*$", discriminant):
    print "bad discriminant"
    sys.exit(2)


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



WeekActions = collections.namedtuple('WeekActions',['week','useractions','newusers','actionsbyage','nonhuman'])

yeartotals={}
yearweeks={}
firstseen={}
lastseen={}

# 13 weeks = 1 quarter (rolling)
ring        = collections.deque(maxlen=13)

with open('data/%s.bucketed-activity.csv' % (discriminant), 'w') as f:
    f.write("weekstart,msgs1,msgs9,msgs40,msgsrest,users1,users9,users40,userrest,newusercount,newuseractions,monthuseractions,yearuseractions,olderuseractions,newspammers,spamactions,botactions,relengactions\n")
    f.flush()
    while starttime < datetime.datetime.now() + datetime.timedelta(42): # weeks in the future because see below
        endtime   = starttime + datetime.timedelta(7)
        weekinfo  = WeekActions(starttime, collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter())
        if not starttime.strftime("%Y") in yeartotals:
            yeartotals[starttime.strftime("%Y")]=collections.Counter()
        if not starttime.strftime("%Y") in yearweeks:
            yearweeks[starttime.strftime("%Y")]=collections.Counter()

        print "Working on %s / %s" % (discriminant, starttime.strftime("%Y-%m-%d")),

        for attempt in range(10):
            try:
                messages = utils.grep(
                    rows_per_page=100,
                    meta='usernames',
                    start=int((starttime-epoch).total_seconds()),
                    end=int((endtime - epoch).total_seconds()),
                    order='asc',  # Start at the beginning, end at now.
                    topic=discriminant,
                    # Cut this stuff out, because its just so spammy.
                    not_user=['anonymous','koschei'],
                    not_topic=verboten,
                )
            except IOError:
                print "Retrying."
                time.sleep(5)
            else:
                break
        else:
            raise "too much timeout"

        for i, msg in enumerate(messages):
            # sanity check
            if msg['topic'] in verboten:
                raise "hell"

            for user in msg['meta']['usernames']:
               if user == 'releng':
                   weekinfo.nonhuman['relengactions'] +=1
                   continue
               if user in bots:
                   weekinfo.nonhuman['botactions'] +=1
                   continue
               if user in spammers:
                   weekinfo.nonhuman['spamactions'] +=1
                   if not user in firstseen:
                       firstseen[user]=starttime # todo: make this actual first time, not first week
                       weekinfo.nonhuman['newspammers'] +=1
                   continue
               if '@' in user:
                   # some msgs put email for anon users
                   continue
                
               weekinfo.useractions[user] += 1
               yeartotals[starttime.strftime("%Y")][user] += 1
               
               if not user in firstseen:
                   firstseen[user]=starttime # todo: make this actual first time, not first week
                   weekinfo.newusers['count'] += 1
                   
               if (starttime - firstseen[user]).days < 7:
                   weekinfo.actionsbyage['new'] += 1
               elif (starttime - firstseen[user]).days < 31:
                   weekinfo.actionsbyage['month'] += 1
               elif (starttime - firstseen[user]).days < 365:
                   weekinfo.actionsbyage['year'] += 1
               else:
                   weekinfo.actionsbyage['older'] += 1
               
               lastseen[user]=starttime

            
            if i % 50 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()            
         
        print       
        #pprint.pprint(dict(weekinfo.useractions))
        yearweeks[starttime.strftime("%Y")] += collections.Counter(list(weekinfo.useractions))
        ring.append(weekinfo)
        
         

        # okay, so, bear with me here. Comments are for explaining confusing
        # conceptual things in code, right? okay, hold on to your seats.
        # The goal is to write the average for the quarter _around_ each week
        # but since we're doing tihs on the fly rather than reading into the
        # future, this loop tracks the latest with "starttime", but we're actually
        # gonna write lines from 6 weeks earlier, because finally we have the
        # needed info. so, we jump back 6 weeks (42 days) from starttime.
        # this is the same as jumping back 7 elements in the deque (if it's that deep)
        
        if len(ring)>6: 

            # first, we're bucketing all the users by percent of activity
            usertotals=collections.Counter()
            for week in ring:
                usertotals += week.useractions
            userrank = {}
            userbucket = {}
            i=len(usertotals)+1
            for name in sorted(usertotals,key=usertotals.get):
               userrank[name]=i
               i-=1
               if i<len(usertotals)*0.01: # top 1%
                  userbucket[name]=1
               elif i<len(usertotals)*0.10: # next 9% (otherwise top 10%)
                  userbucket[name]=2
               elif i<len(usertotals)*0.50: # next 40%
                  userbucket[name]=3
               else:                        # the bottom half
                  userbucket[name]=4           

            workweek=ring[len(ring)-7] # jump back same amount into the deque

            bucketscores = {}
            bucketscores[1]=0
            bucketscores[2]=0
            bucketscores[3]=0
            bucketscores[4]=0
            bucketcount = {}
            bucketcount[1]=0
            bucketcount[2]=0
            bucketcount[3]=0
            bucketcount[4]=0

            for username in workweek.useractions.keys():
                bucketscores[userbucket[username]] +=  workweek.useractions[username]
                bucketcount[userbucket[username]]  +=  1
              
            print "%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d" % (workweek.week.strftime('%Y-%m-%d'), bucketscores[1], bucketscores[2], bucketscores[3], bucketscores[4], bucketcount[1], bucketcount[2], bucketcount[3], bucketcount[4],workweek.newusers['count'],workweek.actionsbyage['new'],workweek.actionsbyage['month'],workweek.actionsbyage['year'],workweek.actionsbyage['older'],workweek.nonhuman['newspammers,'],workweek.nonhuman['spamactions,'], workweek.nonhuman['botactions'], workweek.nonhuman['relengactions'])

            if any((bucketscores[1], bucketscores[2], bucketscores[3], bucketscores[4])):
                f.write("%s,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n" % (workweek.week.strftime('%Y-%m-%d'), bucketscores[1], bucketscores[2], bucketscores[3], bucketscores[4], bucketcount[1], bucketcount[2], bucketcount[3], bucketcount[4],workweek.newusers['count'],workweek.actionsbyage['new'],workweek.actionsbyage['month'],workweek.actionsbyage['year'],workweek.actionsbyage['older'],workweek.nonhuman['newspammers,'],workweek.nonhuman['spamactions,'], workweek.nonhuman['botactions'], workweek.nonhuman['relengactions']))
                f.flush()

        # and loop around
        starttime=endtime

for year in yeartotals.keys():
    with open('data/%s.userdata.%s.csv' % (discriminant,year), 'w') as f:
        f.write("%s,%s,%s,%s,%s\n" % ("user","actions","weeks","firstseen","lastseen"))
        for user in sorted(yeartotals[year], key=yeartotals[year].get, reverse=True):
            f.write("%s,%s,%s,%s,%s\n" % (user,yeartotals[year][user],yearweeks[year][user],firstseen[user].strftime('%Y-%m-%d'),lastseen[user].strftime('%Y-%m-%d')))
            