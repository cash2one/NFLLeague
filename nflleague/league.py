import nflleague
from nflleague.functions import get_json
import nflleague.team
import nflleague.schedule
import nflgame
import json
import numpy as np
from collections import defaultdict

#TODO cache expensive functions which return weekly constants such as record, score etc..
#TODO change heirarchy to league>SEASON>team>week>player>stats 
#       >> LEAGUE=nflleague.league.League(league_id)
#       >> LEAGUE.season(2015)+LEAGUE.season(2016) #for combine stats
#       >> LEAUGE.season(2016).teams()
#       >> LEAGUE.season(2010).team('CHAD MORTON').week(5).lineup.get('TE')
#   Would make interface more intuitive and eliminate need for confusing 'Seasons' dictionary with different league objects
#   Might take much longer to initialize Leauge Objet.  Could avoid, though

def _create_owners(league_id,season):
    return json.loads(open('nflleague/espn-league-json/{}/{}/owner_info.json'.format(league_id,season)).read())

def _create_league(league_id):
    #TODO Change to _load_settings and implement in Settings.  Use to manage all settings
    return {'league_name':'Penn Champions League'}

def _load_settings(league_id,season,category):
    settings=get_json('nflleague/espn-league-json/{}/{}/settings.json'.format(league_id,season),{})
    
    assert settings!={},'Settings Not Created.'
    
    return settings.get(category,{})



class League(object):
    def __init__(self,league_id,season):
        self.season=int(season)
        self.league_id=int(league_id)
        self._league_info=_create_league(self.league_id)
        self.league_name=self._league_info.get('league_name','NA')
        self._owner_info=_create_owners(self.league_id,self.season)
        self._league_schedule=json.loads(open('nflleague/espn-league-json/{}/{}/schedule.json'.format(\
                                                                                     self.league_id,self.season)).read())
        self._scoring=''
        self._teams={} 
        self.settings=Settings(self.league_id,self.season)
    
    def teams(self):
        #returns list of all Team objects in league. Creates if not exisitent
        if len(self._teams.keys()) != len(self._owner_info.keys()):
            for key,value in self._owner_info.iteritems():
                self._teams[key]=nflleague.team.Team(value,self)
        return self._teams.values()

    def team(self,team):
        #returns specified Team object
        for key,value in self._owner_info.iteritems():
            if team in value.values():
                return nflleague.team.Team(value,self)
    
    def team_ids(self):
        return self._owner_info.keys()
    
    def divisions(self):
        divs={}
        for team in self.teams():
            try:
                divs[team.team_div].extend([team])
            except KeyError:
                divs[team.team_div]=[team]
        return divs
    
    def all_players(self,week,pos=None):
        all_plyrs={}
        for pid,plyr in nflgame.players.iteritems():
            if plyr.status!='' and plyr.position in self.settings.roster.actives:
                if pos==None or plyr.position==pos:
                    all_plyrs[pid]=nflleague.player.FreeAgent(self.league_id,self.season,week,pid)
        return all_plyrs
    
    def waivers(self,week,pos=None):
        waiver_wire=self.all_players(week,pos=pos)
        for team in self.teams():
            for plyr in team.week(week).get_all(IR=True):
                if plyr!=None and plyr.player_id in waiver_wire:
                    del waiver_wire[plyr.player_id]
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
        rost=_load_settings(self.league_id,self.season,'roster')
        self.roster=Category(_load_settings(self.league_id,self.season,'roster'))
        self.basic=Category(_load_settings(self.league_id,self.season,'basic'))
    
    def positions(self,Bench=False,IR=False):
        func=lambda x: x not in ['' if Bench else 'Bench', '' if IR else 'IR']
        return filter(func,self.roster.actives)

    def divisions(self):
        #TODO scrape divisions
        return ['NORTHNORTHEASTERN','GREAT LAKES REGION']
    
    def n_teams(self):
        return int(self.basic.number_of_teams)
