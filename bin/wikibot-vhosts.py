#!/usr/bin/env python
"""
Updates the "Which machines do what" wiki page with a nice human-readable
presentation of the contents of /data/vhosts.json

"""

from __future__ import print_function

import os
import sys
import json
from collections import defaultdict
from mediawiki import MediaWiki, CONFIG

VHOSTS_JSON = "/data/vhosts.json"
PAGE_NAME = "Which machines do what"
START_SECTION = 'BEGIN AUTOMATED LIST'
END_SECTION = 'END AUTOMATED LIST'

if CONFIG['WIKIBOT_SANDBOX']:
    PAGE_NAME = "Sandbox:{}".format(PAGE_NAME)

# Various template fragments for building the wiki page

SERVER_HEADER = "== {name} ==\n"
SERVER_FOOTER = "\n\n"

VHOSTS_HEADER = "=== Vhosts ({count}) ===\n"
VHOSTS_EMPTY = "There are no vhosts configured on this server.\n"

VHOSTS_TABLE_HEADER = """{| class="wikitable sortable"
! Name !! Site
"""
VHOSTS_TABLE_ROW = """|-
| {markup}[{href} {hostname}]{markup} || {site}
"""
VHOSTS_TABLE_FOOTER = """|}\n"""

DATABASES_HEADER = "=== Databases ({count}) ===\n"
DATABASES_EMPTY = "There are no databases configured on this server.\n"

DATABASES_TABLE_HEADER = """{| class="wikitable sortable"
! Name !! Type !! Vhosts
"""
DATABASES_TABLE_ROW = """|-
| {name} || {type} || {vhosts}
"""
DATABASES_TABLE_FOOTER = """|}\n"""


def load_vhosts_json():
    with open(VHOSTS_JSON) as f:
        try:
            return json.load(f)
        except ValueError as e:
            print("Couldn't load {}: {}".format(VHOSTS_JSON, e), file=sys.stderr)
            sys.exit(1)

def find_servers(deployments):
    """
    Rearrange the data from vhosts.json into a dict (keyed on server name) of dicts,
    with 'databases' and 'vhosts' lists for each server.
    """
    servers = defaultdict(lambda: defaultdict(list))
    dbs = {}
    for dbname, db in deployments['databases'].items():
        db['name'] = dbname
        db['vhosts'] = []
        dbs[dbname] = db
        servers[db['host']]['databases'].append(db)
    for vhostname, vhost in deployments['vhosts'].items():
        vhost['name'] = vhostname
        for server in vhost['servers']:
            servers[server]['vhosts'].append(vhost)
        for database in vhost.get('databases', []):
            dbs[database]['vhosts'].append(vhostname)
    return servers

def format_servers(servers):
    """
    Takes the dict of servers from find_servers and converts it into a string of wiki
    markup suitable for adding to the page.
    """
    sorted_servers = sorted(servers.keys())
    return "\n".join(format_server(s, servers[s]) for s in sorted_servers)

def format_server(name, deployments):
    output = SERVER_HEADER.format(name=name)
    output += format_vhosts(deployments['vhosts'])
    output += format_databases(deployments['databases'])
    output += SERVER_FOOTER

    return output

def format_vhosts(vhosts):
    if not vhosts:
        return VHOSTS_EMPTY
    output = VHOSTS_HEADER.format(count=len(vhosts))
    output += VHOSTS_TABLE_HEADER
    output += "".join(format_vhost(vhost) for vhost in sorted(vhosts, key=hostname_for_vhost))
    output += VHOSTS_TABLE_FOOTER
    return output

def format_vhost(vhost):
    params = vhost.copy()
    scheme = "https" if params.get('https') else "http"
    params['hostname'] = hostname_for_vhost(params)
    params['href'] = "{}://{}".format(scheme, params['hostname'])
    params['markup'] = "" if params['staging'] else "'''"
    return VHOSTS_TABLE_ROW.format(**params)

def hostname_for_vhost(vhost):
    redirects = vhost.get('redirects', [])
    if vhost['name'] in redirects:
        return vhost.get('aliases', [vhost['name']])[0]
    return vhost['name']


def format_databases(databases):
    if not databases:
        return DATABASES_EMPTY
    output = DATABASES_HEADER.format(count=len(databases))
    output += DATABASES_TABLE_HEADER
    output += "".join(format_database(database) for database in sorted(databases, key=lambda d: d['name']))
    output += DATABASES_TABLE_FOOTER
    return output

def format_database(database):
    kwargs = database.copy()
    kwargs['vhosts'] = "<br />".join(kwargs['vhosts'])
    return DATABASES_TABLE_ROW.format(**kwargs)

def update_wiki_page(wiki_text):
    MediaWiki().replace_page_part(PAGE_NAME, wiki_text, START_SECTION, END_SECTION, 'Updating vhosts list')

def main():
    deployments = load_vhosts_json()
    servers = find_servers(deployments)
    wiki_text = format_servers(servers)
    update_wiki_page(wiki_text)

if __name__ == '__main__':
    main()
