from __future__ import print_function
import json
import nflgame
import nflleague
import nflleague.update 
import nflleague.league
from collections import OrderedDict,defaultdict
import itertools
import os
import scipy.stats
import collections

#TODO cache win/loss

class Week(object):
    def __init__(self,week,team):
        for k,v in team.__dict__.iteritems():
            self.__dict__[k]=v
        
        self.week=str(week)
        self.schedule=self.schedule.get(self.week,{})
        self._opponent=nflleague.standard_team_id(self.league_id,self.season,self.schedule.get('Opponent',None))
        self.__opponent_obj=None
        self.home=bool(self.schedule.get('Home',False))
        
        self.data=nflleague.player._json_lineup_by_team(self.league_id,self.season,self.week,self.team_id)
        self._lineup=[]
        """
        for slot in self.settings.gsis_positions():
            a,b,c,pid,e=self.league_id,self.season,self.week,data[slot].get('player_id',''),self.games
            if data[slot].get('position')!='D/ST':
                self.lineup.append(nflleague.player.PlayerWeek(a,b,c,pid,e,meta=self._players[pid]['lineup'].get(self.week)))
            else:
                pid=nflleague.standard_nfl_abv(pid)
                self.lineup.append(nflleague.player.DefenseWeek(a,b,c,pid,e,meta=self._players[pid]['lineup'].get(self.week)))
            
        self.bench=[]
        for plyr in data.get('Bench',[]):
            a,b,c,pid,e=self.league_id,self.season,self.week,plyr.get('player_id',''),self.games
            if plyr.get('position')!='D/ST':
                self.bench.append(nflleague.player.PlayerWeek(a,b,c,pid,e,meta=self._players[pid]['lineup'].get(self.week)))
            else:
                pid=nflleague.standard_nfl_abv(pid)
                self.bench.append(nflleague.player.DefenseWeek(a,b,c,pid,e,meta=self._players[pid]['lineup'].get(self.week)))
        if 'IR' in data:
            a,b,c,d,e=self.league_id,self.season,self.week,data['IR'].get('player_id'),self.games
            self.IR=nflleague.player.PlayerWeek(a,b,c,d,e)
        else:
            self.IR=None
        """
    @property
    def lineup(self):
        lnp=[]
        for slot in self.settings.gsis_positions():
            plyr=self.data[slot]
            if plyr.get('position')=='D/ST':
                plyr['player_id']=nflleague.standard_nfl_abv(plyr.get('player_id',''))
            lnp.append(self.league_players[plyr.get('player_id','')].spawn(self.week))
        return lnp

    @property
    def bench(self): 
        for plyr in self.data.get('Bench',[]):
            if plyr.get('position')=='D/ST':
                plyr['player_id']=nflleague.standard_nfl_abv(plyr.get('player_id',''))
            lnp.append(self.league_players[plyr.get('player_id','')].spawn(self.week))
        
        return lnp

    def get_all(self,IR=False):
        if IR:
            return self.lineup+self.bench+[self.IR]
        else:
            return self.lineup+self.bench
    
    def get_score(self):
        return sum([p.stats().score() for p in self.lineup])

    def opponent(self):
        if self._opponent==None:
            return ByeWeek(self.week)
        if self.__opponent_obj==None:
            if self._opponent in self._teams:
                self.__opponent_obj=self._teams.get(self._opponent).week(self.week)
            else:
                self.__opponent_obj=nflleague.team.FantasyTeam(self.league_id,self.season,self._opponent).week(self.week)
        
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
        #This function determines what the current optimal lineup would be at any given moment in time.  Projections 
        #and PF are taken into account.
        optimized=[]
        for p in self.get_all():
            if p.game_status() in ['NOT PLAYED','PREGAME']:
                optimized.append((p,float(p.projs().mean_score())))
            elif p.game_status() in ['PLAYING','HALFTIME']:
                optimized.append((p,float(p.stats().projected(p.projs().mean_score()))))
            elif p.game_status() == 'PLAYED':
                optimized.append((p,float(p.stats().score())))
        
        optimized=sorted(optimized, key=lambda x: x[1],reverse=True)
        
        optimal=list()
        for slot in self.settings.positions():
            for p in optimized:
                if p[0].position == slot and p not in optimal:
                    optimal.append(p)
                    break
        flex=[p for p in optimized if p not in optimal and p[0].position in ['WR','RB','TE']]
        if len(flex)!=0:
            optimal.insert(self.settings.positions().index('FLEX'),flex[0])
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
            cum_exp+=plyr.stats().projected(plyr.projs().mean_score())
            if plyr.game_status() in ['NOT PLAYED','PREGAME']:
                cum_std+=plyr.projs().std_dev()
            elif plyr.game_status() in ['PLAYING','HALFTIME']:
                cum_std+=plyr.projs().std_dev()*(float(plyr.mins_remaining())/60)
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
    
    def __getattr__(self,item):
        return self.__dict__.get(item,'')

    def __str__(self):
        return '{} ({}) vs {} ({})'.format(self.team_abv,self.get_score(),self.opponent().team_abv,self.opponent().get_score())

class ByeWeek(Week):
    def __init__(self,week):
        self.week=week
