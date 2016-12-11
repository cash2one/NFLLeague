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

class FantasyTeam(object):
    def __init__(self,league_id,season,team_id):
        self.league_id=league_id
        self.season=season
        self.team_id=team_id
        owner_info=nflleague.league._json_load_owners(self.league_id,self.season).get(str(self.team_id),{})

        self.team_abv=owner_info.get('team_abv')
        self.team_name=owner_info.get('team_name')
        self.team_div=owner_info.get('team_div')
        self.owner=owner_info.get('team_owner')

        self.schedule={}
        json_sched=nflleague.league._json_load_schedule(self.league_id,self.season)
        for week,sched in json_sched.iteritems():
            self.schedule[str(week)]=sched.get(str(self.team_id),{})

        self.logo=_load_logo(self.league_id,self.season,self.team_id)
        self._weeks={}
         
    #TODO Add REG and PLAYOFFS, and option to send list (LOW)    
    def weeks(self):
        #Generate entire set of week objects if not already and return list of all weeks played
        if self._weeks=={}:
            for week,sched in self.schedule.iteritems():
                self._weeks[week]=nflleague.week.Week(week,self)
        self._weeks=collections.OrderedDict(sorted(self._weeks.items()))
        return self._weeks.values()
        
    def week(self,week):
        #Create specific week object if not already and return 
        if str(week) not in self._weeks.keys():
            self._weeks[str(week)]=nflleague.week.Week(week,self)
        return(self._weeks[str(week)])

    def __str__(self):
        return '{} ({})'.format(self.team_name,self.team_abv)

class Team(FantasyTeam):
    #def __init__(self,owner_info,league):
    #    super(Team,self).__init__(league.league_id,league.season)
    #    self.league=league
    def __init__(self,team_id,league):
        super(Team,self).__init__(league.league_id,league.season,team_id)
        #pass all league vars, but avoid passing previously inited Team objects to new Team object
        for k,v in league.__dict__.iteritems():
            #if k!='_teams':
            self.__dict__[k]=v
    
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

