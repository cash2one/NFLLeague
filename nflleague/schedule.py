import nflgame
import json

def _load_schedule(season):
    try:
        return json.loads(open('nflleague/espn-league-json/{}/schedule.json'.format(season)).read())
    except IOError:
        return()

def build_gsis_sched(c_year,c_week):
    seasons=range(2009,c_year+1)
    all_weeks=[range(1,14) for s in seasons]
    sched_gsis={'updated':(c_year,c_week)}
    for (y,weeks) in zip(seasons,all_weeks):
        sched_gsis[y]={}
        for w in weeks:
            sched_gsis[y][w]={}
            for g in nflgame.sched.games.values():
                if (g['year'],g['week']) == (y,w):
                    if g['home'] == 'JAX':
                        sched_gsis[y][w]['JAC']=g['eid']
                        sched_gsis[y][w][g['away']]=g['eid']
                    elif g['away'] == 'JAX':
                        sched_gsis[y][w][g['home']]=g['eid']
                        sched_gsis[y][w]['JAC']=g['eid']
                    else:
                        sched_gsis[y][w][g['home']]=g['eid']
                        sched_gsis[y][w][g['away']]=g['eid']
    return sched_gsis   
