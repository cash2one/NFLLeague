import nflgame
from nflgame import OrderedDict
import nflleague
from collections import defaultdict,Counter
import numpy as np
import json,os

def _load_scoring(league_id,season,defense=False,system='Custom'):
    scoring={}
    if system == 'Custom':
        scoring=json.loads(open('nflleague/espn-league-json/{}/{}/scoring.json'.format(league_id,season)).read())
    elif system == 'Standard':
        scoring=json.loads(open('nflleague/defaults/standard_scoring.json').read())
    elif system == 'PPR':
        scoring=json.loads(open('nflleague/defaults/ppr_scoring.json').read())
    if defense:
        return scoring['defense']
    else:
        return scoring

#DONE Make more robust and implement in PlayerStatistics and DefenseStatistics classes
class LeagueScoring(object):
    def __init__(self,league_id,season,position,stats,system='Custom'):
        self.league_id=league_id
        self.season=season
        self.position=position
        self.system=system
        if self.position in ['QB','RB','WR','TE','K']:
            self.points=_load_scoring(self.league_id,self.season,system=system)
        else:
            self.points=_load_scoring(self.league_id,self.season,defense=True,system=system)
        self._stats=stats
        
        #Add bonus keys
        bonus=['passing_yds_300','passing_yds_400','rushing_yds_100',
                'rushing_yds_200','receiving_yds_100','receiving_yds_200']
        for bon in bonus:
            if self.points.get(bon,False):
                self._stats[bon]=0

    def scoring(self):
        return {k:round(float(self.__score(k,v)),1) for k,v in self._stats.iteritems()}
    
    def score(self):
        return round(sum(self.scoring().values()),1)
    
    def __score(self,key,val):
        val=round(float(val),2)
        
        if key in ['passing_yds','rushing_yds','receiving_yds']:
            for yds in [1,5,10,25]:
                if self.points.get('{}_{}'.format(key,yds),False):
                    return (int(val)/yds)*(float(self.points['{}_{}'.format(key,yds)]))
        elif key == 'passing_int' or key == 'defense_int':
            return val*float(self.points.get('interception',0))
        elif key == 'defense_fgblk' or key == 'defense_xpblk' or key == 'defense_puntblk':
            return val*float(self.points.get('defense_blkk',0))
        #potential problem here
        elif key == 'defense_misc_tds':
            return val*float(self.points.get('defense_blkkrtd',0))
        elif key == 'kickret_yds' or key == 'puntret_yds':
            return (int(val)/25)*float(self.points.get(key,0))
        elif key == 'defense_PA':
            if val == 0: return self.points.get('defense_PA_0',0)
            elif val <= 6: return self.points.get('defense_PA_1_6',0)
            elif val <= 13: return self.points.get('defense_PA_7_13',0)
            elif val <= 17: return self.points.get('defense_PA_14_17',0)
            elif val <= 21: return self.points.get('defense_PA_18_21',0)
            elif val <= 27: return self.points.get('defense_PA_22_27',0)
            elif val <= 34: return self.points.get('defense_PA_28_34',0)
            elif val <= 45: return self.points.get('defense_PA_35_45',0)
            elif val > 46: return self.points.get('defense_PA_46',0)
        elif key == 'defense_TYDA':
            if val <= 99: return self.points.get('defense_YA_99',0)
            elif val <= 199: return self.points.get('defense_YA_199',0)
            elif val <= 299: return self.points.get('defense_YA_299',0)
            elif val <= 349: return self.points.get('defense_YA_349',0)
            elif val <= 399: return self.points.get('defense_YA_399',0)
            elif val <= 449: return self.points.get('defense_YA_449',0)
            elif val <= 499: return self.points.get('defense_YA_499',0)
            elif val <= 549: return self.points.get('defense_YA_549',0)
            elif val > 549: return self.points.get('defense_YA_550',0)
        #Bonus
        elif key == 'passing_yds_400' and self._stats.get('passing_yds',0) >= 400:
            return self.points.get(key,0)
        elif key == 'passing_yds_300' and self._stats.get('passing_yds',0) >= 300:
            return self.points.get(key,0)
        elif key == 'rushing_yds_200' and self._stats.get('rushing_yds',0) >= 200:
            return self.points.get(key,0)
        elif key == 'rushing_yds_100' and self._stats.get('rushing_yds',0) >= 100:
            return self.points.get(key,0)
        elif key == 'receiving_yds_200' and self._stats.get('receiving_yds',0) >= 200:
            return self.points.get(key,0)
        elif key == 'receiving_yds_100' and self._stats.get('receiving_yds',0) >= 100:
            return self.points.get(key,0)
        elif key == 'kicking_fgm_proj':
            return float(self.points.get('kicking_fgm_0_39',0))*val
        return float(self.points.get(key,0))*val

    @property
    def stats(self):
        return self._stats
    
    def _add_stats(self,stats):
        for k,v in stats.iteritems():
            self._stats[k]=self._stats.get(k,0)+v

    def __add__(self,other):
        assert type(self)==type(other)

        new_object=self.__class__(self.league_id,self.season,self.position,{},self.system)
        new_object._add_stats(self._stats)
        new_object._add_stats(other._stats)
        
        return new_object
    
    def __getattr__(self,item):
        try:
            return self.stats[item]
        except KeyError:
            return 0


class PlayerStatistics(LeagueScoring):
    def __init__(self,league_id,season,position,stats,game=None,system='Custom'):
        stats=stats if stats!=None else {}
        super(PlayerStatistics,self).__init__(league_id,season,position,stats,system)
        self.game=game
        #print('PLAYER STATS INITIATIED')    
    
    def projected(self,proj):
        if self.game == 'bye':
            return 0
        elif self.game == None or self.game.time.is_pregame():
            return proj
        elif self.game.time.is_halftime():
            return round(self.score() + float(proj)/2,1)
        elif self.game.playing():
            return round(self.score()+(int(self.game.time._minutes)+(15*(4-int(self.game.time.qtr))))*(float(proj)/60),1)
        elif self.game.time.is_final():
            return self.score()
        else:
            print('PROBLEM IN PROJECTED FUNCTION')
            return 0


class DefenseStatistics(LeagueScoring):
    def __init__(self,league_id,season,team,stats,game=None,system='Custom'):
        super(DefenseStatistics,self).__init__(league_id,season,'D/ST',stats,system=system)
        self.team=team
        self.game=game
    
    def projected(self,proj):
        if self.game == 'bye':
            return 0
        elif self.game == None or self.game.time.is_pregame():
            return proj
        elif self.game.time.is_halftime():
            return round(self.score() + float(proj)/2,1)
        elif self.game.playing():
            return round(self.score()+(int(self.game.time._minutes)+(15*(4-int(self.game.time.qtr))))*(float(proj)/60),1)
        elif self.game.time.is_final():
            return self.score()
        else:
            print('PROBLEM IN PROJECTED FUNCTION')
            return 0
    
    def yardage_breakdown(self):
        if self.game!=None:
            self._stats=defaultdict(int,self._stats)
            for plyr in self.game.max_player_stats():
                if plyr.team != self.team:
                    if plyr.player==None:
                        pos=nflleague.team_rosters.guess_pos(plyr)
                    else:
                        pos=plyr.player.position
                    if pos in ['QB','WR','RB','TE']:
                       self._stats['yds_allowed_pass_{}'.format(pos.lower())]+=plyr.passing_yds
                       self._stats['yds_allowed_rush_{}'.format(pos.lower())]+=plyr.rushing_yds
                       self._stats['yds_allowed_rec_{}'.format(pos.lower())]+=plyr.receiving_yds
        return self._stats

#deprecated
class PlayPlayerStatistics(PlayerStatistics):
    #for use in the case the game hasn't been played yet, create class with no statistics
    def __init__(self,player_id,game,name,home,team):
        self.__dict__=nflgame.player.PlayPlayerStats(player_id,name,home,team).__dict__
        self.game=game


#deprecated
class PlayerProjections(PlayerStatistics):
    def __init__(self,projection_stats,player,system):
        self.team=player.team 
        self.game=player.game
        self.points=_load_scoring(player.league_id,player.season,system)
        self._stats=projection_stats

#deprecated
class DefenseProjections(DefenseStatistics):
    def __init__(self,projection_stats,defense,system):
        self.team=defense.team
        self.game=defense.game
        self.points=_load_scoring(defense.league_id,defense.season,defense=True,system=system)
        self._stats=projection_stats
        
class Projections(dict):
#collection of PlayerProjections or DefenseProjections objects each with key corresponding to website it was scraped from. 
    def __init__(self):
        super(Projections,self).__init__()
    def scoring(self):
        return {k:v.scoring() for k, v in self.iteritems()}
    def scores(self,rnd=2):
        return {k:round(sum(v.scoring()),2) for k,v in self.iteritems()}
    def max_score(self,rnd=2):
        return round(max([v.score() for v in self.values()]),rnd)
    def min_score(self,rnd=2):
        return round(min([v.score() for v in self.values()]),rnd)
    def mean_score(self,rnd=2):
        return round(np.mean([v.score() for v in self.values()]),rnd)
    def std_dev(self,rnd=2):
        return round(np.std([v.score() for v in self.values()]),rnd)
    def sites(self):
        return self.keys()

