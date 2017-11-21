# wiki-fixup Bot

import random
import re

from mediawiki import MediaWiki

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

logger.info('Wiki Fixup Randomiser')

site = MediaWiki(user_agent='Wiki Fixup Bot')

category = site.get_page('Category:Work Needed')
pages = [page for page in category]

logger.info('There are ' + str(len(pages)) + ' pages needing work.')

chosenpage = random.choice(pages)

fixpage = chosenpage.name
fixcount = len(pages)

logger.info('Today we shall fix "' + chosenpage.name + '"!')

# Go get the home page, this is where Today lives
page = site.get_page('Main_Page')
text = page.text()

# Regex for the section we're looking for
sectionre = re.compile('<!-- BEGIN WIKIFIX-RANDOMISER -->(.*?)<!-- END WIKIFIX-RANDOMISER -->', re.M | re.S)

# Regardless of if there is an existing section for this, there should be. Build it here.

section = """<!-- BEGIN WIKIFIX-RANDOMISER -->
There are [[:Category:Work Needed|'''""" + str(fixcount) + """''' pages in need of help]].

Today's random page in need of help is '''[[""" + chosenpage.name + """]]'''. If you know anything about this, go fix it!
<!-- END WIKIFIX-RANDOMISER -->"""

# Find the segment, if we can
sectionmatch = sectionre.search(text)

update_notes = 'Automatic update from Wiki Fixup Bot'

if sectionmatch is not None:
    logger.info('Found section, updating it with article count and random page.')
    text = re.sub(sectionre, section, text)
    update_notes += ', updated pages in need of help section'
else:
    logger.warning('No section found, adding a new one with article count and random page.')
    text = section + "\n\n" + text
    update_notes += ', added pages in need of help section'

# Save out the page, for good and awesome.
if text != page.text():
    page.save(text, summary=update_notes)
    logger.info('Page saved.')
else:
    logger.info('No change in page text, not saving.')
