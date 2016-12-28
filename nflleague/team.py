import nflgame
import nflleague.update
import nflleague.league

import json
import os 
from scipy.misc import imread
import matplotlib.cbook as cbook
import collections

def _load_logo(league_id,season,team_id):
    logo_fp='{}/nflleague/espn-league-json/{}/{}/logos/{}.jpg'.format(os.getcwd(),league_id,season,team_id)
    if not os.path.isfile(logo_fp):
        logo_fp='{}/nflleague/defaults/default_logo.jpg'.format(os.getcwd())
    return logo_fp

         
class Team(object):
    def __init__(self,team_id,league):
        #pass all league vars, but avoid passing previously inited Team objects to new Team object
        for k,v in league.__dict__.iteritems():
            self.__dict__[k]=v
        self.team_id=nflleague.standard_team_id(self.league_id,self.season,team_id)
        self.team_abv=self.owner_info.get(self.team_id,{}).get('team_abv','')
        self.team_name=self.owner_info.get(self.team_id,{}).get('team_name','')
        self.team_div=self.owner_info.get(self.team_id,{}).get('team_div','')
        self.owner=self.owner_info.get(self.team_id,{}).get('team_owner','')
        temp={}
        for week,sched in self._schedule.iteritems():
            temp[str(week)]=sched.get(self.team_id,{})
        self.schedule=temp
        
        self.logo=_load_logo(self.league_id,self.season,self.team_id)
        #self._weeks={}

    #TODO Add REG and PLAYOFFS, and option to send list (LOW)    
    def weeks(self):
        #Generate entire set of week objects if not already and return list of all weeks played
        """
        for week,sched in self.schedule.iteritems():
            if int(week)<=int(nflleague.c_week) and str(week) not in map(str,self._weeks):
                self._weeks[week]=nflleague.week.Week(week,self)
        self._weeks=collections.OrderedDict(sorted(self._weeks.items(),key=lambda x:int(x[0])))
        print(self._weeks)
        return self._weeks.values()
        """
        wks=[]
        for week,sched in self.schedule.iteritems():
            if int(week)<=int(nflleague.c_week):
                wks.append(nflleague.week.Week(week,self))
        return sorted(wks,key=lambda x:int(x.week))
    
    def week(self,week):
        #Create specific week object if not already and return 
        return nflleague.week.Week(week,self)
        """    
        if str(week) not in self._weeks.keys():
            self._weeks[str(week)]=nflleague.week.Week(week,self)
        return(self._weeks[str(week)])
        """
    def record(self):
        #Takes insane amount of time to calculate. Cache
        #Update 10-01: With rebuild of players.json time is greatly reduced.  Still not optimized
        record= {'W':0,'L':0,'T':0}
        #TEMP FIX
        for week in self.weeks()[:-1]:
            if week.win():
                record['W']+=1
            elif not week.win():
                record['L']+=1
            else:
                record['T']+=1
        return record
    
    def __str__(self):
        return '{} ({})'.format(self.team_name,self.team_abv)

class FantasyTeam(Team):
    def __init__(self,league_id,season,team_id):
        super(FantasyTeam,self).__init__(team_id,nflleague.league.League(league_id,season))
