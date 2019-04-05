#!/usr/bin/env python

import logging
import os
import re
import mwclient
import yaml

logger = logging.getLogger('wikibot')

conf_file = os.path.dirname(os.path.dirname(__file__)) + '/conf/general.yml'
CONFIG = yaml.load(open(conf_file), Loader=yaml.FullLoader)


class MediaWiki(object):
    pageprefix = ''

    def __init__(self,
                 username=CONFIG['WIKIFIXUPBOT_USERNAME'],
                 password=CONFIG['WIKIFIXUPBOT_PASSWORD'],
                 user_agent='mySociety Wiki Bot'):

        if CONFIG['WIKIBOT_SANDBOX']:
            logger.info('Running in sandbox mode.')
            self.pageprefix = 'Sandbox:'

        logger.info('Connecting to the Wiki...')
        site = mwclient.Site(
            ('https', CONFIG['WIKI_URL']),
            httpauth=(username, password),
            clients_useragent=user_agent,
            path=CONFIG['WIKI_PATH']
        )
        logger.info('Connected!')
        self.site = site

    def get_page(self, page):
        return self.site.Pages[self.pageprefix + page]

    def update_page(self, page, text, summary):
        page = self.get_page(page)
        if page.text() != text:
            logger.info('Updating %s' % page.name)
            page.save(text, summary=summary)

    def replace_page_part(self, page, text, begin_marker, end_marker, summary):
        page = self.get_page(page)
        current_text = page.text()
        text = re.sub(
            '(<!-- %s -->\s*).*?(\s*<!-- %s -->)(?s)' % (begin_marker, end_marker),
            r'\1%s\2' % text.strip(), current_text)
        if text != current_text:
            logger.info('Updating %s' % page.name)
            page.save(text, summary=summary)
