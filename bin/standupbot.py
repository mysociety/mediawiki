# StandupBot

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

import re
import json
import random
import datetime

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from mediawiki import MediaWiki, CONFIG

import argparse
import logging

logger = logging.getLogger('wikibot')
logging.basicConfig()

parser = argparse.ArgumentParser()

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")
parser.add_argument("-q", "--quiet", help="don't actually message Slack",
                    action="store_true")
parser.add_argument("-a", "--all", help="announce all standups, regardless of time",
                    action="store_true")
parser.add_argument("-c", "--channel", help="announce in a specific channel, such as @username or #sandbox")

args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)

logger.info('StandupBot')

# First check, let's see if we want to run at all

if datetime.datetime.today().weekday() < 5:
    logger.debug('Today is a weekday, starting the process!')

    site = MediaWiki(user_agent='StandupBot')

    # Regex patterns
    listPattern = re.compile('\* (.*)')
    sectionPattern = re.compile('<!-- Begin Standups Schedule -->(.*?)<!-- End Standups Schedule -->', re.M | re.S)
    standupPattern = re.compile('\|-\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n', re.M | re.S)

    announceForTime = datetime.datetime.now()
    announceForTimeString = announceForTime.strftime("%H:%M")

    logger.info('Will be announcing standups for time ' + announceForTimeString)

    # Grab the list of standups!

    logger.debug('Getting standup page...')
    page = site.get_page('Standups')
    text = page.text()

    section = sectionPattern.search(text)

    standups = []

    if section:
        logger.debug('Found table, parsing for standups...')
        table = section.group(1)

        # Find all the matches in the table
        for match in re.finditer(standupPattern, table):

            url = re.sub(r'{{ ?hangout ?\| ?(.*) ?}}', r'https://hangouts.google.com/hangouts/_/mysociety.org/\1', match.group(3))

            if args.channel:
                channel = args.channel
            else:
                channel = match.group(4)

            standup = {
                'team': match.group(1),
                'time': match.group(2),
                'url': url,
                'channel': channel
            }

            # Is this a standup we want to announce?
            if (standup['time'] == announceForTimeString or args.all):
                logger.info('Planning to announce ' + standup['team'] + ' standup at ' + standup['time'])
                standups.append(standup)
            else:
                logger.info('Skipping ' + standup['team'] + ' standup at ' + standup['time'])

            logger.debug('\tURL: ' + standup['url'])
            logger.debug('\tChannel: ' + standup['channel'])

        # If we have any standups in the list, go for it
        if len(standups) > 0:

            # Find the orders!
            logger.debug('Finding orders...')
            page = site.get_page('Standups/Orders')
            text = page.text()

            orders = []

            for match in re.finditer(listPattern, text):
                logger.debug('\tFound Order: ' + match.group(1))
                orders.append(match.group(1))

            # Find the starter questions
            logger.debug('Finding questions...')
            page = site.get_page('Standups/Questions')
            text = page.text()

            questions = []

            for match in re.finditer(listPattern, text):
                logger.debug('\tFound Question: ' + match.group(1))
                questions.append(match.group(1))

            # Actually loop through the standups which need announcing!
            for standup in standups:

                data = {
                    "username": "standupbot",
                    "icon_emoji": ":man_in_business_suit_levitating:",
                    "channel": standup['channel'],
                    "text": "It's standup time!",
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

        else:
            logger.info('There are no standups which need announcing.')

    else:
        logger.error('Could not find standups table on the Wiki.')

else:
    logger.info('Today is the weekend, we don\'t have any standups.')
