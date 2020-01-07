# StandupBot

from __future__ import print_function

import re
import json
import sys
import random
from datetime import datetime, timedelta

from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError

from mediawiki import MediaWiki, CONFIG

import argparse
import logging

logger = logging.getLogger('wikibot')
logging.basicConfig()

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-q", "--quiet", help="don't actually message Slack", action="store_true")
parser.add_argument("-a", "--all", help="announce all standups, regardless of time", action="store_true")
parser.add_argument("-d", "--date", help="provide fake date to use")
parser.add_argument("-c", "--channel", help="announce in a specific channel, such as @username or #sandbox")
args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)

# First check, let's see if we want to run at all
announceForTime = datetime.now().replace(second=0, microsecond=0)
if args.date:
    announceForTime = datetime.strptime(args.date, '%Y-%m-%dT%H:%M')
if announceForTime.weekday() >= 5:
    logger.info('Today is the weekend, we don\'t have any standups.')
    sys.exit(0)

logger.debug('Today is a weekday, starting the process!')

site = MediaWiki(user_agent='StandupBot')

# Regex patterns
listPattern = re.compile('\* (.*)')
planningPattern = re.compile('<!-- Begin Planning Schedule -->(.*?)<!-- End Planning Schedule -->', re.S)
sectionPattern = re.compile('<!-- Begin Standups Schedule -->(.*?)<!-- End Standups Schedule -->', re.S)
entryPattern = re.compile('\|-\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n', re.S)
roomPattern = re.compile('{{ ?(hangout|meet) ?\| ?(.*) ?}}')

logger.info('Will be announcing standups for time %s' % announceForTime)

logger.debug('Getting standup page...')
page = site.get_page('Standups')
text = page.text()

def construct_url(m):
    roomMatch = roomPattern.match(m)

    if roomMatch:
        if roomMatch.group(1) == 'hangout':
            url = 'https://hangouts.google.com/hangouts/_/mysociety.org/{}'.format(roomMatch.group(2))
        elif roomMatch.group(1) == 'meet':
            url = 'https://meet.google.com/{}'.format(roomMatch.group(2))
    else:
        url = m

    return url


def iter_row(section, planning):
    if not section:
        return
    text = section.group(1)
    url_column = 4 if planning else 3

    for match in re.finditer(entryPattern, text):
        targetTime = datetime.strptime(match.group(2), "%H:%M").time()
        targetDate = datetime.strptime(match.group(3), "%Y-%m-%d") if planning else announceForTime
        targetDatetime = datetime.combine(targetDate, targetTime)
        warningMinutes = int(match.group(url_column+2))
        announceTime = targetDatetime - timedelta(minutes=warningMinutes)

        yield {
            'team': match.group(1),
            'url': construct_url(match.group(url_column)),
            'channel': args.channel or match.group(url_column+1),
            'warning': warningMinutes,
            'announceTime': announceTime,
            'planning': planning,
            'extra': False if planning or match.group(6) == 'No' else True,
        }


to_announce = []
plannings = {}
section = planningPattern.search(text)
for planning in iter_row(section, True):
    team = planning['team']
    if announceForTime.date() == planning['announceTime'].date():
        # Skip standups on same day as sprint planning
        plannings[team] = planning
    if planning['announceTime'] == announceForTime or args.all:
        logger.info('Planning to announce %s planning at %s' % (team, planning['announceTime']))
        to_announce.append(planning)
    else:
        logger.info('Skipping announcing %s planning at %s' % (team, planning['announceTime']))


section = sectionPattern.search(text)
if not section:
    logger.error('Could not find standups table on the Wiki.')
    sys.exit(1)

logger.debug('Found table, parsing for standups...')

for standup in iter_row(section, False):
    team = standup['team']
    if team not in plannings and (standup['announceTime'] == announceForTime or args.all):
        logger.info('Planning to announce %s standup at %s' % (team, standup['announceTime']))
        to_announce.append(standup)
    else:
        logger.info('Skipping announcing %s standup at %s' % (team, standup['announceTime']))

    logger.debug('\tURL: ' + standup['url'])
    logger.debug('\tChannel: ' + standup['channel'])

if len(to_announce) == 0:
    logger.info('There are no standups/plannings which need announcing.')
    sys.exit(0)

# Find the orders!
logger.debug('Finding orders...')
page = site.get_page('Standups/Orders')
text = page.text()
orders = [m.group(1) for m in re.finditer(listPattern, text)]
logger.debug('Found %d orders' % len(orders))

# Find the starter questions
logger.debug('Finding questions...')
page = site.get_page('Standups/Questions')
text = page.text()
questions = [m.group(1) for m in re.finditer(listPattern, text)]
logger.debug('Found %d questions' % len(questions))

# Actually loop through the standups which need announcing!
for standup in to_announce:

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
                        "value": random.choice(orders)
                    },
                    {
                        "title": "Today's bonus question",
                        "value": random.choice(questions)
                    }
                ]
            }
        ]

    if args.quiet:
        logger.info(json.dumps(data))

    else:

        try:
            req = Request(CONFIG['SLACK_STANDUPBOT_HOOK_URL'])
            req.add_header('Content-Type', 'application/json')

            response = urlopen(req, json.dumps(data).encode('utf-8'))
        except HTTPError as e:
            error_message = e.read()
            logger.error(error_message)
