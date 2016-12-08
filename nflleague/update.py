from __future__ import print_function

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as WDW
from time import sleep
import os
import json
import re
import random
from pyvirtualdisplay import Display
from os import walk
import urllib
import cv
import numpy as np
import nflgame
from datetime import datetime
import nflleague
import collections
#DONE finish settings/scoring scrape (HIGH)
#TODO make a separte scrape file for all the projection scraping functions. or make a bunch of indiviual programs and 
#use multithreading to simply run each program.  Need to research resource usage of scraping, or consider using
# other means for faster projection scraping.  maybe R or Google Sheets?
# Maybe use multithreading for scraping entire week at one time?  Need some way to speed up scraping process

PLAYERS=nflgame.player._create_players()
TEAMS=[i[2] for i in list(nflgame.teams)]
ACTIVES=['QB','RB','WR','TE','FLEX','D/ST','K']

ESPN_SCORING_MAP={'PY':'passing_yds','PTD':'passing_tds','INT':'interception','2PC':'passing_twoptm','P300':'passing_yds_300',
              'P400':'passing_yds_400','RY':'rushing_yds','RTD':'rushing_tds','2PR':'rushing_twoptm','RY100':'rushing_yds_100',
              'RY200':'rushing_yds_200','REY':'receiving_yds','RETD':'receiving_tds','2PRE':'receiving_twoptm',
              'REY100':'receiving_yds_100','REY200':'receiving_yds_200','KRTD':'kickret_tds','PRTD':'puntret_tds',
              'FTD':'fumbles_frec_tds','FUML':'fumbles_lost','SK':'defense_sk','INTTD':'defense_int_tds',
              'FRTD':'defense_frec_tds','BLKKRTD':'defense_blkkrtd','BLKK':'defense_blkk','FR':'defense_frec',
              'SF':'defense_safe','PA0':'defense_PA_0','PA1':'defense_PA_1_6','PA7':'defense_PA_7_13','PA14':'defense_PA_14_17',
              'PA18':'defense_PA_18_21','PA22':'defense_PA_22_27','PA28':'defense_PA_28_34','PA35':'defense_PA_35_45',
              'PA46':'defense_PA_46','YA100':'defense_YA_99','YA199':'defense_YA_199','YA299':'defense_YA_299',
              'YA349':'defense_YA_349','YA399':'defense_YA_399','YA449':'defense_YA_449','YA499':'defense_YA_499',
              'YA549':'defense_YA_549','YA550':'defense_YA_550','PAT':'kicking_xpmade','PATM':'kicking_xpmissed',
              'FG0':'kicking_fgm_0_39','FGM':'kicking_fgmissed','FG40':'kicking_fgm_40_49','FG50':'kicking_fgm_50_100',
              'FGM0':'kicking_fgmissed_0_39','PY5':'passing_yds_py5','REC':'receiving_rec','KR25':'kickret_yds',
              'PR25':'puntret_yds'}

class Page(webdriver.Firefox):
    def __init__(self, browser):
        if browser.lower() == "firefox":
            pro = webdriver.FirefoxProfile()
            pro.set_preference("http.response.timeout", 5)
            pro.set_preference("dom.max_script_run_time", 5)
            webdriver.Firefox.__init__(self,firefox_profile=pro)

class Generate():
    def __init__(self,league_id,season,browser,private=False,visible=True):
        print("Season {}".format(season))
        if visible==False:
            print('Starting Virtual Environment',end='\r')
            self.display=Display(visible=0,size=(200,200))
            self.display.start()
            print('Virtual Environment Established')

        self.visible=visible
        self.browser=Page(browser)
        self.season=season
        self.current_season,self.current_week=nflgame.live.current_year_and_week()
        self.league_id=league_id
        self.owners=dict
        self.player_game=nflgame.combine_game_stats(nflgame.games_gen(int(self.season)))
        if private:
            print('Signing in to ESPN.com',end='\r')
            self.browser.get("http://games.espn.go.com/ffl/signin")
            sleep(3)
            self.browser.switch_to.frame(self.browser.find_element_by_name("disneyid-iframe"))
            self.browser.find_element_by_xpath("//input[@placeholder='Username or Email Address']").\
                                                                                            send_keys(raw_input("Username: "))
            self.browser.find_element_by_xpath("//input[@placeholder='Password (case sensitive)']").\
                                                                                            send_keys(raw_input("Password: "))
 
            #self.browser.find_element_by_xpath("//input[@placeholder='Username or Email Address']").\
            #                                                                                send_keys('username')
            #self.browser.find_element_by_xpath("//input[@placeholder='Password (case sensitive)']").\
            #                                                                                send_keys('password')
            self.browser.find_element_by_xpath("//button[@type='submit']").click()
            sleep(5)
            print('Logged in to ESPN.com          ')
    
        filename='nflleague/espn-league-json/{}/{}/owner_info.json'.format(self.league_id,self.season)
        if os.path.isfile(filename):
            self.owners=json.loads(open(filename).read())
        else:
            print('No Owner Info Available. Must generate first')

    def __home(self,season=None):
        #navigate to ESPN league office for desired season
        if season != None:
            self.season=season
        try:
            fpath='http://games.espn.go.com/ffl/leagueoffice?leagueId={}&seasonId={}'.format(self.league_id,self.season)
            self.browser.get(fpath)
            sleep(5)
            return True
        except:
            return False
    def init_league(self):
        self.update_league_settings()
        self.update_owners()
        self.update_schedule()
        for week in range(1,self.current_week+1):
            self.update_lineups_by_week(week,force=True)

    def update_owners(self):
        """
        Scrapes ESPN Fantasy Football website for owner information and generates a json file
        of info to be assigned to league object by create_team function
        """
        print('Gathering Owner Information',end='\r')
        filename='nflleague/espn-league-json/{}/{}/owner_info.json'.format(self.league_id,self.season)
        check_dir(filename)
        
        self.__home()
        #navigate to members for scraping owner name/team name information
        #Gathers team_num/team_abv/team_name/Division/Owner
        
        self.browser.get('http://games.espn.go.com/ffl/leaguesetup/ownerinfo?leagueId={}'.format(self.league_id))
        sleep(5)
        
        owner_info={}
        for team in self.browser.find_elements_by_class_name('ownerRow'): 
            currentInfo={}
            if team.text!='':
                try:    
                    temp=[u2a(name.text).upper() for name in team.find_elements_by_tag_name('td') \
                                                               if (name.text not in ['','Joined','Send Email','Add 2nd Owner'])]
                    currentInfo['team_abv']=temp[1]
                    currentInfo['team_name']=temp[2]
                    currentInfo['team_div']=temp[3]
                    currentInfo['team_owner']=temp[4]
                   
                    idString=team.find_element_by_class_name('teamName').find_element_by_tag_name('a').get_attribute('href')
                    currentInfo['team_id']=int(re.search('{}(.*){}'.format('teamId=','&seasonId'),idString).group(1))
                    owner_info[currentInfo['team_id']]=currentInfo
                except IndexError:
                    pass
        print("Owner Information Gathered           ") 
        with open('nflleague/espn-league-json/{}/{}/owner_info.json'.format(self.league_id,self.season),'w') as out:
            json.dump(owner_info,out,indent=4,sort_keys=True, separators=(',',': '),ensure_ascii=True)
        self.owners=owner_info
        return True

    def update_lineups_by_week(self,week,force=False):
        #self.__home()
        #Scrapes ESPN Fantasy league to gather all lineups for the week
        lineups={}
        filename='nflleague/espn-league-json/{}/{}/lineup_by_week.json'.format(self.league_id,self.season)
        if os.path.isfile(filename):
            lineups=json.loads(open(filename).read())
            lineups.pop('updated')
            if str(week) in lineups.values()[0].keys() and not force:
                print('Week {} Skipped'.format(week))
                return False
            elif str(week) in lineups.values()[0].keys() and force:
                for w in lineups.values():
                    w.pop(str(week))
        else:
            check_dir(filename)
            lineups={k:{} for k in self.owners.keys()}
        
        #Try to get image for team.  Expection raise if image link cant be traced.  Replaced with default image on load by 
        #nflleague.league
        for team in lineups.keys():
            print("**************SEASON {} WEEK {} TEAM {}**************".format(self.season,week,team))
            address='http://games.espn.com/ffl/boxscorequick?leagueId={}&teamId={}&scoringPeriodId={}&seasonId={}'\
                                                                                    .format(self.league_id,team,week,self.season)
            address="{}{}".format(address,'&view=scoringperiod&version=quick')
            self.browser.get(address)
            #if self.current_season:
            if True==True:
                try: 
                    xpath="//div/a[@href='/ffl/clubhouse?leagueId={}&teamId={}']".format(self.league_id,team)
                    WDW(self.browser,5).until(EC.element_to_be_clickable((By.XPATH,xpath)))

                    logo_address=self.browser.find_element_by_xpath(xpath).find_element_by_tag_name('img').get_attribute('src')
                    ss_path='{}/logos/{}.{}'.format('/'.join(filename.split('/')[:-1]),team,logo_address.split('.')[-1])
                    check_dir(ss_path)
                    urllib.urlretrieve(logo_address,ss_path)
                    try:
                        logo=cv.LoadImage(ss_path,True)
                        out=cv.CreateImage((500,500),logo.depth,3)
                        cv.Resize(logo,out)
                        out_path=ss_path.split(".")[0]
                        print(out_path)
                        cv.SaveImage('{}.jpg'.format(out_path),out)
                    except:
                        os.remove(ss_path)
                except Exception as err:
                    print(err)
            #Get players in lineup
            lineups[team][week]=[] 
            #eventually make actives list of positions from settings
            actives=['QB','RB','RB','WR','WR','TE','FLEX','D/ST','K']
            table=self.browser.find_element_by_css_selector('.playerTableTable.tableBody')
            for player in table.find_elements_by_tag_name('tr'): 
                playerRow=player.find_elements_by_tag_name('td')
                if len(playerRow) > 3 and playerRow[0].text not in ['STARTERS','PLAYER, TEAM POS','SLOT','TOTAL']:
                    if playerRow[0].text in actives:
                        lineups[team][week].append([playerRow[0].text,playerRow[1].text,playerRow[-1].text])
                        print(lineups[team][week][-1])
                    else:
                        slot=(playerRow[0].text).split(' ')[-1]
                        pNp=[slot,playerRow[0].text,playerRow[-1].text]
                        lineups[team][week].append(pNp)
                        print(lineups[team][week][-1])
            try:
                #check for bench.  Will be present for current season, but not for previous seasons
                WDW(self.browser,5).until(EC.element_to_be_clickable((By.LINK_TEXT,"Show Bench"))).click()
                table=self.browser.find_element_by_css_selector('.playerTableTable.tableBody.hideableGroup')
                for player in table.find_elements_by_tag_name('tr'): 
                    playerRow=player.find_elements_by_tag_name('td')
                    if len(playerRow) > 3 and playerRow[0].text != 'SLOT':
                        lineups[team][week].append([playerRow[0].text,playerRow[1].text,playerRow[-1].text])
                        print(lineups[team][week][-1])
            except Exception as err:
                print('No Bench Infomation Found')
                
            
            #Filter from [[pos,[fname,lname,team,pos],score,bye],...] via get_id_from_name() to [pos,playerId,score,bye]
            #players=json.loads(open(nflgame.player._player_json_file).read())
            def get_condition(ptp):
                ptp=filter(lambda x: x!='',re.split(",| ",ptp.replace('*','')))
                return ptp[-1] if ptp[-1] in ['O','Q','P','SSPD','IR'] else 'H'
            
            team_week=[]
            #Replace player name with player id for lookup once called in nflleague.week and get current condition
            slots_gsis={'QB':['QB'],'RB':['RB1','RB2','FLEX'],'WR':['WR1','WR2','FLEX'],'FLEX':['FLEX'],
                    'TE':['TE','FLEX'],'D/ST':['D/ST'],'K':['K'],'Bench':['Bench' for i in range(0,6)],'IR':['IR']}
            for item in filter(lambda x:x!=[] and x[0] in slots_gsis.keys(),lineups[team][week]):
                try:
                    ptp=filter_ptp(item[1])
                    print(ptp)
                    team_week+=[{'slot': item[0],
                                 'gsis_slot':slots_gsis[item[0]].pop(0),
                                 'position':ptp[2],
                                 'team':ptp[1],
                                 'player_id':self.get_id_from_name(ptp),
                                 'score': 0 if item[-1] == '--' else item[-1],
                                 'condition': get_condition(item[1])}]
                    if team_week[-1]['player_id'] == None:
                        print('\t\t{} Failed. No match found for {}'.format(item[1], item))
                except IndexError:
                    print("\t\t\t{} Empty".format(item[0]))
            lineups[team][week]={tw['gsis_slot']:tw for tw in team_week if tw['slot']!='Bench'}
            lineups[team][week]['Bench']=[tw for tw in team_week if tw['slot']=='Bench']
        now=datetime.now()
        lineups['updated']='{}/{} {}:{}'.format(now.month,'0{}'.format(now.day) if now.day<10\
                                            else now.day, now.hour,'0{}'.format(now.minute) if now.minute < 10 else now.minute)
        
        if os.path.isfile(filename):
            os.remove(filename) 
        
        with open(filename,'w') as out:
            out.seek(0)
            json.dump(lineups,out,indent=4,sort_keys=True,separators=(',',': '),ensure_ascii=True)
        out.close()
        return True

    def update_schedule(self):
        print('Updating {} Schedule'.format(self.season))
        filename='nflleague/espn-league-json/{}/{}/schedule.json'.format(self.league_id,self.season)
        check_dir(filename)

        self.__home()
        address='http://games.espn.com/ffl/schedule?leagueId={}'.format(self.league_id)
        self.browser.get(address)
        sleep(5)
                
        schedule={}
        schedule_table=self.browser.find_element_by_class_name('tableBody')
        #schedule={1:[[11,3], ... ],2:[[4,6]...],...}
        for row in schedule_table.find_elements_by_tag_name('tr'):
            try:
                if row.text.split(" ")[3] == 'PLAYOFFS':
                    break
            except IndexError:
                pass
            if row.get_attribute('class')=='tableHead':
                current_week=row.text.split(" ")[1]
                schedule[current_week]={}
            elif row.get_attribute('class')!='tableSubHead' and row.get_attribute('bgcolor')!='#ffffff':
                string='{}(.*){}'.format('teamId=','&seasonId')
                temp=[int(re.search(string,col.find_element_by_tag_name('a').get_attribute('href')).group(1))\
                                                for i,col in enumerate(row.find_elements_by_tag_name('td')) if i in [0,3]]
                schedule[current_week][temp[0]]={'Opponent':temp[1],'Home':False}
                schedule[current_week][temp[1]]={'Opponent':temp[0],'Home':True}

        with open(filename,'w') as out:
            json.dump(schedule,out,indent=4,sort_keys=True,separators=(',',': '),ensure_ascii=True)
        out.close()

        print('Schedule Update Success')
        return True
    
    def update_league_settings(self):
        #TEMP. incomplete
        print('Updating {} Settings'.format(self.season))
        filename='nflleague/espn-league-json/{}/{}/settings.json'.format(self.league_id,self.season)
        check_dir(filename)
        if os.path.isfile(filename) and raw_input("Settings Exists. Update?(Y/N): ") in ['N','n']:
            print("Settings Update Skipped")
            return False

        self.__home()
        address="http://games.espn.com/ffl/leaguesetup/settings?leagueId={}".format(self.league_id)
        self.browser.get(address)
        sleep(5)
        
        settings={}
        #Basics Settings
        league_settings=self.browser.find_element_by_id('settings-content')
        basic_settings=league_settings.find_element_by_id('basicSettingsTable')
        settings['basic']={}
        for row in basic_settings.find_elements_by_tag_name('tr'):
            col=[c for c in row.find_elements_by_tag_name('td')]
            if len(col)==2:
                item=(col[0].text).lower().replace(" ","_")
                settings['basic'][item]=col[1].text

        #Roster Settings
        roster_settings=league_settings.find_element_by_name('roster')
        settings['roster']={}
        #one row so no loop
        left=roster_settings.find_element_by_css_selector('.dataSummary.settingLabel')
        for subrow in left.find_elements_by_tag_name('p'):
            item,val=subrow.text.split(': ')
            item=item.lower().replace(" ","_")
            settings['roster'][item]=val

        settings['roster']['positions']=collections.OrderedDict()
        right=roster_settings.find_elements_by_css_selector('.leagueSettingsTable.tableBody')[1]
        for subrow in right.find_elements_by_tag_name('tr'):
            subcol=subrow.find_elements_by_tag_name('td')
            pos,num=subcol[0].text,subcol[1].text
            if pos != 'POSITION':
                position=pos.split(" ")[-1].replace('(','').replace(')','')
                if pos.split(" ")[0] == 'Flex':
                    settings['roster']['flex']=position.split('/')
                    position='FLEX'
                elif pos.split(" ")[0] == 'Bench':
                    position='Bench'
                settings['roster']['positions'][position]=num
        
        settings['roster']['actives']=[]
        settings['roster']['gsis_actives']=[]
        for slot,no in settings['roster']['positions'].iteritems():
            for i in range(1,int(no)+1):
                settings['roster']['actives'].append(slot)
                if slot in ['RB','WR']:
                    settings['roster']['gsis_actives'].append('{}{}'.format(slot,i))
                else:
                    settings['roster']['gsis_actives'].append(slot)
        
        settings['roster']['slots_gsis']={}
        for slot in settings['roster']['actives']:
            settings['roster']['slots_gsis'][slot]=[]
            for gsis_slot in settings['roster']['gsis_actives']:
                if slot == gsis_slot.replace('1','').replace('2',''):
                    settings['roster']['slots_gsis'][slot].append(gsis_slot)
        for flex_slot in settings['roster']['flex']:
            settings['roster']['slots_gsis'][flex_slot].append('FLEX')

        if os.path.isfile(filename):
            os.remove(filename) 
        check_dir(filename)
        with open(filename,'w+') as out:
            json.dump(settings,out,indent=4,separators=(',',': '))

        self.update_league_scoring()
    
    def scrape_projections(self,week,site=None):
        if site == None:
            self.__espn(week)
            self.__fantasy_pros(week)
            self.__cbs(week)
        elif site=='CBS':
            self.__cbs(week)
        elif site=='ESPN':
            self.__espn(week)
        elif site=='FantasyPros':
            self.__fantasy_pros(week)
        now = datetime.now()
        with open('nflleague/projections/updated.txt','w') as out:
            out.write('{}/{} {}:{}'.format(now.month,'0{}'.format(now.day) if now.day<10 else now.day,\
                                                       now.hour, '0{}'.format(now.minute) if now.minute < 10 else now.minute))
        out.close()
        return

    def __cbs(self,week):
        #Scrapes cbs Projections for given week
        filename='nflleague/espn-league-json/projections/week{}/cbs.json'.format(week)
        
        print('Scraping CBS Projections.  Week: {} '.format(week))

        address="http://www.cbssports.com/fantasy/football/stats/weeklyprojections/{}/{}/avg/standard?&print_rows=9999"
        
        def scrape_cbs(pos):
            current={}
            self.__home()
            print("Position: {}".format(pos))
            self.browser.get(address.format(pos,week))
            sleep(5)
            player_table=self.browser.find_element_by_css_selector('.data.compact')
            for row in player_table.find_elements_by_tag_name('tr'):
                try:
                    cols=list(item.text for col,item in enumerate(row.find_elements_by_tag_name('td'),start=0))
                    if cols != [] and sum(map(float,cols[1:]))!=0.0:
                        if pos == 'QB':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'passing_cmp':float(cols[2]),
                            'passing_att':float(cols[1]),'passing_yds':float(cols[3]),
                            'passing_tds':float(cols[4]),'passing_int':float(cols[5]),'rushing_att':float(cols[8]),
                            'rushing_yds':float(cols[9]),'rushing_tds':float(cols[11])}
                        elif pos == 'RB':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'rushing_att':float(cols[1]),
                            'rushing_yds':float(cols[2]),'rushing_tds':float(cols[4]),'receiving_rec':float(cols[5]),
                            'receiving_yds':float(cols[6]),'receiving_tds':float(cols[8])}
                        elif pos in ['WR','TE']:
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'receiving_rec':float(cols[1]),
                            'receiving_yds':float(cols[2]),'receiving_tds':float(cols[4])}
                        elif pos == 'K':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'kicking_fgm_proj':float(cols[1]),
                            'kicking_fga':float(cols[2]),'kicking_xpmade':float(cols[3])}
                        elif pos == 'DST':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'defense_int':float(cols[1]),
                            'defense_frec':float(cols[2]),'defense_ffum':float(cols[3]),'defense_sk':float(cols[4]),
                            'defense_tds':float(cols[5]),'defense_safe':float(cols[6]),'defense_TPA':float(cols[7]),
                            'defense_TYDA':float(cols[8])}
                except (IndexError,ValueError,TypeError) as err:
                    print(err)
                    pass
            return current 
        cbs={}
        for pos in ['QB','RB','WR','TE','DST','K']:
            cbs=dict(scrape_cbs(pos).items() + cbs.items())

        
        if os.path.isfile(filename):
            os.remove(filename) 
        check_dir(filename)
        with open(filename,'w+') as out:
            out.seek(0)
            json.dump(cbs,out,indent=4,sort_keys=True,separators=(',',': '),ensure_ascii=True)
        
            return True

    def __fantasy_pros(self,week):
        #Scrapes fantasy pros Projections for given week
        filename='nflleague/espn-league-json/projections/week{}/fantasypros.json'.format(week)
        
        print('Scraping Fantasy Pros Projections.  Week: {} '.format(week))

        address="https://www.fantasypros.com/nfl/projections/{}.php"
        
        def scrape_fantasy_pros(pos):
            current={}
            self.__home()
            self.browser.get(address.format(pos.lower()))
            sleep(5)
            player_table=self.browser.find_element_by_id('data')
            for row in player_table.find_elements_by_tag_name('tr'):
                try:
                    cols=list(item.text for col,item in enumerate(row.find_elements_by_tag_name('td'),start=0))
                    if cols != [] and float(cols[-1])!=0.0:
                        if pos == 'QB':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'passing_cmp':float(cols[2]),
                            'passing_att':float(cols[1]),'passing_yds':float(cols[3]),
                            'passing_tds':float(cols[4]),'passing_int':float(cols[5]),'rushing_att':float(cols[6]),
                            'rushing_yds':float(cols[7]),'rushing_tds':float(cols[8]),'receiving_rec':0.0,
                            'receiving_yds':0.0,'receiving_tds':0.0}
                        if pos in ['RB','WR']:
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'passing_cmp':0.0,
                            'passing_att':0.0,'passing_yds':0.0,
                            'passing_tds':0.0, 'passing_int':0.0,'rushing_att':float(cols[1]),
                            'rushing_yds':float(cols[2]),'rushing_tds':float(cols[3]),'receiving_rec':float(cols[4]),
                            'receiving_yds':float(cols[5]),'receiving_tds':float(cols[6])}
                        elif pos == 'TE':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'passing_cmp':0.0,
                            'passing_att':0.0,'passing_yds':0.0,
                            'passing_tds':0.0, 'passing_int':0.0,'rushing_att':0.0,
                            'rushing_yds':0.0,'rushing_tds':0.0,'receiving_rec':float(cols[1]),
                            'receiving_yds':float(cols[2]),'receiving_tds':float(cols[3])}
                        elif pos == 'K':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'kicking_fgm_proj':float(cols[1]),
                            'kicking_fga':float(cols[2]),'kicking_xpmade':float(cols[3])}
                        elif pos == 'DST':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'defense_int':float(cols[2]),
                            'defense_frec':float(cols[3]),'defense_ffum':float(cols[4]),'defense_sk':float(cols[1]),
                            'defense_tds':float(cols[5]),'defense_safe':float(cols[7]),'defense_TPA':float(cols[8]),
                            'defense_TYDA':float(cols[9])}
                except (IndexError,ValueError) as err:
                    print(err)
                    pass
            return current 
        fp={}
        for pos in ['QB','RB','WR','TE','DST','K']:
            print("Position: {}".format(pos))
            fp=dict(scrape_fantasy_pros(pos).items() + fp.items())
        
        if os.path.isfile(filename):
            os.remove(filename) 
        check_dir(filename)
        with open(filename,'w+') as out:
            out.seek(0)
            json.dump(fp,out,indent=4,sort_keys=True,separators=(',',': '),ensure_ascii=True)
        
            return True
    
    def __espn(self,week):
        #Scrapes ESPN Projections for given week
        filename='nflleague/espn-league-json/projections/week{}/espn.json'.format(week)
        
        print('Scraping ESPN Projections.  Week: {} '.format(week))

        address="http://games.espn.com/ffl/tools/projections?&slotCategoryId={}&leagueId={}"
        address="{}{}".format(address,"&scoringPeriodId={}&seasonId={}&startIndex={}")
        ESPN_SCM={'QB':0,'RB':2,'WR':4,'TE':6,'DST':16,'K':17}
        
        def scrape_espn(pos):
            current={}
            dst_flag=False
            for i in range(0,99):
                print("Position: {}  Page: {}".format(pos,i))
                self.browser.get(address.format(ESPN_SCM[pos],self.league_id,week,self.season,40*i))
                WDW(self.browser,10).until(EC.element_to_be_clickable((By.LINK_TEXT,"Reset Draft")))
                player_table=self.browser.find_element_by_css_selector(".playerTableTable.tableBody")
                for row in player_table.find_elements_by_tag_name('tr'):
                    try:
                        cols=list(item.text for col,item in enumerate(row.find_elements_by_tag_name('td'),start=0)\
                                                                                                     if col not in [1,2,3,4])
                        if str(cols[-1]) in ['--','0'] and pos != 'DST':
                            return current
                        if pos in ['QB','RB','WR','TE']:
                            current[self.get_id_from_name(cols[0])]={'passing_cmp':float(cols[1].split("/")[0]),
                            'passing_att':float(cols[1].split("/")[1]),'passing_yds':float(cols[2]),
                            'passing_tds':float(cols[3]),'passing_int':float(cols[4]),'rushing_att':float(cols[5]),
                            'rushing_yds':float(cols[6]),'rushing_tds':float(cols[7]),'receiving_rec':float(cols[8]),
                            'receiving_yds':float(cols[9]),'receiving_tds':float(cols[10])}
                        elif pos == 'K':
                            current[self.get_id_from_name(cols[0])]={'kicking_fgm_proj':float(cols[4].split("/")[0]),
                            'kicking_fga':float(cols[4].split("/")[1]),'kicking_xpmade':float(cols[5].split("/")[0])}
                        elif pos == 'DST':
                            current[self.get_id_from_name(" ".join([cols[0],pos]))]={'defense_fpts':float(cols[-1])}
                    except (IndexError,ValueError) as err:
                        print(err)
                        pass
                if pos == 'DST':
                    return current
        espn={}
        #TODO multithread for all positions and block for kicker? definitely possible, but expensive. consider
        for pos in ['QB','RB','WR','TE','DST','K']:
            espn=dict(scrape_espn(pos).items() + espn.items())

        if os.path.isfile(filename):
            os.remove(filename) 
        check_dir(filename)
        with open(filename,'w+') as out:
            out.seek(0)
            json.dump(espn,out,indent=4,sort_keys=True,separators=(',',': '),ensure_ascii=True)
        
        return True
    
    def update_league_scoring(self):
        filename='nflleague/espn-league-json/{}/{}/scoring.json'.format(self.league_id,self.season)
        
        address="http://games.espn.com/ffl/leaguesetup/settings?leagueId={}".format(self.league_id)
        if self.browser.current_url!=address:
            self.browser.get(address)
            sleep(5)
        
        scoring={}
        league_settings=self.browser.find_element_by_id('settings-content')
        scoring_settings=league_settings.find_element_by_name('scoring') 
        for row in scoring_settings.find_elements_by_class_name('rowOdd'):
            for subtable in row.find_elements_by_tag_name('tr'):
                statName=subtable.find_elements_by_class_name('statName')
                statPoints=subtable.find_elements_by_class_name('statPoints')
                for name,points in zip(statName,statPoints):
                    name,points=name.text,points.text
                    name=name.split(" ")[-1].replace('(','').replace(')','')
                    new_name=ESPN_SCORING_MAP.get(name,False)
                    if new_name:
                        scoring[new_name]=points 
                    else:
                        print('Failed',name,points)
        
        for row in scoring_settings.find_elements_by_class_name('rowEven'):
            if row.find_element_by_css_selector('.categoryName.settingLabel').text=='Team Defense / Special Teams':
                scoring['defense']={}
                for subtable in row.find_elements_by_tag_name('tr'):
                    statName=subtable.find_elements_by_class_name('statName')
                    statPoints=subtable.find_elements_by_class_name('statPoints')
                    for name,points in zip(statName,statPoints):
                        name,points=name.text,points.text
                        name=name.split(" ")[-1].replace('(','').replace(')','')
                        new_name=ESPN_SCORING_MAP.get(name,False)
                        if new_name:
                            scoring['defense'][new_name]=points
                        else:
                            print('Failed',name,points)
            else:
                for subtable in row.find_elements_by_tag_name('tr'):
                    statName=subtable.find_elements_by_class_name('statName')
                    statPoints=subtable.find_elements_by_class_name('statPoints')
                    for name,points in zip(statName,statPoints):
                        name,points=name.text,points.text
                        name=name.split(" ")[-1].replace('(','').replace(')','')
                        new_name=ESPN_SCORING_MAP.get(name,False)
                        if ESPN_SCORING_MAP.get(name,False):
                            scoring[new_name]=points 
                        else:
                            print('Failed',name,points)
        
        scoring['defense']['defense_fpts']=1.0
        scoring['defense']['defense_rush']=0
        scoring['defense']['defense_pass']=0
        """
        scoring={'passing_yds':0.04,
                 'passing_yds_py5':0.2,
                 'passing_tds':4.0, 
                 'passing_int':-2.0, 
                 #'passing_cmp':0.0,
                 #'passing_att':0.0,
                 'passing_twoptm':2.0,
                 'rushing_yds':0.1, 
                 'rushing_tds':6.0, 
                 #'rushing_att': 0.0, 
                 'rushing_twoptm':2.0,
                 'receiving_yds':0.1, 
                 'receiving_rec':0.2,
                 'receiving_tds':6.0, 
                 'receiving_twoptm':2.0,
                 'fumbles_lost':-2.0,
                 'kickret_yds':1.0,
                 'puntret_yds':1.0,
                 'kicking_fgm_0_39':2.0,
                 'kicking_fgm_40_49':3.0,
                 'kicking_fgm_50_100':4.0,
                 'kicking_fgm_proj':2.0,
                 #'kicking_fgm':0.0,
                 'kicking_xpmade':0.3,
                 #'kicking_xpa':0.0,
                 'kicking_xpmissed':-2.0,
                 'kicking_fgmissed_0_39':-1.0,
                 'kicking_fgmissed':0.0,
                 'defense':{
                            'defense_int':2.0,
                            'defense_frec':2.0,
                            'defense_sk':1.0,
                            'defense_tds':6.0,
                            #'defense_ffum':0.0,
                            'defense_safe':2.0,
                            'defense_puntblk':2.0,
                            'defense_xpblk':2.0,
                            'defense_fgblk':2.0,
                            'kickret_tds':6.0,
                            'puntret_tds':6.0,
                            'defense_PA_0':5.0,
                            'defense_PA_6':4.0,
                            'defense_PA_13':3.0,
                            'defense_PA_17':1.0,
                            'defense_PA_27':0.0,
                            'defense_PA_34':-1.0,
                            'defense_PA_45':-3.0, 
                            'defense_PA_46':-5.0, 
                            'defense_YA_99':5.0,
                            'defense_YA_199':3.0,
                            'defense_YA_299':2.0,
                            'defense_YA_349':0.0,
                            'defense_YA_399':-1.0,
                            'defense_YA_449':-3.0,
                            'defense_YA_499':-5.0,
                            'defense_YA_549':-6.0,
                            'defense_YA_550':-7.0,
                            'defense_rush':0,
                            'defense_pass':0,
                            #use for sites with dst projections w/o scoring breakdown
                            'defense_fpts':1.0}}
        """
        if os.path.isfile(filename):
            os.remove(filename) 
        check_dir(filename)
        with open(filename,'w+') as out:
            json.dump(scoring,out,ensure_ascii=True,indent=4,separators=(',',': '))

    def change_season(self,season):
        print('Navigating to League Office')
        if self.__home(season=season):
            self.season=season
            print('Current Season: {}'.format(self.season))
        else:
            print('Cannot access season or season does not exist')
    
    def close(self):
        print('\nClosing Browser')
        self.browser.quit()
        if not self.visible:
            self.display.popen.kill()
    
    def get_id_from_name(self,ptp):
        #receives tuple of form (player name, team, positions) or string of form 'First Last, Team Position' then filters
        if type(ptp) == tuple:
            name,team,pos=ptp
        else:
            name,team,pos=filter_ptp(ptp)
        print(name,team,pos)
        #Chad Johnson
        if name == 'Chad Ochocinco':
            return '00-0020397'
        #Roosevelt Nix-Jones
        if name == 'Roosevelt Nix':
            return '00-0030741'
        #Mike Vick
        if name == 'Michael Vick':
            return '00-0020245'
        #Dan Herron
        if name == 'Daniel Herron':
            return '00-0029588'
        #Steve Johnson
        if name == 'Stevie Johnson':
            return '00-0026364'
        #Anthony Dixon
        if name == 'Boobie Dixon':
            return '00-0027772'
        #Stephen Hauschka
        if name == 'Steven Hauschka':
            return '00-0025944'
        #Rob Kelley
        if name == 'Robert Kelley':
            return "00-0032371"
        #WR/RB
        if name == 'Danny Woodhead':
            return '00-0026019'
        
        if pos != 'D/ST':
            player=nflgame.find(name)
            if len(player) == 1:
                
                player=player[0]
                print('*',player.full_name,player.position,player.team,player.player_id)
                return player.player_id
            elif len(player) > 1:
                #For case of multiple players with same name
                player=nflleague.functions.find(name,self.season,players=self.player_game)
                if player != None and (player.position=='' or player.position == pos):
                    print('**',player.full_name,player.position,player.team,player.player_id)
                    return player.player_id
                else:
                    #For case of two active players with same name.  i.e. Brandon Marshall
                    player=nflleague.functions.find(name,self.season,pos=pos,players=self.player_game)
                    if player != None:
                        print('***',player.full_name,player.position,player.team,player.player_id)
                        return player.player_id
            return None
        elif pos == 'D/ST':
            return name
        return None

def filter_ptp(ptp):
    #takes string of for 'First X Last X, Team Pos', 'First X Last X, Team Pos Pos', 'Team D/ST, TeamABV D/ST', Team D/ST, D/ST'
    # or 'TeamLoc Team' and converts it to (First Last, TeamABV, pos) or (Team D/ST, TeamABV, D/ST)
    ptp=re.split(",| ",ptp.replace('*','').replace('/',''))
    ptp=filter(lambda x: x not in ['','O','Q','P','D','SSPD','IR','Sr.','Jr.','I','II','III','IV','V'],ptp)
    
    if ptp[-2] in ['WR','RB']:
        #Account for multiposition players
        name,team,pos=' '.join([ptp[0],ptp[-4]]),ptp[-3],ptp[-2]
        return (name,team,pos)
    elif ptp[-1] in ['QB','RB','WR','TE','K']:
        name,team,pos=' '.join([ptp[0],ptp[-3]]),ptp[-2],ptp[-1]
        return (name,team,pos)
    else:
        #may need to filter to standard team
        dst=filter(lambda x: x in TEAMS,ptp)[0]
        return ('{} D/ST'.format(dst),nflgame.standard_team(dst),'D/ST')
def u2a(unicodestring):
    return unicodestring.encode("utf-8")

def check_dir(filename):
    folder='/'.join(filename.split("/")[:-1])
    if not os.path.exists(folder):
        os.makedirs(folder)
        return False
    else:
        return True    
