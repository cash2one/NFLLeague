from collections import OrderedDict
import heapq
import Levenshtein

import nflgame
import json
import os

def check_file(filepath):
    folder='/'.join(filepath.split('/')[:-1])
    if not os.path.exists(folder):
        os.makedirs(folder)

def get_json(filepath,dtype):
    try:
        item=json.loads(open(filepath).read())
    except:
        check_file(filepath)
        item=dtype 
    return item
    
def save_json(filepath,data):
    check_file(filepath)
    with open(filepath,'w') as out:
        json.dump(data,out,indent=4,separators=(',',': '))
    out.close()

#DEPRECATED
#assigns correct team to a player.   Need this for historical data to account for traded players.  Could probably do this 
#in nflleague.update.get_id... Caches corrected team for fast recovery since nflgame.game is semi expensive
def correct_team(player_id,season,week):
    print('IN DEPRECATED FUNCTION')
    filename='nflleague/espn-league-json/cached/teamcorrections.json'
    teams={}
    print(player_id)
    if os.path.isfile(filename):
        teams=json.loads(open(filename).read())
    try:
        return teams['{}{}'.format(player_id,season)]
    except KeyError:
        try:
            games=nflgame.games(season,week)
            stats=list(nflgame.combine_play_stats(games).filter(playerid=player_id))[0]
            teams['{}{}'.format(player_id,season)]=stats.team
            with open(filename,'w') as out:
                json.dump(teams,out,indent=4,separators=(',',': '))
            out.close()
            return stats.team
        except IndexError:
            print(player_id)

def standard_position(pos):
    pos = pos.upper()
    if pos in ('QB', 'RB', 'WR', 'K', 'P','TE'):
        return pos
    if pos == 'FB':
        return 'RB'
    return 'DEF'

def standard_name(player):
    if player.player is not None:
        return player.player.name.lower()
    else:
        return player.name.lower()

def shrink_name(name):
    first, rest = name.split(' ', 1)
    return '%s.%s' % (first[0], rest)

def ratio(n1, n2):
    return Levenshtein.ratio(unicode(n1.lower()), unicode(n2.lower()))

def edit_name(p, name):
    if p.player is not None:
        return ratio(p.player.name, name)
    else:
        name = shrink_name(name)
        if p.name[0].lower() != name[0].lower():
            return 0.0
        return ratio(p.name, name)
    
def find(name, season, team=None, pos=None,players=None):
    if players==None:
        players = nflgame.combine_game_stats(nflgame.games_gen(int(season)))
    indexed={}
    for p in players:
        indexed[p.playerid] = p
    if pos is not None:
        pos = standard_position(pos)

    result = []
    for pid, p in indexed.iteritems():
        if pos is not None and pos != standard_position(p.guess_position):
            continue

        r = edit_name(p, name)
        if r >= 0.8:
            result.append((r, pid))
    if len(result) == 0:
        return None

    result = heapq.nlargest(1, result)
    if team is not None and result[0][0] < 0.85:
        sameteam = lambda (r, pid): \
            nflgame.standard_team(team) == indexed[pid].team
        result = filter(sameteam, result)
        if len(result) == 0:
            return None
    #may need to for return of player object
    return nflgame.players[result[0][1]]
"""
def gen_rosters(season=None):
    if season == None:
        season = range(2009,nflgame.live.current_year_and_week()[0])
        print(season)
    elif type(season) == int:
        season=list(season)

    for year in season: 
        games = nflgame.games(year)

        players = nflgame.combine(games)
        positions = set([p.player.position for p in players if p.player.position])

        # Sets up some empty dictionaries for each team to hold all of the positions
        teams = nflgame.teams
        team_rosters = {}
        for team in teams:
            team_rosters[team[0]] = {}
            for position in positions:
                team_rosters[team[0]][position] = []
            # There are going to be a lot of players that are no longer in the league
            # aka don't have a position available in metadata
            team_rosters[team[0]]['UNK'] = []

        plays = nflgame.combine_plays(games)
        for play in plays:
            for player in play.players:
                # PEP8 4EVA
                p, pp = player, player.player
                if pp.position:
                    if pp.full_name not in team_rosters[p.team][pp.position]:
                        team_rosters[p.team][pp.position] += [pp.full_name]
                else:
                    if pp.full_name not in team_rosters[p.team]['UNK']:
                        team_rosters[p.team]['UNK'] += [pp.full_name]

        for team in teams:
            print '\n{} roster {}'.format(team[3], year)
            print '-'*79
            for position in team_rosters[team[0]]:
                if team_rosters[team[0]][position]:
                    print '{:3}:\t{}'.format(position, ',\t'.join(team_rosters[team[0]][position]))
"""
