import nflgame
import nflgame.live

c_year,c_week=nflgame.live.current_year_and_week()

import nflleague.functions
import nflleague.team
import nflleague.week
import nflleague.player
import nflleague.league
import nflleague.scoring
import nflleague.schedule
import nflleague.seq
from nflleague.league import Category

players=nflleague.player._json_week_players()

def gen_players_week(league_id,season,week):
    def gen():
        for pid,plyr in players.iteritems():
            try:
                if plyr['schedule'][str(season)][str(week)]!='bye':
                    yield nflleague.player.FreeAgent(league_id, season, week, pid)
            except KeyError:
                continue
    return nflleague.seq.GenPlayer(gen())
    

def standard_team_id(league_id,season,team_iden):
    #Converts any team identifier(i.e. team name or owner or abv) to the team number
    for k,v in nflleague.league._json_load_owners(league_id,season).iteritems():
        if str(team_iden).lower() in map(lambda x:str(x).lower(),v.values()):
            return str(k)


