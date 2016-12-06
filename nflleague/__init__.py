import nflgame
import nflgame.live

c_year,c_week=nflgame.live.current_year_and_week()

import nflleague.functions
import nflleague.team
import nflleague.week
import nflleague.player
import nflleague.league
import nflleague.scoring
import nflleague.schedule

players=nflleague.player._create_week_players()

from nflleague.league import Category

