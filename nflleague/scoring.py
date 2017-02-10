import nflgame
from nflgame import OrderedDict
import nflleague
import nflleague.seq
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


#Keeps handling of stats uniform to nflgame, but allows scores to be accessed as well
class LeagueScoring(dict):
    def __init__(self,league_id,season,position,system='Custom'):
        super(LeagueScoring,self).__init__()
        self.league_id=league_id
        self.season=season
        self.position=position
        self.system=system
        if self.position in ['QB','RB','WR','TE','K']:
            self.points=_load_scoring(self.league_id,self.season,system=system)
        else:
            self.points=_load_scoring(self.league_id,self.season,defense=True,system=system)
        
        #Add bonus keys
        bonus=['passing_yds_300','passing_yds_400','rushing_yds_100',
                'rushing_yds_200','receiving_yds_100','receiving_yds_200']
        for bon in bonus:
            if self.points.get(bon,False):
                self[bon]=0

    def scoring(self):
        return {k:round(float(self.__score(k,v)),1) for k,v in self.iteritems()}
    
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
        elif key == 'passing_yds_400' and self.get('passing_yds',0) >= 400:
            return self.points.get(key,0)
        elif key == 'passing_yds_300' and self.get('passing_yds',0) >= 300:
            return self.points.get(key,0)
        elif key == 'rushing_yds_200' and self.get('rushing_yds',0) >= 200:
            return self.points.get(key,0)
        elif key == 'rushing_yds_100' and self.get('rushing_yds',0) >= 100:
            return self.points.get(key,0)
        elif key == 'receiving_yds_200' and self.get('receiving_yds',0) >= 200:
            return self.points.get(key,0)
        elif key == 'receiving_yds_100' and self.get('receiving_yds',0) >= 100:
            return self.points.get(key,0)
        elif key == 'kicking_fgm_proj':
            return float(self.points.get('kicking_fgm_0_39',0))*val
        return float(self.points.get(key,0))*val


class PlayerStats(object):
    def __init__(self,league_id,season,week,position,game=None,system='Custom'):
        self.league_id=league_id
        self.season=season
        self.week=week
        self.position=position
        self.game=game
        self.system=system

        self._stats=LeagueScoring(league_id,season,position,system)
    
    def scoring(self):
        return self._stats.scoring()
    
    def score(self):
        return self._stats.score()
    
    @property
    def stats(self):
        return self._stats
    
    def _add_stats(self,data):
        for k,v in data.iteritems():
            #self.__dict__[k]=self.__dict__.get(k,0)+v
            #self._stats[k]=self.__dict__[k]
            self._stats[k]=self._stats.get(k,0)+v
    
    def __add__(self,other):
        assert isinstance(self,type(other)) or other==0 #other==0 to allow use of sum() function

        new_object=self.__class__(self.league_id,self.season,self.week,self.position,self.game,self.system)
        new_object._add_stats(self._stats)
        new_object._add_stats(other._stats)
        
        return new_object
    
    def __radd__(self,other):
        try:
            return self+other
        except AttributeError:
            return self
    
    def __getattr__(self,item):
        try:
            return self._stats[item]
        except KeyError as err:
            for cat in nflgame.statmap.categories:
                if item.startswith(cat):
                    return 0
            print(err)
            raise AttributeError
    
    def __str__(self):
        return str(self.score())


class DefenseStats(PlayerStats):
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


class PlayerProjs(PlayerStats):
    def __init__(self,league_id,season,week,position,site,game,system='Custom'):
        super(PlayerProjs,self).__init__(league_id,season,week,position,game,system)
        self.site=site
    
        self._projs=LeagueScoring(league_id,season,position,system)
    
    def scoring(self):
        return self._projs.scoring()
    
    def score(self):
        return self._projs.score()
    
    def projected(self):
        if self.game == 'bye':
            return 0
        elif self.game == None or self.game.time.is_pregame():
            return self._stats.score()
        elif self.game.time.is_halftime():
            return round(self._stats.score() + float(self._projs.score())/2,1)
        elif self.game.playing():
            return round(self._stats.score()+(int(self.game.time._minutes)+(15*(4-int(self.game.time.qtr))))*\
                                                                            (float(self._projs.score())/60),1)
        elif self.game.time.is_final():
            return self._stats.score()
    
    def _add_projs(self,data):
        for k,v in data.iteritems():
            self._projs[k]=self._projs.get(k,0)+v
    
    def __str__(self):
        return str(self._projs.score())


class GenPlayerStats(nflleague.seq.GenPlayer):
    def __init__(self,iterable):
        super(GenPlayerStats,self).__init__(iterable)
    
    def max_score(self):
        return list(self.sort(lambda x:x.score()))[0]
    
    def min_score(self):
        return list(self.sort(lambda x:x.score(),descending=False))[0]
    
    @property
    def mean(self,rnd=2):
        return round(np.mean([x.score() for x in list(self)]),rnd)

class GenPlayerProjs(GenPlayerStats):
    def sites(self):
        return [x.site for x in self]
    
    def __getattr__(self,item):
        if item in self.sites():
            return list(self.filter(site=item))[0]
        raise AttributeError
        
def _json_projections(week,site,pid):
    filename='nflleague/espn-league-json/projections/week{}/{}.json'.format(week,site.lower())
    return json.loads(open(filename).read()).get(pid,{})

