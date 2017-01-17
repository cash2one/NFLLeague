NFLLeague is an API for ESPN Fantasy Football which harnesses the power of BurntSushi's nflgame.  By utilizing several key features of nflgame, nflleague offers league-oriented, player-focused methods for rapidly accessing a wide range of ESPN and NFL player data. NFLLeague is ideal for those who are interested in performing analysis in a league-wise fashion, researching league historical data, or accessing real-time fantasy stats and scores.

To gather ESPN data for your league, substitute your league information and run the following:
```python
import nflleague.update

current_week=5
league_id=123456
season=2015
scraper=nflleague.update.Generate(league_id,season,'firefox',private=True,visible=False)
scraper.update_league_settings()
scraper.update_owners()
scraper.update_schedule()
for week in range(1,current_week+1):
    scraper.update_lineups_by_week(week,force=True)

#scrape projection data if needed.
scraper.scrape_projections(current_week)
scraper.close()
```
or equivalently:
```python
import nflleague.update

league_id=123456
season=2015
scraper=nflleague.update.Generate(league_id,season,'firefox',private=True,visible=False)
scraper.init_league()

#scrape projection data if needed.
scraper.scrape_projections()
scraper.close()
```

It's too early to begin official documentation for NFLLeague, because I am sure there are some heavy structural changes yet to be made.  However, I'm currently working my best to document classes and functions in code to help people become accustom to how the package works.  Please address any questions in the Issue Tracker, or, for now, e-mail me at CMorton737@gmail.com.  Below I'll provide some basic usage examples, as well as in the cookbook.py

To output the results of any given week from any given year, say my team in week 4 of the 2015 season:
```python
import nflleague

league=nflleague.league.League(123456,2015)
game=league.team('CHAD MORTON').week(6)

print(game)
print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for plyr,opp_plyr in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%.1f\t\t%s\t%.1f'
    print(m % (plyr.slot,plyr.gsis_name,plyr.statistics().score(),opp_plyr.gsis_name,opp_plyr.statistics().score()))
```
Which gives the result:
```
CHOP (124.4) vs WISE (104.1)
THE LOG CHOPPERZ vs. WYNNEDALE WINERY DINERY
QB:     A.Luck          27.9    B.Bortles       22.9
RB:     L.Bell          8.8     E.Lacy          2.4
RB:     R.Hillman       12.1    M.Ingram        18.2
WR:     A.Green         4.4     J.Edelman       12.4
WR:     K.Allen         18.5    D.Moncrief      14.1
TE:     M.Bennett       7.1     A.Gates         11.3
FLEX:   B.Marshall      16.5    T.Hilton        14.6
D/ST:   Broncos D/ST    18.0    Lions D/ST      -1.0
K:      P.Dawson        11.1    S.Hauschka      9.2
```

To break down the number of Fantasy points/TDs scored by WRs on my team in 2015:
```python
import nflleague

league=nflleague.league.League(123456,2015)
team=league.team('CHAD MORTON')

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
    print('%s: %.1f pts/ %i TDs' % (plyr,ps.score(),ps.stats.get('receiving_tds',0)))
```

which returns:
```
Brandon Marshall, NYJ WR: 164.6 pts/ 10 TDs
Keenan Allen, SD WR: 93.9 pts/ 3 TDs
A.J. Green, CIN WR: 88.5 pts/ 4 TDs
Martavis Bryant, PIT WR: 65.9 pts/ 3 TDs
Kendall Wright, TEN WR: 15.0 pts/ 1 TDs
Golden Tate, DET WR: 9.7 pts/ 0 TDs
```

And one final teaser... 
NFLLeague can help in making informed, data-driven waiver decisions, as well as identify "sleepers".  For example, lets look at the top 5 WR's available on waivers going in to week 6 of 2015 ordered by how many times they were targeted in week 5.  We'll compare that to their average targets/game in weeks previous.

```python
import nflleague
import numpy as np

league=nflleague.league.League(123456,2015)

for p in league.waivers(5,pos='WR').sort(lambda x:x.statistics().receiving_tar).limit(5):
    m='%s:\tWeek 5: %i\tAve: %.2f'
    print(m % (p,p.statistics().receiving_tar,np.mean([n.receiving_tar for n in p.seasonal_stats()])))
```
Which gives the following:

```
Golden Tate, DET WR:        Week 5: 18  Ave: 7.25
Anquan Boldin, SF WR:       Week 5: 12  Ave: 6.50
Travis Benjamin, CLE WR:    Week 5: 12  Ave: 6.75
Willie Snead, NO WR:        Week 5: 11  Ave: 5.50
Allen Robinson, JAC WR:     Week 5: 9   Ave: 9.75
```


###Check Out Some Project Examples!
Here are a few examples of some of the ways that I've used NFLLeague within my own Fantasy league:

   Every week, I post a LIVE infographic, which I call "Weekly Matchup Showcase".  It is a general but detailed look 
   at real-time scoring, information, and statistics in a head-to-head format.  I use APScheduler to schedule lineup 
   and projection updates all throughout the week, and on gamedays, NFLLeague's ability to rapidly access statistics 
   allows updates to be posted as often as every 15 seconds. Here is a [recent example.](http://cs.iusb.edu/~chmorton/WMS123456201614.png)

   [Here](http://cs.iusb.edu/~chmorton/ScoringReport123456201613.png) is another report detailing the scoring breakdown and statistics for the 2016 season per team


###Help Wanted
NFLLeague is a work in progress, and I am always looking for contributors to help test, improve, and expand the functionality of this package.  My background is in mathematics/statistics, so professional and/or highly skilled programmers are desired to help sure up and optimize the code.

###Current Issues/Public TODO List
There are several aspects of NFLLeague that I would like assistance in improving.

####Scraping Expert Projections/Scraping Method in General
In attempting to expand programmatic access to expert projection data, one bottleneck that I have encountered is the speed in which I can scrape data from projection sources using python and selenium.  I chose Selenium for this project for the sake of uniformity and simplicity of having the package exclusively Python, but due to the length of time it takes to gather projection data from just three sources(ESPN,CBS,Fantasy Pros), it'd be best to find a more efficient method. 

What's been tried:
  * Multithreading to scrape multiple sources at once. Biggest improvement, but still slow and burdensome on resources
  * Using headless browser PhantomGS.  Due to known issues with trying to use PhantomGS and Selenium together, I 
   found it to be unuseable.  Someone more knowledgeable with Selenium may be able find a work around. But I'm leaning
   towards abandoning Selenium all together.

Ideas:
  * I have had seen some improvement while experimenting with using R or Google Sheets to scrape. One route that may 
   be worth exploring further is to use the Google Sheets API to write a background script that manages what projection 
   sites Google needs to scrape and when.  This would export the workload entirely to Google, keep the package Python, 
   and give quick access via API to up-to-date projections without having to run a 'scrape_projections.py' function locally.
  * R has quick and efficient methods for scraping data.  Consider this a last resort.

If we can improve scraping speed of projections in such a way that would integrate nicely into the package as a whole, we might apply it to the rest of the scraping functions in nflleague.update.

Any other ideas? See Issue Tracker for discussion.

####Adding Yahoo Fantasy Sports Functionality
While it sounds difficult, this would just be a weekend project for someone who wants to create the scraping functions that pull data from Yahoo and save it in a format identical to existing ESPN data.  I personally don't use Yahoo so I have never had the need to do it, but doing so would ultimately allow for more fantasy players to use and help support this package.

