#!/usr/bin/env python

import logging
import os
import mwclient
import yaml

logger = logging.getLogger('wikibot')

conf_file = os.path.dirname(os.path.dirname(__file__)) + '/conf/general.yml'
CONFIG = yaml.load(open(conf_file))


class MediaWiki(object):
    pageprefix = ''

    def __init__(self):
        if CONFIG['WIKIBOT_SANDBOX']:
            logger.info('Running in sandbox mode.')
            self.pageprefix = 'Sandbox:'

        logger.info('Connecting to the Wiki...')
        site = mwclient.Site(
            ('https', CONFIG['WIKI_URL']),
            httpauth=(CONFIG['WIKIBOT_USERNAME'], CONFIG['WIKIBOT_PASSWORD']),
            clients_useragent='mySociety Wiki Bot',
            path=CONFIG['WIKI_PATH']
        )
        site.login(CONFIG['WIKIBOT_USERNAME'], CONFIG['WIKIBOT_PASSWORD'])
        logger.info('Connected!')
        self.site = site

    def get_page(self, page):
        return self.site.Pages[self.pageprefix + page]
