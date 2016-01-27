#!/bin/bash

# abort on any errors
set -e

# check that we are in the expected directory
cd "$(dirname $BASH_SOURCE)"/../..

# Some env variables used during development seem to make things break - set
# them back to the defaults which is what they would have on the servers.
PYTHONDONTWRITEBYTECODE=""

# Create the virtual environment
virtualenv_dir='../virtualenv-wiki'
virtualenv_activate="$virtualenv_dir/bin/activate"
if [ ! -f "$virtualenv_activate" ]; then
    virtualenv $virtualenv_dir
fi
source $virtualenv_activate

# Upgrade python package management
curl -L -s https://raw.github.com/mysociety/commonlib/master/bin/get_pip.bash | bash

# Install what we need
pip install -r wiki/requirements.txt
