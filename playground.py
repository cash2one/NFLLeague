import nflleague

scraper=nflleague.update.Generate(203986,2016,'Firefox')
scraper.init_league()
for week in range(1,14):
    scraper.update_lineups_by_week(week,force=True)
scraper.close()
