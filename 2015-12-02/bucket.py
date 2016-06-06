#!/usr/bin/python
import csv
import sys
import datetime
from collections import defaultdict


# 2012-01-01 (the magic number for this dataset
starttime=datetime.datetime.fromtimestamp(1325394000)


# awesomely munge the date out of the filename
filename = sys.argv[1]
daynum=int(filename[:5])
# convert to an actual date
filedate = starttime + datetime.timedelta(daynum*7)

# we're gonna consider the quarter as 13 weeks -- 6 before
# and 6 after. this steps through the "neighbor" files. whoo!
usertotals = defaultdict(int)
for w in xrange(-6,7):
    f=("%04d" % (daynum+w))  + ".csv"
    try:
       with open(f, 'rb') as csvfile:
          reader = csv.reader(csvfile)
          for row in reader:    
             username=row[0]
             thisweek=row[1]
             usertotals[username] += int(thisweek)
    except IOError:
        pass
                  
#lump everyone into buckets by rank        
userrank = {}
userbucket = {}
i=len(usertotals)+1
for n in sorted(usertotals,key=usertotals.get):
   userrank[n]=i
   i-=1
   if i<len(usertotals)*0.01: # top 1%
      userbucket[n]=1
   elif i<len(usertotals)*0.10: # next 9% (otherwise top 10%)
      userbucket[n]=2
   elif i<len(usertotals)*0.50: # next 40%
      userbucket[n]=3
   else:                        # the bottom half
      userbucket[n]=4           
        

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


with open(filename, 'rb') as csvfile:
    reader=csv.reader(csvfile)
    for row in reader:
        username=row[0]
        thisweek=row[1]
        bucketscores[userbucket[username]] +=  int(thisweek)
        bucketcount[userbucket[username]]  +=  1
        


print "%s,%d,%d,%d,%d,%d,%d,%d,%d" % (filedate.strftime('%Y-%m-%d'), bucketscores[1], bucketscores[2], bucketscores[3], bucketscores[4], bucketcount[1], bucketcount[2], bucketcount[3], bucketcount[4] )
