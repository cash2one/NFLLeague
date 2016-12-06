from __future__ import print_function
import json
import nflgame
from nflleague.player import PlayerTeam,DefenseWeek,DefensePlayerWeek,PlayerWeekEmpty,DefenseWeekEmpty
import nflleague
import nflleague.update 
import nflleague.league
from collections import OrderedDict,defaultdict
import itertools
import os
import scipy.stats
import collections

team=[]
#TODO Replace with nflleague.league.Settings(x,y).rosters.{actives/gsis_actives}
ACTIVES=['QB','RB','RB','WR','WR','TE','FLEX','D/ST','K']
GSIS_POS=['QB','RB1','RB2','WR1','WR2','TE','FLEX','D/ST','K']
#TODO cache win/loss
class Week(nflleague.team.Team):
    def __init__(self,week,schedule,team):
        super(Week,self).__init__(team.owner_info,team.league)
        self.week=week
        self.team=self.team_id
        self._opponent=schedule['Opponent']
        self.__opponent_obj=None
        self.home=bool(schedule['Home'])
        self.settings=team.league.settings 
        #TODO Reorganize.  I don't like this complex init.  _load_week function for json?
        data=json.loads(open('nflleague/espn-league-json/{}/{}/lineup_by_week.json'.format(self.league_id,self.season)).read()) 
        data=data[str(self.team_id)][str(self.week)]
        
        #sIs:slot/playerId or name/score
        self.lineup=[]
        for slt in GSIS_POS:
            if slt in data.keys():
                if slt != 'D/ST':
                    self.lineup.extend([PlayerTeam(data[slt],self)])
                elif slt == 'D/ST':
                    self.lineup.extend([DefenseWeek(data[slt],self)])
            else:
                if slt != 'D/ST':
                    self.lineup.extend([PlayerWeekEmpty(slt,self)])
                elif slt == 'D/ST':
                    self.lineup.extend([DefenseWeekEmpty(slt,self)])
        
        self.bench=[]
        for sIs in data['Bench']:
            if sIs['player_id'].split(" ")[-1]!='D/ST':
                self.bench.extend([PlayerTeam(sIs,self)])
            else:
                self.bench.extend([DefenseWeek(sIs,self)])
        
        try:
            self.IR=PlayerTeam(data['IR'],self)
        except KeyError:
            self.IR=None
    
    def get_all(self,IR=False):
        if IR:
            return self.lineup+self.bench+[self.IR]
        else:
            return self.lineup+self.bench
    
    def get_score(self):
        return sum([p.score for p in self.lineup])

    def opponent(self):
        if self.__opponent_obj==None:
            self.__opponent_obj=self.league.team(self._opponent).week(self.week)
        return self.__opponent_obj

    def win(self):
        score,opp_score=self.get_score(),self.opponent().get_score()
        if score > opp_score:
            return True
        elif score < opp_score:
            return False
        elif self.home:
            return True
        return False

    def optimal_lineup(self):
        optimized=[]
        #JAC/Jax issue fixed 11/15
        for p in self.get_all():
            if p.game_status() in ['NOT PLAYED','PREGAME']:
                optimized.append((p,float(p.projections().mean_score())))
            elif p.game_status() in ['PLAYING','HALFTIME']:
                optimized.append((p,float(p.statistics().projected(p.projections().mean_score()))))
            elif p.game_status() == 'PLAYED':
                optimized.append((p,float(p.statistics().score())))
        
        optimized=sorted(optimized, key=lambda x: x[1],reverse=True)
        
        optimal=list()
        for slot in ACTIVES:
            for p in optimized:
                if p[0].position == slot and p not in optimal:
                    optimal.append(p)
                    break
        
        flex=[p for p in optimized if p not in optimal and p[0].position in ['WR','RB','TE']][0]
        optimal.insert(ACTIVES.index('FLEX'),flex)
        return optimal

    def mins_remaining(self):
        return sum([p.mins_remaining() for p in self.lineup])
    
    def yet_to_play(self):
        return filter(lambda p: p.game_status() in ['NOT PLAYED','PREGAME'],self.lineup)

    def in_play(self):
        return filter(lambda p: p.game_status() in ['PLAYING','HALFTIME'],self.lineup)

    def score_proj_distro(self):
        #Demo Basic Win Expectancy Alg (Cauchy Model)
        cum_exp,cum_std=0,0
        for plyr in self.lineup:
            cum_exp+=plyr.statistics().projected(plyr.projections().mean_score())
            if plyr.game_status() in ['NOT PLAYED','PREGAME']:
                cum_std+=plyr.projections().std_dev()
            elif plyr.game_status() in ['PLAYING','HALFTIME']:
                cum_std+=plyr.projections().std_dev()*(float(plyr.mins_remaining())/60)
            elif plyr.game_status() in ['PLAYED']:
                cum_std+=0
        
        if cum_std != 0:
            return scipy.stats.cauchy(loc=cum_exp,scale=5*cum_std)
        else:
            class BinaryDistro(object):
                def __init__(self,loc=0,scale=0):
                    self.loc=loc
                    self.scale=scale
                def ppf(self,x):
                    return self.loc
                def cdf(self,x):
                    if x > self.loc:
                        return 1.0
                    elif x < self.loc:
                        return 0.0
                    else:
                        return 0.5
                def pdf(self,x):
                    if round(x,1) != round(cum_exp,1):
                        return 0
                    else:
                        return 1
            return BinaryDistro(loc=cum_exp)
    
    def win_expectancy(self):
        distro=self.score_proj_distro()
        opp_distro=self.opponent().score_proj_distro()
        if distro.ppf(0.5) >= opp_distro.ppf(0.5):
            if self.get_score()>self.opponent().get_score():
                val=round(opp_distro.cdf(distro.ppf(0.5)),5)
                if val < 0.01 or val > 0.99:
                    return val
                else:
                    return round(val,3)
            else:
                val=1-round(distro.cdf(opp_distro.ppf(0.5)),5)
                if val < 0.01 or val > 0.99:
                    return val
                else:
                    return round(val,3)
        else:
            if self.get_score()<self.opponent().get_score():
                val=1-round(distro.cdf(opp_distro.ppf(0.5)),5)
                if val < 0.01 or val > 0.99:
                    return val
                else:
                    return round(val,3)
            else:
                val=round(opp_distro.cdf(distro.ppf(0.5)),5)
                if val < 0.01 or val > 0.99:
                    return val
                else:
                    return round(val,3)
    
    def win_expectancy_plot(self):
        fp='nflleague/espn-league-json/{}/{}/win_exp/week{}.json'.format(self.league_id,self.season,self.week)
        try:
            xy=json.loads(open(fp).read())
        except Exception as err:
            folder='/'.join(fp.split('/')[:-1])
            if not os.path.exists(folder):
                os.makedirs(folder)
            xy={}
        data={}
        for key,val in xy.iteritems():
            data[key]=sorted(val,key=lambda x: x[0],reverse=True)
        mins=self.mins_remaining()
        opp_mins=self.opponent().mins_remaining()
        win_exp=self.win_expectancy()
        if str(self.team_id) in data.keys():
            if mins+opp_mins not in [x[0] for x in data[str(self.team_id)]]:
                y2,y1=win_exp,data[str(self.team_id)][-1][1]
                x2,x1=mins+opp_mins,data[str(self.team_id)][-1][0]
                m=float(y2-y1)/(x2-x1)
                prev=data[str(self.team_id)][-1][0]
                new=prev-1
                while(new!=mins+opp_mins):
                    new-=1
                    data[str(self.team_id)].append((new,m*(new-x1)+y1))
        else:
            data[str(self.team_id)]=[(2000,0)]
    
        with open(fp,'w') as out:
            json.dump(data,out)

        return data[str(self.team_id)]

