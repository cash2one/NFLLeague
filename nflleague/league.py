import nflleague
from nflleague.functions import get_json
import nflleague.team
import nflleague.schedule
import nflgame
import json
import numpy as np
from collections import defaultdict,OrderedDict
from copy import deepcopy
#TODO cache expensive functions which return weekly constants such as record, score etc..
#TODO change heirarchy to league>SEASON>team>week>player>stats 
#       >> LEAGUE=nflleague.league.League(league_id)
#       >> LEAGUE.season(2015)+LEAGUE.season(2016) #for combine stats
#       >> LEAUGE.season(2016).teams()
#       >> LEAGUE.season(2010).team('CHAD MORTON').week(5).lineup.get('TE')
#   Would make interface more intuitive and eliminate need for confusing 'Seasons' dictionary with different league objects
#   Might take much longer to initialize Leauge Objet.  Could avoid, though

class League(object):
    def __init__(self,league_id,season):
        self.season=int(season)
        self.league_id=int(league_id)
        self.team_ids=_json_load_owners(self.league_id,self.season).keys()
        self.settings=Settings(self.league_id,self.season)
        self.games=nflgame.seq.Gen(nflgame.games(self.season))
        self._players=_json_league_players(self.league_id,self.season)
        self.league_name=self.settings.basic.league_name 
        self._schedule=_json_load_schedule(self.league_id,self.season)       
        self.owner_info=_json_load_owners(self.league_id,self.season)
        self._teams={}

    def teams(self):
        #returns list of all Team objects in league. Creates if not exisitent
        for tid in self.team_ids:
            if tid not in self._teams:
                self._teams[tid]=nflleague.team.Team(tid,self)
        return self._teams.values()

    def team(self,team):
        #returns specified Team object
        tid=nflleague.standard_team_id(self.league_id,self.season,team)
        if tid not in self._teams:
            self._teams[tid]=nflleague.team.Team(tid,self)
        return self._teams[tid]
          
    def team_ids(self):
        return self.team_ids
    
    def divisions(self):
        divs={}
        for team in self.teams():
            try:
                divs[team.team_div].extend([team])
            except KeyError:
                divs[team.team_div]=[team]
        return divs
           
    def all_players(self,week):
        def gen():
            for pid,plyr in self._players.iteritems():
                try:
                    if plyr['position'][str(self.season)][str(week)] in self.settings.roster.actives:
                        yield nflleague.player.PlayerWeek(self.league_id,self.season,week,pid,\
                                                       games=self.games,meta=plyr['lineup'].get(str(week),None))
                except KeyError:
                    continue
                except TypeError:
                    continue
        return nflleague.seq.GenPlayer(gen())
    
    def waivers(self,week,pos=None):
        waiver_wire=self.all_players(week).filter(team_abv='FA')
        if pos!=None:
            return waiver_wire.filter(position=pos)
        return waiver_wire
    


class Seasons(dict):
    def __init__(self,league_id,seasons):
        super(Seasons,self).__init__({season:nflleague.league.League(league_id,season) for season in seasons})
    def team(self,team,seasons=None):
        if seasons==None:
            return {k:v.team(team) for k,v in self.iteritems() if v.team(team)!=None}
        elif type(seasons)==list:
            return {k:v.team(team) for k,v in self.iteritems() if k in seasons and v.team(team)!=None}
    def teams(self,seasons=None):
        if seasons==None:
            return {k:v.team(team) for k,v in self.iteritems()}
        elif type(seasons)==list:
            return {k:v.team(team) for k,v in self.iteritems() if k in seasons}
    def owners(self,seasons=None):
        if seasons==None:
            return {year:v._owner_info.values() for year,v in self.iteritems()}
        elif type(seasons)==int:
            return self[seasons]._owner_info.values()
        elif type(seasons)==list:
            return {year:v._owner_info.values() for year,v in self.iteritems() if year in seasons}
        

class Category(dict):
    __getattr__=dict.get
    __setattr__=dict.__setitem__
    __delattr__=dict.__delitem__

#DONE Scrape settings function is complete, just needs implemented here.
class Settings(object):
    def __init__(self,league_id,season):
        self.league_id=league_id
        self.season=season
        self.roster=Category(_load_settings(self.league_id,self.season,'roster'))
        self.basic=Category(_load_settings(self.league_id,self.season,'basic'))
        self._schedule=Category(_json_load_schedule(self.league_id,self.season))
     
    def schedule(self,week,team_id):
        return self._schedule.get(str(week),{}).get(str(team_id),0)

    def positions(self,Bench=False,IR=False):
        func=lambda x: x not in ['' if Bench else 'Bench', '' if IR else 'IR']
        return filter(func,self.roster.actives)
    
    def gsis_positions(self,Bench=False,IR=False):
        func=lambda x: x not in ['' if Bench else 'Bench', '' if IR else 'IR']
        return filter(func,self.roster.gsis_actives)

    def divisions(self):
        #TODO scrape divisions
        return ['NORTHNORTHEASTERN','GREAT LAKES REGION']
    
    def n_teams(self):
        return int(self.basic.number_of_teams)


def _json_load_owners(league_id,season):
    return get_json('nflleague/espn-league-json/{}/{}/owner_info.json'.format(league_id,season),{})

def _load_settings(league_id,season,category):
    settings=get_json('nflleague/espn-league-json/{}/{}/settings.json'.format(league_id,season),{})
    assert settings!={},'Settings Not Created.'
    return settings.get(category,{})

def _json_load_schedule(league_id,season):
    schedule=get_json('nflleague/espn-league-json/{}/{}/schedule.json'.format(league_id,season),{})
    assert schedule!={},'Schedule Not Created.'
    return schedule

def _json_league_players(league_id,season):
    path='nflleague/espn-league-json/{}/{}/lineup_by_player.json'
    comb=get_json(path.format(league_id,season),{})
    orig=deepcopy(nflleague.players)
    
    for pid in orig.keys():
        orig[pid]['lineup']=comb[pid]
    return orig
