NFLLeague is an API for ESPN Fantasy Football which harnesses the power of [BurntSushi](https://github.com/BurntSushi)'s nflgame.  By utilizing several key features of nflgame, nflleague offers league-oriented, player-focused methods for rapidly accessing a wide range of ESPN and NFL player data. NFLLeague is ideal for those who are interested in performing analysis in a league-wise fashion, researching league historical data, or accessing real-time fantasy stats and scores.

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

league=nflleague.league.League(203986,2015)
game=league.team('CHAD MORTON').week(4)

print('%s vs. %s' % (game.team_name,game.opponent().team_name))
for p,op in zip(game.lineup,game.opponent().lineup):
    m='%s:\t%s\t%.1f\t\t%s\t%.1f'
    print(m % (p.slot,p.gsis_name,p.statistics().score(),op.gsis_name,op.statistics().score()))
print('%s %s %.1f-%.1f' % (game.team_name,'win' if game.win() else 'lose',game.get_score(),game.opponent().get_score()))
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

###Check Out Some Project Examples!
Here are just two examples of how I have used NFLLeague to generate reports within my own Fantasy league.  These examples highlight 
some of the features and capabilities of NFLLeague:

   Every week, I post a LIVE infographic, which I call "Weekly Matchup Showcase".  It is a general but detailed look 
   at real-time scoring, information, and statistics in a head-to-head format.  I use APScheduler to schedule lineup 
   and projection updates all throughout the week.  While games are being played, NFLLeague's ability to rapidly access data
   allows updated reports to be generated and posted as often as every 15 seconds. Here is a 
   [recent example](http://cs.iusb.edu/~chmorton/WMS123456201614.png) taken after the Sunday games.

   [Here](http://cs.iusb.edu/~chmorton/ScoringReport123456201613.png) is a basic report where I break down the scoring of each 
   individual team by week and by opponent.

   Code to generate these reports is available upon request.  

###Help Wanted!
NFLLeague is a work in progress, and I am always looking for contributors to help test, improve, and expand the functionality of this package.  My background is in numerical analysis and statistics, so professional and/or highly skilled programmers are desired to help sure up and optimize the code.

###Current Issues/Public TODO List
There are several aspects of NFLLeague that I would like assistance in improving.

####Scraping Expert Projections/Scraping Method in General
In attempting to expand programmatic access to expert projection data, one bottleneck that I have encountered is the speed in which I can scrape data from projection sources using python and selenium.  I chose Selenium for this project for the sake of uniformity and simplicity of having the package exclusively Python, but due to the length of time it takes to gather projection data from just three sources(ESPN,CBS,Fantasy Pros), it'd be best to find a more efficient method. 

What's been tried:
  * Multithreading to scrape multiple sources at once. Biggest improvement, but still slow and burdensome on resources
  * Using headless browser PhantomJS.  Due to known issues with trying to use PhantomJS and Selenium together, I 
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

