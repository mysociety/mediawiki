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

# Handy flags to help with debugging...
# Don't actually push messages to Slack, just show the message payload locally
DO_NOT_SEND = False
# Add all standups to the announce list, regardless of time
ANNOUNCE_ALL = False
# Announce in a specific channel, rather than the one listed in the Wiki
# False is a default value, but '@yourusername' and '#sandbox' are also good
ANNOUNCE_IN = False

print('StandupBot')

# First check, let's see if we want to run at all

if datetime.datetime.today().weekday() < 5:
    print('Today is a weekday, starting the process!')

    site = MediaWiki(user_agent='StandupBot')

    # Regex patterns
    listPattern = re.compile('\* (.*)')
    sectionPattern = re.compile('<!-- Begin Standups Schedule -->(.*?)<!-- End Standups Schedule -->', re.M | re.S)
    standupPattern = re.compile('\|-\n\| (.*?)\n\| (.*?)\n\| (.*?)\n\| (.*?)\n', re.M | re.S)

    announceForTime = datetime.datetime.now()
    announceForTimeString = announceForTime.strftime("%H:%M")

    print('Will be announcing standups for time ' + announceForTimeString)

    # Grab the list of standups!

    print('Getting standup page...')
    page = site.get_page('Standups')
    text = page.text()

    section = sectionPattern.search(text)

    standups = []

    if section:
        print('Found table, parsing for standups...')
        table = section.group(1)

        # Find all the matches in the table
        for match in re.finditer(standupPattern, table):

            url = re.sub(r'{{ ?hangout ?\| ?(.*) ?}}', r'https://hangouts.google.com/hangouts/_/mysociety.org/\1', match.group(3))

            if ANNOUNCE_IN:
                channel = ANNOUNCE_IN
            else:
                channel = match.group(4)

            standup = {
                'team': match.group(1),
                'time': match.group(2),
                'url': url,
                'channel': channel
            }

            # Is this a standup we want to announce?
            if (standup['time'] == announceForTimeString or ANNOUNCE_ALL):
                print('Planning to announce ' + standup['team'] + ' standup at ' + standup['time'])
                standups.append(standup)
            else:
                print('Skipping ' + standup['team'] + ' standup at ' + standup['time'])

            print('\tURL: ' + standup['url'])
            print('\tChannel: ' + standup['channel'])

        # If we have any standups in the list, go for it
        if len(standups) > 0:

            # Find the orders!
            print('Finding orders...')
            page = site.get_page('Standups/Orders')
            text = page.text()

            orders = []

            for match in re.finditer(listPattern, text):
                print('\tFound Order: ' + match.group(1))
                orders.append(match.group(1))

            # Find the starter questions
            print('Finding questions...')
            page = site.get_page('Standups/Questions')
            text = page.text()

            questions = []

            for match in re.finditer(listPattern, text):
                print('\tFound Question: ' + match.group(1))
                questions.append(match.group(1))

            # Actually loop through the standups which need announcing!
            for standup in standups:

                data = {
                    "username": "standupbot",
                    "icon_emoji": ":man_in_business_suit_levitating:",
                    "channel": standup['channel'],
                    "text": "<!here> It's standup time!",
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

                if DO_NOT_SEND:
                    print(json.dumps(data))

                else:

                    try:
                        req = Request(CONFIG['SLACK_STANDUPBOT_HOOK_URL'])
                        req.add_header('Content-Type', 'application/json')

                        response = urlopen(req, json.dumps(data).encode('utf-8'))
                    except HTTPError as e:
                        error_message = e.read()
                        print(error_message)

        else:
            print('There are no standups which need announcing.')

    else:
        print('Could not find standups table.')

else:
    print('Today is the weekend, we don\'t have any standups.')
