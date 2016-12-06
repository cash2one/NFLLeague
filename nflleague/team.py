import nflgame
import nflleague.update
import nflleague.league

import json
import os 
from scipy.misc import imread
import matplotlib.cbook as cbook
import collections

class Team(nflleague.league.League):
    def __init__(self,owner_info,league):
        super(Team,self).__init__(league.league_id,league.season)
        self.owner_info=owner_info 
        self.league=league
        
        self.team_id=int(owner_info.get('team_id'))
        self.team_abv=owner_info.get('team_abv')
        self.team_name=owner_info.get('team_name')
        self.team_div=owner_info.get('team_div')
        self.owner=owner_info.get('team_owner')
        
        self.logo='{}/nflleague/espn-league-json/{}/{}/logos/{}.jpg'.format(os.getcwd(),self.league_id,self.season,self.team_id)
        if not os.path.isfile(self.logo):
            self.logo='{}/nflleague/defaults/default_logo.jpg'.format(os.getcwd())

        self.schedule={}
        for key in league._league_schedule:
            for keykey in league._league_schedule[key]:
                if str(keykey) == str(self.team_id):
                    self.schedule[int(key)]=league._league_schedule[str(key)][str(keykey)]

        self._week_data=json.loads(open('nflleague/espn-league-json/{}/{}/lineup_by_week.json'.format(\
                                                                                    self.league_id,self.season)).read())
        self._weeks={}

    #TODO Add REG and PLAYOFFS, and option to send list (LOW)    
    def weeks(self):
        #Generate entire set of week objects if not already and return list of all weeks played
        if len(self._weeks.keys()) != len(self._week_data.keys()):
            for week in self._week_data[str(self.team_id)]:
                try:
                    self._weeks[int(week)]=nflleague.week.Week(int(week),self.schedule[int(week)],self)
                except KeyError:
                    pass
        self._weeks=collections.OrderedDict(sorted(self._weeks.items()))
        return self._weeks.values()

    def week(self,week):
        #Create specific week object if not already and return 
        if week not in self._weeks.keys():
            self._weeks[int(week)]=nflleague.week.Week(week,self.schedule[int(week)],self)
        return(self._weeks[int(week)])
    
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
       return ' / '.join(['{}: {}'.format(k,v) for k,v in self.owner_info.iteritems()])

