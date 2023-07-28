# StandupBot

import argparse
import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timedelta

from urllib.error import HTTPError
from urllib.request import Request, urlopen
from mediawiki import CONFIG, MediaWiki

logger = logging.getLogger('wikibot')
logging.basicConfig()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    parser.add_argument("-q", "--quiet", help="don't actually message Slack", action="store_true")
    parser.add_argument("-a", "--all", help="announce all standups, regardless of time", action="store_true")
    parser.add_argument("-d", "--date", help="provide fake date to use")
    parser.add_argument("-c", "--channel", help="announce in a specific channel, such as @username or #sandbox")
    args = parser.parse_args()
    return args


def no_run_date(time):
    if time.weekday() >= 5:
        logger.info('Today is the weekend, we don\'t have any standups.')
        return True

    if time.year == 2023 and time.month == 12 and time.day >= 25:
        logger.info('Twixtmas')
        return True

    path = os.path.dirname(__file__) + '/../../bank-holidays.json'
    try:
        data = json.load(open(path))
    except IOError:
        return False

    date = time.date().isoformat()
    def is_today(i):
        return i['date'] == date
    bh_ew = list(filter(is_today, data['england-and-wales']['events']))
    bh_s = list(filter(is_today, data['scotland']['events']))

    if bh_ew and bh_s:
        logger.info('UK-wide bank holiday, no standups')
        return True

    return False


COL = '(?:\\| (.*?)\n)'

class WikiParser(object):
    # Regex patterns
    listPattern = re.compile(r'\* (.*)')
    planningPattern = re.compile('<!-- Begin Planning Schedule -->(.*?)<!-- End Planning Schedule -->', re.S)
    sectionPattern = re.compile('<!-- Begin Standups Schedule -->(.*?)<!-- End Standups Schedule -->', re.S)
    entryPattern = re.compile('\\|-\n{COL}{COL}{COL}{COL}{COL}{COL}{COL}?'.format(COL=COL), re.S)
    roomPattern = re.compile('{{ ?(hangout|meet) ?\\| ?(.*) ?}}')

    def __init__(self, time, channel=None, ignore_time=False):
        self.site = MediaWiki(user_agent='StandupBot')
        self.time = time
        self.channel_override = channel
        self.ignore_time = ignore_time

    def get_pages(self):
        # Find the orders!
        logger.debug('Finding orders...')
        page = self.site.get_page('Standups/Orders')
        text = page.text()
        self.orders = orders = [m.group(1) for m in re.finditer(self.listPattern, text)]
        logger.debug('Found %d orders' % len(orders))

        # Find the starter questions
        logger.debug('Finding questions...')
        page = self.site.get_page('Standups/Questions')
        text = page.text()
        self.questions = questions = [m.group(1) for m in re.finditer(self.listPattern, text)]
        logger.debug('Found %d questions' % len(questions))

        logger.debug('Getting standup page...')
        page = self.site.get_page('Standups')
        self.text = page.text()

    def construct_url(self, m):
        roomMatch = self.roomPattern.match(m)

        if roomMatch:
            if roomMatch.group(1) == 'hangout':
                url = 'https://hangouts.google.com/hangouts/_/mysociety.org/{}'.format(roomMatch.group(2))
            elif roomMatch.group(1) == 'meet':
                url = 'https://meet.google.com/{}'.format(roomMatch.group(2))
        else:
            url = m

        return url

    def iter_row(self, section, planning):
        if not section:
            return
        text = section.group(1)

        for match in re.finditer(self.entryPattern, text):
            if planning:
                team, time, date, url, channel, minutes, _ = match.groups()
                targetDate = datetime.strptime(date, "%Y-%m-%d")
                extra = False
            else:
                team, time, days, url, channel, minutes, extra = match.groups()
                targetDate = self.time
                extra = (extra != 'No')
                days = days.split()
                if days and str(self.time.isoweekday()) not in days:
                    continue

            targetTime = datetime.strptime(time, "%H:%M").time()
            targetDatetime = datetime.combine(targetDate, targetTime)
            warningMinutes = int(minutes)
            announceTime = targetDatetime - timedelta(minutes=warningMinutes)

            yield {
                'team': team,
                'url': self.construct_url(url),
                'channel': self.channel_override or channel,
                'warning': warningMinutes,
                'announceTime': announceTime,
                'planning': planning,
                'extra': extra,
            }

    def planning(self):
        to_announce = []
        self.plannings = {}
        section = self.planningPattern.search(self.text)
        for planning in self.iter_row(section, True):
            team = planning['team']
            if self.time.date() == planning['announceTime'].date():
                # Skip standups on same day as sprint planning
                self.plannings[team] = planning
            if planning['announceTime'] == self.time or self.ignore_time:
                logger.info('Planning to announce %s planning at %s' % (team, planning['announceTime']))
                to_announce.append(planning)
            else:
                logger.info('Skipping announcing %s planning at %s' % (team, planning['announceTime']))
        return to_announce

    def standups(self):
        to_announce = []
        section = self.sectionPattern.search(self.text)
        if not section:
            logger.error('Could not find standups table on the Wiki.')
            sys.exit(1)

        logger.debug('Found table, parsing for standups...')

        for standup in self.iter_row(section, False):
            team = standup['team']
            if team not in self.plannings and (standup['announceTime'] == self.time or self.ignore_time):
                logger.info('Planning to announce %s standup at %s' % (team, standup['announceTime']))
                to_announce.append(standup)
            else:
                logger.info('Skipping announcing %s standup at %s' % (team, standup['announceTime']))

            logger.debug('\tURL: ' + standup['url'])
            logger.debug('\tChannel: ' + standup['channel'])
        return to_announce


class SlackPoster(object):
    def __init__(self, **kwargs):
        self.orders = kwargs['orders']
        self.questions = kwargs['questions']

    def construct_message(self, standup):
        # Decide on the appropriate message string
        event = 'sprint planning' if standup['planning'] else 'standup'

        if standup['warning'] == 0:
            standupMessage = "It's time for the {} {}!".format(standup['team'], event)
            if not standup['extra']:
                standupMessage += ' ' + standup['url']
        else:
            if standup['warning'] == 1:
                plural = 'minute'
            else:
                plural = 'minutes'

            standupMessage = "It's the {} {} in {} {}!".format(standup['team'], event, standup['warning'], plural)
            if not standup['extra']:
                standupMessage += ' ' + standup['url']

        data = {
            "username": "standupbot",
            "icon_emoji": ":man_in_business_suit_levitating:",
            "channel": standup['channel'],
            "text": "<!here> {}".format(standupMessage),
        }
        if standup['extra']:
            data["attachments"] = [
                {
                    "color": "good",
                    "fallback": "Standup: " + standup['url'],
                    "title": standup['team'] + " Standup",
                    "title_link": standup['url'],
                    "text": standup['url'],
                    "fields": [
                        {
                            "title": "Today's suggested order",
                            "value": random.choice(self.orders),
                        },
                        {
                            "title": "Today's bonus question",
                            "value": random.choice(self.questions),
                        },
                    ],
                }
            ]
        return data

    def post(self, to_announce, quiet=False):
        # Actually loop through the standups which need announcing!
        for standup in to_announce:
            data = self.construct_message(standup)
            if quiet:
                logger.info(json.dumps(data))
            else:
                try:
                    req = Request(CONFIG['SLACK_STANDUPBOT_HOOK_URL'])
                    req.add_header('Content-Type', 'application/json')
                    urlopen(req, json.dumps(data).encode('utf-8'))
                except HTTPError as e:
                    error_message = e.read()
                    logger.error(error_message)


args = parse_args()
if args.verbose:
    logger.setLevel(logging.DEBUG)

announceForTime = datetime.now().replace(second=0, microsecond=0)
if args.date:
    announceForTime = datetime.strptime(args.date, '%Y-%m-%dT%H:%M')

# First check, let's see if we want to run at all
if no_run_date(announceForTime):
    sys.exit(0)

logger.info('Will be announcing standups for time %s' % announceForTime)

parser = WikiParser(announceForTime, args.channel, args.all)
parser.get_pages()

to_announce = parser.planning() + parser.standups()

if len(to_announce) == 0:
    logger.info('There are no standups/plannings which need announcing.')
    sys.exit(0)

SlackPoster(orders=parser.orders, questions=parser.questions).post(to_announce, args.quiet)
