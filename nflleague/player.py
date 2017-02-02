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

class Player(nflgame.player.Player):
    def __init__(self,season,week,player_id):
        data=nflleague.players.get(player_id,nflleague.players['00-0000000'])
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
    
    def __str__(self):
        return '{}, {} {}'.format(self.full_name,self.team,self.position)

class PlayerWeek(Player):
    #team_id temporary until I have time to restructure teamweeklineups json data by player
    def __init__(self,league_id,season,week,player_id,games=None,meta=None):
        super(PlayerWeek,self).__init__(season,week,player_id)
        self.league_id=league_id
        self.games=games 
        
        self._stats=None
        self._projs=None
        self._plays=None
                
        if meta==None:
            self.meta=_json_lineup_by_player(self.league_id,self.season,self.week,self.player_id)
        else:
            self.meta=meta
        
        self.team_id=self.meta.get('team_id',0)
        self.team_abv=nflleague.league._json_load_owners(self.league_id,self.season).get(self.team_id,{}).get('team_abv','FA')
        self.position=self.meta.get('position',self.position)
        self.slot=self.meta.get('slot','NA')
        self.gsis_slot=self.meta.get('gsis_slot','NA')
        self.score=round(float(self.meta.get('score',0)),1)
        self.in_lineup=bool(self.meta.get('in_lineup',False))
        self.condition=self.meta.get('condition','NA')
        
        if self.bye:
            self.game='bye'
        else:
            if games==None:
                self.game=nflgame.game.Game(self.game_eid)
            else:
                self.game=list(games.filter(eid=self.game_eid))[0]
        
        #print('PlayerWeek Initialized {} {} {} {}'.format(self.season,self.week,str(self),self.team_abv))
         
    def stats(self,system='Custom'):
        if self._stats==None:
            self._stats=nflleague.scoring.PlayerStats(self.league_id,self.season,self.week,self.position,game=self.game)
            self._stats._add_stats(gen_player_stats(self.season,self.week,self.player_id,self.team,self.game))
        return self._stats

    def projs(self,system='Custom'):
        def projections():
            sites=[]
            for site in nflleague.sites:
                p=nflleague.scoring.PlayerProjs(self.league_id,self.season,self.week,self.position,site,self.game,system)
                p._add_stats(self.stats().stats)
                p._add_projs(nflleague.scoring._json_projections(self.week,site,self.player_id))
                
                sites.append(p)
            return sites

        if self._projs==None:
            self._projs=nflleague.scoring.GenPlayerProjs(projections())
        return self._projs
    
    def seasonal(self,inclusive=False):
        def __seasonal():
            weeks=[]
            for week in range(1,int(self.week)+1 if inclusive else int(self.week)):
                a,b,c,d,e=self.league_id,self.season,week,self.position,self.games
                weeks.append(nflleague.scoring.PlayerStats(a,b,c,d,e))
                weeks[-1]._add_stats(gen_player_stats(b,c,self.player_id,self.team,self.game))
            return weeks
        
        return nflleague.scoring.GenPlayerStats(__seasonal())
    
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
        stats=self.stats()
        try:
            print("{} [{}] {} {} {}".format(self.full_name,self.player_id,self.position,self.team,self.game_status()))
            print("\tScore: {}".format(self.stats().score()))
            for k,v in self.stats().stats.iteritems():
                print("\t{}: {} ({} pts)".format(k,v,self.stats().scoring().get(k,0)))
        except Exception as err:
            print('No stats available for {}'.format(self.full_name))
    
    def __add__(self,other):
        assert self.player_id==other.player_id,"Player Id's don't match"
        assert type(self)==type(other)
        new_player=self 
        new_player._stats=self.stats()+other.stats()
        new_player.week=None
        return new_player
    

class DefenseWeek(PlayerWeek):
    def __init__(self,league_id,season,week,player_id,games=None,meta=None):
        super(DefenseWeek,self).__init__(league_id,season,week,nflleague.standard_nfl_abv(player_id),games=games,meta=meta)
        self.__players=None

    def stats(self,system='Custom'):
        if self._stats==None:
            self._stats=nflleague.scoring.PlayerStats(self.league_id,self.season,self.week,'D/ST',self.game,system)
            self._stats._add_stats(gen_defense_stats(self.season,self.week,self.team,self.game).get('defense',{}))
        return self._stats
    
    def seasonal(self,inclusive=False):
        def __seasonal():
            weeks=[]
            for week in range(1,int(self.week)+1 if inclusive else int(self.week)):
                a,b,c,d,e=self.league_id,self.season,week,self.position,self.games
                weeks.append(nflleague.scoring.PlayerStats(a,b,c,d,e))
                weeks[-1]._add_stats(gen_defense_stats(self.season,week,self.team,self.game).get('defense',{}))
            return weeks
        
        return nflleague.scoring.GenPlayerStats(__seasonal())
    
    def players(self):
        #Returns list of DefensePlayerWeek objects of players who contributed to defensive stats
        #NEED TO FIX OFFENSIVE PLAYERS BEING COUNTED AS DEFENSIVE PLAYERS
        def def_players():
            players=[]
            defstats=gen_defense_stats(self.season,self.week,self.team,game=self.game)
            for pid,stats in defstats.iteritems():
                if pid!='defense':
                    players.append(DefPlayerWeek(self.league_id,self.season,self.week,pid,games=self.games))
            return players
        if self.__players==None:
            self.__players=nflleague.seq.GenPlayer(def_players())
        return self.__players
        

class DefPlayerWeek(PlayerWeek):
    def projs(self,system='Custom'):
        assert False, 'Cannot be Called on Individul Defensive Players'


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

def _json_week_players():
    return get_json('nflleague/players.json',{})

def _json_lineup_by_player(league_id,season,week,player_id):
    path='nflleague/espn-league-json/{}/{}/lineup_by_player.json'
    data=get_json(path.format(league_id,season),{})
    return data.get(player_id,{}).get(str(season),{}).get(str(week),{})

def _json_lineup_by_team(league_id,season,week,team_id):
    path='nflleague/espn-league-json/{}/{}/lineup_by_week.json'
    data=get_json(path.format(league_id,season),{})
    return data.get(str(team_id),{}).get(str(week),{})

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
            if not cache[season][week]=={}:
                val=cache[season][week].values()
                cache[season][week]['defense']=reduce(lambda x,y:x+y,[Counter(dstats) for dstats in val])
            else:
                cache[season][week]['defense']={}
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
