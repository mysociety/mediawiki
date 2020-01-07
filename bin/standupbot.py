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
parser.add_argument("-c", "--channel", help="announce in a specific channel, such as @username or #sandbox")
args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)

# First check, let's see if we want to run at all
announceForTime = datetime.now()
if announceForTime.weekday() >= 5:
    logger.info('Today is the weekend, we don\'t have any standups.')
    sys.exit(0)

logger.debug('Today is a weekday, starting the process!')

site = MediaWiki(user_agent='StandupBot')

# Regex patterns
listPattern = re.compile('\* (.*)')
sectionPattern = re.compile('<!-- Begin Standups Schedule -->(.*?)<!-- End Standups Schedule -->', re.S)
entryPattern = re.compile('\|-\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| ([0-9]*?)\n', re.S)
roomPattern = re.compile('{{ ?(hangout|meet) ?\| ?(.*) ?}}')

announceForTimeString = announceForTime.strftime("%H:%M")
logger.info('Will be announcing standups for time ' + announceForTimeString)

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


section = sectionPattern.search(text)
if not section:
    logger.error('Could not find standups table on the Wiki.')
    sys.exit(1)

standups = []

logger.debug('Found table, parsing for standups...')
table = section.group(1)

# Find all the matches in the table
for match in re.finditer(entryPattern, table):
    team = match.group(1)
    url = construct_url(match.group(3))
    channel = args.channel or match.group(4)

    warningMinutes = int(match.group(5))
    logger.debug('Standup has {} minutes warning'.format(warningMinutes))

    # Convert the time string to an actual structure
    targetTime = datetime.strptime(match.group(2), "%H:%M")

    # Subtract minutes warning
    announceTime = targetTime - timedelta(minutes=warningMinutes)
    announceTimeString = announceTime.strftime("%H:%M")

    standup = {
        'team': team,
        'announceTime': announceTimeString,
        'url': url,
        'channel': channel,
        'warning': warningMinutes
    }

    # Is this a standup we want to announce?
    if (standup['announceTime'] == announceForTimeString or args.all):
        logger.info('Planning to announce ' + team + ' standup at ' + standup['announceTime'])
        standups.append(standup)
    else:
        logger.info('Skipping announcing ' + team + ' standup at ' + standup['announceTime'])

    logger.debug('\tURL: ' + standup['url'])
    logger.debug('\tChannel: ' + standup['channel'])

# If we have any standups in the list, go for it
if len(standups) == 0:
    logger.info('There are no standups which need announcing.')
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
for standup in standups:

    # Decide on the appropriate message string
    if standup['warning'] == 0:
        standupMessage = "It's time for the {} standup!".format(standup['team'])
    else:
        if standup['warning'] == 1:
            plural = 'minute'
        else:
            plural = 'minutes'

        standupMessage = "It's the {} standup in {} {}!".format(standup['team'], standup['warning'], plural)

    data = {
        "username": "standupbot",
        "icon_emoji": ":man_in_business_suit_levitating:",
        "channel": standup['channel'],
        "text": "<!here> {}".format(standupMessage),
        "attachments": [
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
    }

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
