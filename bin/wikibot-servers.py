#!/usr/bin/env python
"""
Updates the "Servers" wiki page with a table of server metadata
derived from PuppetDB
"""

import os
import yaml
import json
from pypuppetdb import connect
from collections import defaultdict
from mediawiki import MediaWiki, CONFIG

conf_file = os.path.dirname(os.path.dirname(__file__)) + '/conf/general.yml'
CONFIG = yaml.load(open(conf_file), Loader=yaml.FullLoader)

fields = [
  "hostname",
  "ipaddress",
  "ipaddress6",
  "location",
  "lsbdistcodename",
  "server_role",
  "ssh_fp_ecdsa",
  "ssh_fp_ed25519",
  "ssh_fp_rsa",
  "zone",
]

# Template fragments for building the tables on the wiki

PAGE_NAME = "Servers"
START_SECTION = 'BEGIN AUTOMATED LIST'
END_SECTION = 'END AUTOMATED LIST'

LOCATION_HEADER = "== {location} ({count}) ==\n"
LOCATON_FOOTER = "\n\n"

SERVERS_TABLE_HEADER = """{| class="wikitable sortable"
! Hostname !! Debian !! Zone !! Role !! IPv6 !! IPv4 !! SSH Host Key Fingerprints
"""

SERVERS_TABLE_ROW = """|-
| [{href} {hostname}] || {lsbdistcodename} || {zone} || [[Server_Roles/{server_role}|{server_role}]] || {ipaddress6} || {ipaddress} || '''RSA''' {ssh_fp_rsa}<br> '''ECDSA''' {ssh_fp_ecdsa} <br> '''ED25519''' {ssh_fp_ed25519}
"""

SERVERS_RABLE_FOOTER = """|}\n"""

# Obtain server data from PuppetDB
def get_server_data_from_puppetdb(fields):

  # connect to PuppetDB
  db = connect(
    ssl_key=CONFIG['WIKIFIXUPBOT_PUPPETDB_KEY'],
    ssl_cert=CONFIG['WIKIFIXUPBOT_PUPPETDB_CERT'],
    ssl_verify='/etc/puppetlabs/puppet/ssl/certs/ca.pem',
    host='puppet.ukcod.org.uk',
    port=8081
  )

  # Build data structure, skipping any missing facts.
  servers = defaultdict(dict)
  nodes = db.nodes()
  for node in nodes:
    fqdn = node.fact('fqdn').value
    for field in fields:
      try:
        servers[fqdn][field] = node.fact(field).value
      except:
        continue

  # disconnect from PuppetDB
  db.disconnect()

  # return data
  return servers

# Separate servers by location
def format_locations(servers):
  # Sort the servers into locations
  locations = defaultdict(dict)
  for server in servers:
    location = servers[server]['location']
    locations[location][server] = servers[server]
  return "\n".join(format_location(l, locations[l]) for l in sorted(locations.keys()))

# Set-up each locations section
def format_location(name, servers):
  output = LOCATION_HEADER.format(location=name, count=len(servers))
  output += format_servers(servers)
  return output

# Sort servers at a location
def format_servers(servers):
  output = SERVERS_TABLE_HEADER
  output += "".join(format_server(servers[server]) for server in sorted(servers.keys()))
  output += SERVERS_RABLE_FOOTER
  return output

# Generate each server's table entry
def format_server(server):
  params = server.copy()

  # Deal with missing IPv4 address
  if "ipaddress" not in params.keys():
    params['ipaddress'] = "N/A"

  # Deal with Panther's unusual name in the MB systems
  if params['hostname'] == "panther":
    linkname = "mypanther"
  else:
    linkname = params['hostname']

  # Set a URL for the server hostname link
  if params['location'] == "mythic":
    params['href'] = f'https://www.mythic-beasts.com/customer/servers/virtual/{linkname}'
  elif params['location'] == "brightbox":
    params['href'] = f'https://cloud.brightbox.com/accounts/acc-lrpha/servers/{linkname}/'
  else:
    params['href'] = 'https://wiki.mysociety.org/wiki/Servers'

  return SERVERS_TABLE_ROW.format(**params)


# Actually update the wiki
def update_wiki_page(wiki_text):
  MediaWiki().replace_page_part(PAGE_NAME, wiki_text, START_SECTION, END_SECTION, 'Updating servers list')

def main():
  servers = get_server_data_from_puppetdb(fields)
  wiki_text = format_locations(servers)
  update_wiki_page(wiki_text)

if __name__ == '__main__':
    main()
