import nflgame
from nflgame import OrderedDict
import nflleague
import nflleague.team_rosters
from nflleague.functions import get_json,save_json
#from nflleague.schedule import _build_gsis_sched
import json,os,itertools
from collections import Counter,defaultdict

#TODO improve uniformity of json import method, exception handling, and use (Low)
#DONE cached defenses (MEDIUM)
#DONE fix kicker scoring by summing points by play? (HIGH)
#DONE fix DST yardage allowed (HIGH)
#DONE add game status function

allPlayers=nflgame.player._create_players()#needed?
playerData=json.loads(open(nflgame.player._player_json_file).read())#needed?

gsis_sched=nflleague.schedule.build_gsis_sched(nflleague.c_year,nflleague.c_week+5)

def get_game_status(game):
    if game == 'bye':
        return 'BYE'
    elif game == None:
        return 'NOT PLAYED'
    elif game.time.is_pregame():
        return 'PREGAME'
    elif game.time.is_halftime():
        return 'HALFTIME'
    elif game.playing():
        return 'PLAYING'
    elif game.game_over():
        return 'PLAYED'
    else:
        assert "game does not fall into any predefined categories (FUNCTION)" 

def _create_week_players():
    return get_json('nflleague/players.json',{})

#Could combine Player and Defense classes
class Player(nflgame.player.Player):
    def __init__(self,season,week,player_id):
        data=nflleague.players.get(player_id)
        super(Player,self).__init__(data)
        self.season=season
        self.week=week
        
        if type(self.team)==dict:
            self.team=self.team.get(str(season),{}).get(str(week),'UNK')
        if type(self.position)==dict:
            self.position=self.position.get(str(season),{}).get(str(week),'UNK')
        self.game_eid=data['schedule'].get(str(season),{}).get(str(week),'bye')
        self.bye=True if self.game_eid=='bye' else False
        if not self.bye:
            self.schedule=nflgame.sched.games.get(self.game_eid,{})
        else:
            self.schedule={}
    
    def game_status(self):
        return get_game_status(self.game)
    
    def game_info(self,item):
        if self.bye:
            return 'BYE'
        else:
            return self.schedule.get(item,'')
    
    def mins_remaining(self):
        if self.game_status() in ['NOT PLAYED','PREGAME']:
            return 60
        elif self.game_status() == 'HALFTIME':
            return 30
        elif self.game_status() in ['BYE','PLAYED']:
            return 0
        elif self.game_status() == 'PLAYING':
            return int(self.game.time._minutes)+(15*(4-int(self.game.time.qtr)))
    
    def formatted_stats(self):
        stats=self.statistics()
        try:
            print("{} [{}] {} {} {}".format(self.full_name,self.player_id,self.position,self.team,self.game_status()))
            print("\tScore: {}".format(self.statistics().score()))
            for k,v in self.statistics().stats.iteritems():
                print("\t{}: {} ({} pts)".format(k,v,self.statistics().scoring().get(k,0)))
        except Exception as err:
            print('No stats available for {}'.format(self.full_name))
    
class PlayerWeek(Player):
    def __init__(self,league_id,season,week,player_id):
        super(PlayerWeek,self).__init__(season,week,player_id)
        self.league_id=league_id

        self._stats=None
        self._projs=None
        self._plays=None
        
        if not self.bye:
            print(self.schedule.get('eid'))
            self.game=nflgame.game.Game(self.schedule.get('eid'))
        else:
            self.game='bye'

    def statistics(self,system='Custom'):
        stats=gen_player_stats(self.season,self.week,self.player_id,self.team,self.game)
        if self._stats==None and stats!=False:
            a,b,c,d,e=self.league_id,self.season,self.position,stats,self.game
            self._stats=nflleague.scoring.PlayerStatistics(a,b,c,d,e)
        return self._stats
        
    def projections(self,sites=['ESPN','FantasyPros','CBS'],system='Custom'):
        projections=nflleague.scoring.Projections()
        for site in sites:
            filename='nflleague/espn-league-json/projections/week{}/{}.json'.format(self.week,site.lower())
            projection=json.loads(open(filename).read())
            try:         
                proj=projection[self.player_id]
            except KeyError:
                proj={}
            a,b,c,d,e=self.league_id,self.season,self.position,proj,self.game
            projections[site]=nflleague.scoring.PlayerStatistics(a,b,c,d,e)
        
        return projections
    
    def historical_stats(self,years,weeks=None):
        #Returns dictionary of historical and current player stats which can be quickly accessed by [season][week]
        #Will be cached locally for fast retreival if stats have not been accessed before.
        #Use self.statistics() for current weeks stats when live functionality is important. 
        #Completely independent of fantasy league

        #For all weeks. Regular season only for now.
        if weeks==None:
            weeks=[]
            for year in years:
                if str(year) == str(nflleague.c_year):
                    weeks.append(range(1,int(nflleague.c_week)+1))
                else:
                    weeks.append(range(1,18))
            
        history={}
        for i,year in enumerate(years):
            history[year]={}
            for week in weeks[0]:
                a,b,c,d=year,week,self.player_id,self.team
                stats=gen_player_stats(a,b,c,d)
                history[year][week]=nflleague.scoring.LeagueScoring(self.league_id,year,self.position,stats)
        return history
    
    def combine_plays(self):
        if self._plays==None:
            self._plays=filter(lambda p: p.has_player(self.player_id),nflgame.combine_plays([self.game]))
        return self._plays
    
    def RB_success_rate(self):
        rushing_att=self.statistics().stats.get('rushing_att',0)
        if self.position == 'RB' and rushing_att != 0:
            success=0
            for play in self.combine_plays():
                n=play.down
                x=play.yards_togo
                if 4-n == 0:
                    if play._stats.get('rushing_yds',0) >= x:
                        success+=1
                elif play._stats.get('rushing_yds',0) >= float(x)/(4-n):
                    success+=1
            return float(success)/rushing_att
        return 0
   
    def points_added_per_play(self):
        critical_plays=0
        for play in self.combine_plays():
            if play._stats.get('rushing_att',0) or play._stats.get('receiving_tar',0):
                critical_plays+=1
        return float(self.score)/critical_plays if critical_plays!=0 else 0
    
    def redzone_usage(self):
        def redzone(team,play_gen):
            pos=nflgame.game.FieldPosition(team,offset=30)
            return filter(lambda p: p.team==team and p.yardline>=pos,list(play_gen))
        
        rz_plays=redzone(self.team,self.game.drives.plays())
        rz_play_count=0
        for play in list(rz_plays):
            if play._stats.get('receiving_tar',0) or play._stats.get('rushing_att',0):
                rz_play_count+=1
        rz_player_count=len(filter(lambda p: p.has_player(self.player_id),rz_plays))
        
        return float(rz_player_count)/rz_play_count if rz_play_count!=0 else 0
    
    def redzone_td_rate(self):
        def redzone(team,play_gen):
            pos=nflgame.game.FieldPosition(team,offset=30)
            return filter(lambda p: p.team==team and p.yardline>=pos,play_gen)
        
        rz_plays=redzone(self.team,self.game.drives.plays())
        rz_indv_all=filter(lambda p:p.has_player(self.player_id),rz_plays)
        rz_indv_td=filter(lambda p:p.touchdown==True,rz_indv_all)
        if len(rz_indv_all)!=0:
            return float(len(rz_indv_td))/len(rz_indv_all)
        else:
            return 0
    
    def redzone_plays(self):
        def redzone(team,play_gen):
            pos=nflgame.game.FieldPosition(team,offset=30)
            return filter(lambda p: p.team==team and p.yardline>=pos,play_gen)
        return filter(lambda p:p.has_player(self.player_id),redzone(self.team,self.game.drives.plays()))


#Class for managing owned players within a league.  Contains league,team, and week metadata
class PlayerTeam(PlayerWeek):
    def __init__(self,data,meta):
        super(PlayerTeam,self).__init__(meta.league_id,meta.season,meta.week,data.get('player_id'))
        self.team_id=meta.team_id

        self.position=data.get('position','')
        self.slot=data.get('slot','')
        self.gsis_slot=data.get('gsis_slot','')
        self.score=round(float(data.get('score',0)),1)
        self.in_lineup=bool(data.get('in_lineup',False))
        self.condition=data.get('condition','')
    
#class for managing Free Agents within a league.  Players will have no metadata.
class FreeAgent(PlayerWeek):
    def __init__(self,league_id,season,week,player_id):
        super(FreeAgent,self).__init__(league_id,season,week,player_id)
        

class Defense(Player):
    def __init__(self,season,week,team):
        super(Defense,self).__init__(season,week,nflgame.standard_team(team))

#TODO Clunky.  Needs work. Defense Classes need restructuring in line with structure of 'Player' class/subclasses
class DefensePlayerWeek(Player):
    def __init__(self,meta,player_id,stats,game=None):
        super(DefensePlayerWeek,self).__init__(meta.season,meta.week,player_id)
        self.league_id=meta.league_id
        self.team_id=meta.team_id
        
        self.position=self.position if self.position=='' else 'DEF'
        self.game=game
        if not self.bye and self.game==None:
            self.game=nflgame.game.Game(self.game_eid)

        self._stats=nflleague.scoring.LeagueScoring(self.league_id,self.season,self.position,stats,'Custom')
    def statistics(self,system='Custom'):
        return self._stats

#metadata is week/team/league data. data is lineup data from ESPN
class DefenseWeek(Defense):
    def __init__(self,data,meta):
        super(DefenseWeek,self).__init__(meta.season,meta.week,data.get('player_id').split()[0])
        self.league_id=meta.league_id
        self.team_id=meta.team_id
        self.meta=meta

        self.slot=data.get('slot')
        self.gsis_slot=data.get('gsis_slot')
        self.score=round(float(data.get('score')),2)
        self.in_lineup=bool(data.get('in_lineup'))
        self.condition=''

        self._stats=None
        self._projs=None
        self._players=None
        print(self.gsis_name) 
        if not self.bye:
            self.game=nflgame.game.Game(self.game_eid)
        else:
            self.game='bye'

        #print('DefenseWeek Object Initiated {} {} {}'.format(self.team,self.season,self.week))
            
    def statistics(self,system='Custom'):
        #Fastest way to access statistics for current week.
        stats=gen_defense_stats(self.season,self.week,self.team,self.game)
        if self._stats==None and stats!=False:
            stats=stats.get('defense',{})
            self._stats=nflleague.scoring.DefenseStatistics(self.league_id,self.season,self.team,stats,self.game)
        
        return self._stats

    def projections(self,sites=['ESPN','FantasyPros','CBS'],system='Custom'):
        projections=nflleague.scoring.Projections()
        for site in sites:
            #TODO Make separate json access function
            filename='nflleague/espn-league-json/projections/week{}/{}.json'.format(self.week,site.lower())
            projection=json.loads(open(filename).read())
            try:         
                #TODO make all internal references to defense of standard name type (i.e. NE vs Patriots)
                proj=projection[self.full_name]
            except KeyError:
                proj={}
            #TODO make generic LeagueScoring Object? 
            a,b,c,d,e=self.league_id,self.season,self.team,proj,self.game
            projections[site]=nflleague.scoring.DefenseStatistics(a,b,c,d,e)
        
        return projections
    
    def historical_stats(self,years,weeks=None):
        #Returns dictionary of historical and current player stats which can be quickly accessed by [season][week]
        #Will be cached locally for fast retreival if stats have not been accessed before.
        #Use self.statistics() when live functionality is important. 
        
        #For all weeks. Regular season only for now.
        if weeks==None:
            weeks=[]
            for year in years:
                if str(year) == str(nflleague.c_year):
                    weeks.append(range(1,int(nflleague.c_week)+1))
                else:
                    weeks.append(range(1,18))
            
        history={}
        for i,year in enumerate(years):
            history[year]={}
            for week in weeks[i]:
                a,b,c=year,week,self.team
                stats=gen_defense_stats(a,b,c)
                stats=stats.get('defense',{})
                history[year][week]=nflleague.scoring.LeagueScoring(self.league_id,year,'D/ST',stats)
        return history
        
    def players(self):
        #Returns list of DefensePlayerWeek objects of players who contributed to defensive stats
        if self._players==None:
            stats=gen_defense_stats(self.season,self.week,self.team,game=self.game)
            self._players=[]
            for plyr in stats:
                if plyr!='defense':
                    self._players.append(DefensePlayerWeek(self.meta,plyr,stats[plyr],game=self.game))
        return self._players
    
    def formatted_stats(self):
        try:
            print("{} {} {} {}".format(self.full_name,self.position,self.team,self.game_status()))
            print("\tScore: {}".format(self.statistics().score()))
            for k,v in self.statistics().stats.iteritems():
                print("\t{}: {} ({} pts)".format(k,v,self.statistics().scoring().get(k,0)))
        except Exception as err:
            print('No stats available for {}'.format(self.team))

#TODO Clean these up or eliminate.  To be deprecated soon
class PlayerWeekEmpty(PlayerWeek):
    def __init__(self,data,meta):
        self.player_id=None
        self.league_id=meta.league_id
        self.season=meta.season
        self.team_id=meta.team_id
        self.week=meta.week
        self.slot=data
        self.gsis_slot=data
        self.gsis_id=None
        self.gsis_name=None
        self.score=0
        self.bye=True
        self.team=None
        self.in_lineup=True
        self.gsis_name=None
        self.game='bye'
        self.full_name=None
        self.position=None
         
    def statistics(self,system='Custom'):
        #return empty player object
        return nflleague.scoring.PlayPlayerStatistics(self.player_id,self.game,self.gsis_id,False,self.team)
    
    def projections(self, sites=['ESPN','FantasyPros','CBS'],system='Custom'):
        #return empty projection object
        projections=nflleague.scoring.Projections()
        for site in sites:
            projections[site]=nflleague.scoring.PlayerProjections({},self,system)
        return projections


class DefenseWeekEmpty(DefenseWeek):
    def __init__(self,data,meta):
        self.player_id=None
        self.league_id=meta.league_id
        self.season=meta.season
        self.team_id=meta.team_id
        self.week=meta.week
        self.slot=data
        self.gsis_slot=data
        self.gsis_id=None
        self.gsis_name=None
        self.score=0
        self.bye=True
        self.team=None
        self.in_lineup=True
        self.gsis_name=None
        self.game='bye'
        self.full_name=None    
        self.position='D/ST'
    def statistics(self,system='Custom'):
        #return empty player object
        return nflleague.scoring.PlayPlayerStatistics(self.player_id,self.game,self.gsis_id,False,self.team)
    
    def projections(self, sites=['ESPN','FantasyPros','CBS'],system='Custom'):
        #return empty projection object
        projections=nflleague.scoring.Projections()
        for site in sites:
            projections[site]=nflleague.scoring.PlayerProjections({},self,system)
        return projections


def gen_player_stats(season,week,player_id,team,game=None):
    fp='nflleague/espn-league-json/cache/C{}.json'
    filepath=fp.format(player_id)
    cache=get_json(filepath,{})
    game_eid=nflleague.players[player_id]['schedule'].get(str(season),{}).get(str(week),'bye')
    week,season=str(week),str(season)
    if season not in cache.keys():
        cache[season]={}
    if week not in cache[season].keys() or (season,week) == (str(nflleague.c_year),str(nflleague.c_week)):
        if game_eid == 'bye':
            cache[season][week]={'BYE':True}
            save_json(filepath,cache)
            return cache[season][week] 
        
        if game==None:
            game=nflgame.game.Game(game_eid)
        
        game_status=get_game_status(game)
        #Only update if game is currently playing or player stats haven't been cached yet
        if game_status in ['NOT PLAYED','PREGAME']:
            return {}
        if game_status in ['PLAYING','HALFTIME'] or week not in cache[season].keys():
            player=None
            if player_id in nflleague.players:
                player=Player(season,week,player_id)
            print('Caching Player {}, {} {} (Y:{}  W:{})'.format(player.full_name,team,player.position,season,week))
            play_stats=nflgame.combine_max_stats([game])
            player_stats=list(play_stats.filter(playerid=player_id))
            if len(player_stats) != 0:
                cache[season][week]=player_stats[0].stats  
            else:
                cache[season][week]={}
            #Any specialty stats that need to be broken down by play or some other metric can be added here
            if player.position=='K':
                #Need to break down kicker scoring by play here because most efficient way to find length of indvl field goal.
                #Adds num of field goals made in 0-39,40-49,50+ ranges to kicker's stats dictionary.  
                print('Calculating Kicker Stats')
                play_stats=nflgame.combine_plays([game])
                plays=list(filter(lambda p: p.has_player(player_id),play_stats))
                cache[season][week]=defaultdict(int,cache[season][week])
                for play in plays:
                    if 'kicking_fgm' in play._stats:
                        if play._stats['kicking_fgm_yds'] <= 39:
                            cache[season][week]['kicking_fgm_0_39'] += 1
                        elif play._stats['kicking_fgm_yds'] <= 49:
                            cache[season][week]['kicking_fgm_40_49'] += 1
                        elif play._stats['kicking_fgm_yds'] >= 50:
                            cache[season][week]['kicking_fgm_50_100'] += 1
                    elif 'kicking_fgmissed' in play._stats and int(play._stats['kicking_fgmissed_yds']) <= 39:
                        cache[season][week]['kicking_fgmissed_0_39'] += 1
            save_json(filepath,cache)
    return cache[season][week]

def gen_defense_stats(season,week,team,game=None):
    fp='nflleague/espn-league-json/cache/C{}.json'
    filepath=fp.format(team)
    cache=get_json(filepath,{})
    game_eid=nflleague.players[team]['schedule'][str(season)][str(week)]
    week,season=str(week),str(season)
    if season not in cache.keys():
        cache[season]={}
    if week not in cache[season].keys() or (season,week) == (str(nflleague.c_year),str(nflleague.c_week)):
        if game_eid == 'bye':
            cache[season][week]={'BYE':True}
            save_json(filepath,cache)
            return cache[season][week] 
        
        if game==None:
            game=nflgame.game.Game(game_eid)
     
        game_status=get_game_status(game)
        
        if game_status in ['NOT PLAYED','PREGAME']:
            return {}
        if game_status in ['PLAYING','HALFTIME'] or week not in cache[season].keys():
            print('Caching {} Defense (Y:{}  W:{})'.format(team,season,week))
            players=nflgame.combine_max_stats([game])
            
            #individual players
            dst=filter(lambda p:p.team==team and (p.has_cat('defense') or p.has_cat('kickret') or p.has_cat('puntret')),players)
            cache[season][week]={}
            if len(dst) != 0:
                for dst_plyr in dst:
                    cache[season][week][dst_plyr.playerid]=dst_plyr._stats
            else:
                cache[season][week]={}
            #combines all individual player stats dicts into one team stats category for access w/o initing player objs
            cache[season][week]['defense']=reduce(lambda x,y:x+y,[Counter(dstats) for dstats in cache[season][week].values()])
            
            #team stats
            if game.home == team:
                cache[season][week]['defense']['defense_PA']=game.score_away
                opponent=game.away
            if game.away == team:
                cache[season][week]['defense']['defense_PA']=game.score_home
                opponent=game.home
            
            cache[season][week]['defense']['defense_rush'],cache[season][week]['defense']['defense_pass']=0,0
            dst_team=filter(lambda t:t.team==opponent,players)
            for off_p in dst_team:
                try:
                    #Find better way
                    DEF=['DE','DT','CB','SS','FS','MLB','OLB','ILB','DB','T','RT','LT','S','LB']
                    if off_p.player.position not in DEF:
                        cache[season][week]['defense']['defense_rush']+=off_p.rushing_yds
                        cache[season][week]['defense']['defense_pass']+=off_p.passing_yds+off_p.passing_sk_yds
                except Exception as err:
                    print(err)
            TYDA=cache[season][week]['defense']['defense_rush']+cache[season][week]['defense']['defense_pass']
            cache[season][week]['defense']['defense_TYDA']=TYDA
            
            save_json(filepath,cache)
    return cache[season][week]
