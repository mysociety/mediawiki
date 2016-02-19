# wiki-fixup Bot

import random
import re

from mediawiki import MediaWiki

print 'Wiki Fixup Randomiser'

site = MediaWiki(user_agent='Wiki Fixup Bot')

category = site.get_page('Category:Work Needed')
pages = [page for page in category]

print 'There are ' + str(len(pages)) + ' pages needing work.'

chosenpage = random.choice(pages)

fixpage = chosenpage.name
fixcount = len(pages)

print 'Today we shall fix "' + chosenpage.name + '"!'

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
    print '  Found section, updating it with article count and random page.'
    text = re.sub(sectionre, section, text)
    update_notes += ', updated pages in need of help section'
else:
    print '  No section found, adding a new one with article count and random page.'
    text = section + "\n\n" + text
    update_notes += ', added pages in need of help section'

# Save out the page, for good and awesome.
page.save(text, summary=update_notes)
print '  Page saved.'
