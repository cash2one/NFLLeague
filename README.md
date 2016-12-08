NFLLeague is an API for ESPN Fantasy Football which harnesses the power of BurntSushi's nflgame.  By utilizing several key features of nflgame, nflleague offers league-oriented, player-focused methods for rapidly accessing a wide range of ESPN and NFL player data. NFLLeague is ideal for those who are interested in performing analysis in a league-wise fashion, researching league historical data, or accessing real-time fantasy stats and scores.

To output the results of any given week from any given year, say my team in week 4 of the 2015 season:
```python
import nflleague

league=nflleague.league.League(203986,2015)
game=league.team('CHAD MORTON').week(4)

print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for plyr,opp_plyr in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%f\t\t%s\t%f'
    print(m % (plyr.slot,plyr.gsis_nam,plyr.statistics().score(),opp_plyr.gsis_name,opp_plyr.statistics().score()))
print('%s %s %f-%f' % (game.team_name,'win' if game.win() else 'lose',game.get_score(),game.opponent().get_score()))
```
Which gives the result:
```
THE LOG CHOPPERZ vs. THE BAY AREA BEAUTIES
QB:     D.Brees         22.2        P.Manning       8.2
RB:     L.Bell          22.4        M.Lynch         0.0
RB:     J.Randle        8.6         L.Murray        4.7
WR:     A.Green         9.6         C.Johnson       5.0
WR:     B.Marshall      14.2        D.Hopkins       17.5
TE:     M.Bennett       16.5        J.Witten        6.5
FLEX:   K.Allen         14.0        R.Matthews      1.8
D/ST:   Broncos D/ST    9.0         Seahawks D/ST   3.0
K:      P.Dawson        2.0         J.Tucker        10.2
THE LOG CHOPPERZ win 118.5-60.9
```
