# wiki-fixup Bot

import re
import urllib.request
import json
import datetime

from mediawiki import MediaWiki, CONFIG

import argparse
import logging

logger = logging.getLogger('wikibot')
logging.basicConfig()

parser = argparse.ArgumentParser()

parser.add_argument("-v", "--verbose", help="increase output verbosity",
                    action="store_true")

args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)

# Pipedrive's weird custom field values
pipedrive_field = {
    'url': 'c1c3eeb09294d3cc7f4f063112928f2af0fd3f47',
    'authority_type': 'b03d084a55c7185ccf693d5cffe6a7cdb9a84719',
    'projectdb_categories': 'd227060caf28505726bffbe677f2f4f401b1dd20'
}

projectdb_category_map = {
    '653': 'commercial',
    '656': 'funder_current',
    '655': 'funder_former',
    '657': 'research'
}

projectdb_canonical_country_names = {
    'Myanmar (Burma)': 'Myanmar',
    'United States': 'United States of America'
}

# Regex to match the organisation infoboxes
organisation_infobox_re = re.compile('\{\{ ?infobox organisation(.*?)\}\}', re.M | re.S)

# Pagination
pagination_start = 0
pagination_count = 100
pagination_remaining = True

# Threshold for an organisation becoming inactive
inactive_after_date = datetime.date.today() - datetime.timedelta(days=365)

logger.info('Pipedrive Bot')

logger.debug('Connecting to the Wiki...')

mw = MediaWiki(username=CONFIG['PIPEDRIVEBOT_USERNAME'],
               password=CONFIG['PIPEDRIVEBOT_PASSWORD'],
               user_agent='Wiki PipeDrive Bot')

logger.debug('Connected!')

logger.info('Getting list of organisations from Pipedrive...')

while (pagination_remaining):

    logger.info('Getting from ' + str(pagination_start) + ' to ' + str(pagination_start + pagination_count))

    url = "https://api.pipedrive.com/v1/organizations?start=" + str(pagination_start) + "&limit=" + str(pagination_count) + "&api_token=" + CONFIG['PIPEDRIVE_API_KEY']
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode('utf8'))

    if data['success']:

        for organisation in data['data']:

            logger.info('----')
            logger.info(organisation['name'] + ' (' + str(organisation['id']) + ')')

            logger.debug('Getting page...')

            page = mw.get_page(organisation['name'])
            text = page.text()

            update_notes = 'Automatic update from Pipedrive'

            # Is this page totally empty? If so, add the undocumented template!

            if not text:
                text = 'This organisation page was created by [[User:Pipedrivebot|PipedriveBot]] based on data in [[Pipedrive]].'
                logger.info('This is a new page!')
                update_notes = update_notes + ', created page'

            # Regardless of if there is an existing infobox or not, we need
            # one. Build it here.

            infobox = """{{ infobox organisation
|name=""" + organisation['name'] + """
|pipedrive_id=""" + str(organisation['id']) + """
|deals_open=""" + str(organisation['open_deals_count'] or 0) + """
|deals_closed=""" + str(organisation['closed_deals_count'] or 0) + """
|deals_won=""" + str(organisation['won_deals_count'] or 0) + """
|deals_lost=""" + str(organisation['lost_deals_count'] or 0) + """
"""

            if (organisation['last_activity_date'] and
                    datetime.datetime.strptime(organisation['last_activity_date'], '%Y-%m-%d').date() > inactive_after_date):
                infobox += """|active=True
"""
            else:
                infobox += """|active=False
"""

            if organisation[pipedrive_field['url']]:
                infobox += '|url=' + organisation[pipedrive_field['url']] + """
"""

            if organisation[pipedrive_field['authority_type']]:
                infobox += '|authority_type=' + organisation[pipedrive_field['authority_type']] + """
"""

            if organisation['address_country']:
                canonical_name = projectdb_canonical_country_names.get(organisation['address_country'], organisation['address_country'])
                infobox += '|country=' + canonical_name + """
"""

            # If there are any mapped categories, do something useful
            if organisation[pipedrive_field['projectdb_categories']]:

                category_codes = organisation[pipedrive_field['projectdb_categories']].split(',')

                for category_code in category_codes:
                    if category_code in projectdb_category_map:
                        infobox += '|' + projectdb_category_map[category_code] + """=True
"""

            infobox += '}}'

            # Find the infobox, if we can
            organisation_infobox_match = organisation_infobox_re.search(text)

            if organisation_infobox_match is not None:
                logger.debug('Found infobox, updating it.')
                text = re.sub(organisation_infobox_re, infobox, text)
                update_notes = update_notes + ', updated infobox'
            else:
                logger.info('No infobox found, adding a new one.')
                text = infobox + "\n\n" + text
                update_notes = update_notes + ', added infobox'

            mw.update_page(organisation['name'], text, update_notes)

        # Any pagination to do?
        if data['additional_data']['pagination']['more_items_in_collection']:
            logger.debug('There\'s another page of data, hang tight...')
            pagination_start = data['additional_data']['pagination']['next_start']
        else:
            pagination_remaining = False

    else:

        logger.error('Something went wrong: ' + data['error'])

logger.info('Updating own page with latest run...')

current_time = datetime.datetime.now().strftime('%A %-d %B %Y at %H:%M')
this_run_text = 'Latest run: ' + current_time
mw.replace_page_part('User:Pipedrivebot', this_run_text,
                     'BEGIN_LATEST_RUN', 'END_LATEST_RUN',
                     'Updated latest time the bot was run')

logger.info('All done!')
