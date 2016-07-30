#!/usr/bin/python3
import pandas
import matplotlib.pyplot as plt 
import matplotlib as m
m.rcParams['font.size'] = 12
m.rcParams['font.family'] = 'Overpass'
m.rcParams['legend.frameon'] = False

data=pandas.read_csv("org.fedoraproject.prod.git.receive.bucketed-activity.csv",parse_dates=[0])
data.set_index('weekstart',inplace=True)

graph=data[['users1','users9','users40','userrest']].rename(columns={"users1": "Top 1%","users9":"Top 9%","users40":"Top 40%","userrest":"Remaining 50%"}).plot.area(figsize=(16, 9),
                                                              color=['#579d1c','#ffd320', '#ff420e', '#004586' ],
                                                              grid=True)
#graph.legend(ncol=4)
# totally abusing this.
plt.suptitle("Number of Contributors Making Changes to Packages Each Week",fontsize=24)
graph.set_title("Grouped by Quarterly Activity Level of Each Contributor",fontsize=16)
graph.set_xlabel('')
fig=graph.get_figure()
fig.savefig('git.user.count.svg',dpi=300)

#############################################

data['msgstotal']=data[['msgs1','msgs9','msgs40','msgsrest']].sum(1)
data['msgs1%']=100*data['msgs1']/data['msgstotal']
data['msgs9%']=100*data['msgs9']/data['msgstotal']
data['msgs40%']=100*data['msgs40']/data['msgstotal']
data['msgsrest%']=100*data['msgsrest']/data['msgstotal']




m.rcParams['legend.frameon'] = True
graph=data[['msgs1%','msgs9%','msgs40%','msgsrest%']].rename(columns={"msgs1%": "Top 1%","msgs9%":"Top 9%","msgs40%":"Top 40%","msgsrest%":"Remaining 50%"}).plot.area(figsize=(16, 9),
                                                              color=['#579d1c','#ffd320', '#ff420e', '#004586' ],
                                                              grid=True,ylim=(0,100))
plt.suptitle("Percent of Package Changes Each Week From Each Activiy Level Group",fontsize=24)
graph.set_title("",fontsize=16)
graph.set_xlabel('')

fig=graph.get_figure()
fig.savefig('git.activity.share.svg',dpi=300)
