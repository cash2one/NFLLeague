import nflgame
import json
import collections
from nflleague.functions import get_json,save_json

def load_schedule_info(season,week,team):
    #Condition to deal with game.schedule.home='JAX' but game.data.home='JAC' in 2016 week 1
    team='JAX' if int(season)==2016 and int(week)==1 and team in ['JAC','JAX'] else team
    game_info=nflgame._search_schedule(int(season),int(week),home=team,away=team,kind='REG')
    if len(game_info) == 0:
        return 'bye'
    if len(game_info) == 1:
        return game_info[0]['eid']

def guess_pos(plyr):
    if plyr.player != None:
        if plyr.player.position != '':
            return plyr.player.position
        else:
            stats= [(plyr.passing_att, 'QB'),
                    (plyr.rushing_att, 'RB'),
                    (plyr.receiving_tar, 'WR'),
                    (plyr.defense_tkl, 'DEF'),
                    (plyr.defense_ast, 'DEF'),
                    (plyr.kicking_tot, 'K'),
                    (plyr.kicking_fga, 'K'),
                    (plyr.punting_tot, 'P')]
            return sorted(stats, reverse=True)[0][1]
    try:
        position=plyr.guess_position
        if position in ['',None]:
            position='UNKNOWN POS'
    except Exception as err:
        print(err)
        position='UNKNOWN POS'
    return position

def identity_player():
    iden={"00-0000000": {
              "birthdate": "1/1/1900",
              "college": "None",
              "first_name": "N/A",
              "full_name": "Not Available",
              "gsis_id": "00-0000000",
              "gsis_name": "N.A.",
              "height": 0,
              "last_name": "N/A",
              "number": 0,
              "position": {},
              "profile_id": 000000,
              "profile_url": "http://www.nfl.com/",
              "team": {},
              "schedule":{},
              "weight": 0,
              "years_pro": 0}}
    return iden

#TODO Give function capability to skip over weeks and seasons that have already been accounted for
def generate_week_players():
    s,w=nflgame.live.current_year_and_week()

    week_players=get_json('nflleague/players.json',identity_player())
    nflgame_players=get_json(nflgame.player._player_json_file,{})
    if len(week_players)==1:
        for pid,plyr in nflgame_players.iteritems():
            if plyr.get('team',False):
                plyr['team']={str(s):{str(w):plyr.get('team','NUTTIN')}}
                plyr['position']={str(s):{str(w):plyr.get('position','NONE')}}
            else:
                plyr['position']={}
                plyr['team']={}
            plyr['schedule']={}
            plyr['gsis_name']='.'.join([plyr['first_name'][0],plyr['last_name']])
            week_players[pid]=plyr
    
    for season in range(2016,s+1):
        for week in range(1,18):
            if (season,week) == (s,w):
                break
            
            print(season,week)
            if str(season) in week_players['00-0000000']['team'].keys():
                if str(week) in week_players['00-0000000']['team'][str(season)].keys():
                    continue
                    print('S:{}  W:{} passed'.format(season,week))
                else:
                    week_players['00-0000000']['team'][str(season)][str(week)]='NA'
                    week_players['00-0000000']['position'][str(season)][str(week)]='NA'
            else:
                week_players['00-0000000']['team'][str(season)]={str(week):'NA'}
                week_players['00-0000000']['position'][str(season)]={str(week):'NA'}

            games=nflgame.games(season,week=week)
            players=nflgame.combine_max_stats(games) 
            for plyr in players:
                team=nflgame.standard_team(plyr.team)
                if plyr.player!=None:
                    position=guess_pos(plyr)
                    if str(season) not in week_players[plyr.playerid]['team'].keys():
                        week_players[plyr.playerid]['team'][str(season)]={str(week):team}
                        week_players[plyr.playerid]['position'][str(season)]={str(week):position}
                    else:
                        week_players[plyr.playerid]['team'][str(season)][str(week)]=team
                        week_players[plyr.playerid]['position'][str(season)][str(week)]=position

        #Fill in any unknown team weeks with most likely correct team
        for pid,plyr in week_players.iteritems():
            if type(plyr['team'])==dict and str(season) not in plyr['team'].keys():
                continue
            if plyr.get('position','')=='D/ST':
                continue
            
            #Only 1 position per season, so find most commonly guessed position and set to all games.  For now
            count=collections.Counter()
            for pos in plyr['position'][str(season)].values():
                count[pos]+=1
            position=sorted(count.items(),key=lambda x:x[1],reverse=True)[0][0]
            for i in range(1,18):
                plyr['position'][str(season)][str(i)]=position
            
            #Fill in Teams
            act=[]
            for week in range(1,18):
                if str(week) in plyr['team'][str(season)].keys():
                    act.append(plyr['team'][str(season)][str(week)])
                else:
                    act.append(False)
            #Dont forget about the knile davis situation     
            if not act[0]:
                T,index=False,0
                while(not T):
                    T=act[index]
                    index+=1
                act[0]=T
                plyr['team'][str(season)]['1']=T
            
            for i,team_week in enumerate(act,start=1):
                if not team_week:
                    plyr['team'][str(season)][str(i)]=plyr['team'][str(season)][str(i-1)]
            week_players[pid]=plyr

        #Build Defenses.  Defenses will have constant team and position
        for did in nflgame.teams:
            if did[0] not in week_players:
                week_players[did[0]]={
                          "first_name": did[1],
                          "full_name": did[3],
                          "gsis_id": did[0],
                          "gsis_name": ' '.join([did[2],'D/ST']),
                          "last_name": did[2],
                          "position": "D/ST",
                          "profile_url": "http://www.nfl.com/",
                          "team": did[0],
                          "schedule":{},
                          "status":'ACT'}
        
        length=len(week_players)

        #Build game_eid dictionary
        for i,(pid,plyr) in enumerate(week_players.iteritems()):
            if type(plyr['team'])==dict and str(season) not in plyr['team'].keys():
                #skip players who weren't statistically active
                continue
            week_players[pid]['schedule'][str(season)]={}
            print(pid,plyr['full_name'],'{}%'.format(round((float(i)/length)*100,2)))
            for week in range(1,18):
                if plyr.get('position')!='D/ST':
                    team=week_players[pid]['team'][str(season)][str(week)]
                else:
                    team=week_players[pid]['team']
                week_players[pid]['schedule'][str(season)][str(week)]=load_schedule_info(season,week,team)
    
    save_json('nflleague/players.json',week_players)

