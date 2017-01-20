import nflleague

#For fun and testing purposes, I've included example data scraped from Matthew Berry's celebrity league.
#To output the results of any matchup from any given year, say Chelsea Handler's team in week 10 of 2016:
league=nflleague.league.League(1773242,2016)
game=league.team('CHELSEA HANDLER').week(10)

print(game)
print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for plyr,opp_plyr in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%.1f\t\t%s\t%.1f'
    print(m % (plyr.slot,plyr.gsis_name,plyr.statistics().score(),opp_plyr.gsis_name,opp_plyr.statistics().score()))

#To break down the number of Fantasy points/TDs scored by WRs on Kevin Durant's team in 2016:
league=nflleague.league.League(1773242,2016)
team=league.team('KEVIN DURANT')

stats={}
for week in team.weeks():
    for plyr in week.lineup:
        if plyr.position=='WR':
            if plyr.player_id not in stats:
                stats[plyr.player_id]=plyr
            else:
                stats[plyr.player_id]+=plyr

for plyr in sorted(stats.values(),key=lambda x:x.statistics().score(),reverse=True):
    ps=plyr.statistics()
    print('%s: %.1f pts/ %i TDs' % (plyr,ps.score(),ps.receiving_tds))

#One use of NFLLeague is to aid in making informed, data-driven waiver decisions, as well as identify "sleepers".
#For example, lets look at the top 5 WR's available on waivers going in to week 6 of 2016 ordered by how many times they were targeted in week 5, and compare that to their average targets/game in weeks previous.
import numpy as np

league=nflleague.league.League(1773242,2016)

for p in league.waivers(5,pos='WR').sort(lambda x:x.statistics().receiving_tar).limit(5):
    m='%s:\tWeek 5: %i\tAve: %.2f'
    print(m % (p,p.statistics().receiving_tar,np.mean([n.receiving_tar for n in p.seasonal_stats()])))

                          
