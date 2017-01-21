NFLLeague is an API for ESPN Fantasy Football which harnesses the power of BurntSushi's nflgame.  By utilizing several key features of nflgame, nflleague offers league-oriented, player-focused methods for rapidly accessing a wide range of ESPN and NFL player data. NFLLeague is ideal for those who are interested in performing analysis in a league-wise fashion, researching league historical data, or accessing real-time fantasy stats and scores.

###Installation
To use this package, run the following commands to install the necessary dependencies:
```
sudo pip install nflgame selenium matplotlib scipy numpy
sudo apt-get install firefox python-levenshtein
```
Optional: To run the scraping in a virtual environment (faster scraping), install PyVirtualDisplay
```
sudo apt-get install xvfb xserver-xephyr vnc4server
sudo pip install pyvirtualdisplay
```
###Gathering Data
To gather ESPN data for your league, substitute your league information and run the following:
```python
import nflleague.update

scraper=nflleague.update.Scraper(LEAGUE_ID,SEASON,username='USERNAME',password='PASSWORD')
scraper.update_league_settings()
scraper.update_owners()
scraper.update_schedule()
for week in range(1,17):
    scraper.update_lineups_by_week(week,force=True)
scraper.close()
```
or equivalently:
```python
import nflleague.update

scraper=nflleague.update.Scraper(LEAGUE_ID,SEASON,username='USERNAME',password='PASSWORD')
scraper.scrape_league()
scraper.close()
```

It's too early to begin official documentation for NFLLeague, because I am sure there are some heavy structural changes yet to be made.  However, I'm currently working my best to document classes and functions in code to help people become accustom to how the package works.  Please address any questions in the Issue Tracker, or, for now, e-mail me at CMorton737@gmail.com.  Below I'll provide some basic usage examples, as well as in the cookbook.py

For fun and testing purposes, I've included example data scraped from Matthew Berry's celebrity league.
To output the results of any matchup from any given year, say Chelsea Handler's team in week 10 of 2016:
```python
import nflleague

league=nflleague.league.League(1773242,2016)
game=league.team('CHELSEA HANDLER').week(10)

print(game)
print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for plyr,opp_plyr in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%.1f\t\t%s\t%.1f'
    print(m % (plyr.slot,plyr.gsis_name,plyr.stats().score(),opp_plyr.gsis_name,opp_plyr.stats().score()))
```
Which gives the result:
```
HAND (150.0) vs EFRO (113.0)
TEAM HANDLER vs. TEAM EFRON
QB:     C.Newton        23.0        D.Brees         20.0
RB:     E.Elliott       40.0        J.Ajayi         8.0
RB:     T.Hightower     7.0         J.Howard        8.0
WR:     T.Williams      23.0        A.Brown         34.0
WR:     C.Beasley       8.0         J.Crowder       13.0
TE:     A.Gates         16.0        J.Graham        8.0
FLEX:   T.Gabriel       14.0        Q.Enunwa        1.0
D/ST:   Seahawks D/ST   5.0         Texans D/ST     12.0
K:      S.Hauschka      14.0        J.Tucker        9.0
```

To break down the number of Fantasy points/TDs scored by WRs on Kevin Durant's team in 2016:
```python
import nflleague

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

for plyr in sorted(stats.values(),key=lambda x:x.stats().score(),reverse=True):
    ps=plyr.stats()
    print('%s: %.1f pts/ %i TDs' % (plyr,ps.score(),ps.stats.get('receiving_tds',0)))
```

which returns:
```
Golden Tate, DET WR: 202.0 pts/ 3 TDs
Dez Bryant, DAL WR: 179.0 pts/ 8 TDs
DeSean Jackson, WAS WR: 151.0 pts/ 4 TDs
Donte Moncrief, IND WR: 20.0 pts/ 1 TDs
```

And one final teaser... 
NFLLeague can help in making informed, data-driven waiver decisions, as well as identify "sleepers".  For example, lets look at the top 5 WR's available on waivers going in to week 6 of 2016 ordered by how many times they were targeted in week 5.  We'll compare that to their average targets/game in weeks previous.

```python
import nflleague
import numpy as np

league=nflleague.league.League(1773242,2016)

for p in league.waivers(5,pos='WR').sort(lambda x:x.stats().receiving_tar).limit(5):
    m='%s:\tWeek 5: %i\tAve: %.2f'
    print(m % (p,p.stats().receiving_tar,np.mean([n.receiving_tar for n in p.seasonal_stats()])))
```
Which gives the following:

```
Jeremy Kerley, SF WR:       Week 5: 13  Ave: 8.00
Cameron Meredith, CHI WR:   Week 5: 12  Ave: 2.00
Brandon LaFell, CIN WR:     Week 5: 11  Ave: 5.25
Eddie Royal, CHI WR:        Week 5: 9   Ave: 5.50
Jaelen Strong, HOU WR:      Week 5: 9   Ave: 2.75
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

