import nflleague

league=nflleague.league.League(203986,2015)
game=league.team('CHAD MORTON').week(4)

print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for plyr,opp_plyr in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%s\t\t%s\t%s'
    print(m % (plyr.slot,plyr.gsis_name,plyr.statistics().score(),opp_plyr.gsis_name,opp_plyr.statistics().score()))
print('%s %s %s-%s' % (game.team_name,'win' if game.win() else 'lose',game.get_score(),game.opponent().get_score()))


                            