# mySociety Mediawiki Deployment

This repository contains the code used to build and deploy our internal
Mediawiki instances. Some of this code was originally part of the 
[mysociety/internal](https://github.com/mysociety/internal) repository.

This is a work-in-progress.

## Setup

In production our deployment automation will seed the required environment variables into `../env.sh`. These are then used to build the configuration files and exported into the environment of the containers.

When working locally you can you can set up a similar file (there's an example at `conf/env-example`) and export `ENV_FILE` before running any of the setup scripts. This isn't necessary to do the initial bootstrap which will simply configure a virtualenv at `venv/` and perform some other checks.

Dependencies can be installed by running `script/bootstrap`. This is called from `script/update` which will also populate the required configuration files, although without a local environment file these will either be stub entries or empty strings.

## Deployment

In production, updates to the `master` branch of this repository will be automatically deployed, so any changes to things like wiki bots will be deployed automatically. Full details are available on our internal wiki on the MediaWiki_vhosts and Docker_Platform pages.

Local testing of a full stack isn't finished yet, there are some dependencies on our platform. [This issue](https://github.com/mysociety/mediawiki/issues/2) tracks this requirement.

## Build
### Terraform
The terraform code manages an S3 bucket and a user policy that grants access to the bucket for a given user. Due to the way we currently manage our AWS resources we expect this user to exist in the account against which the plan is applied.

Both `script/build` and `terraform/Makefile` are currently intended to work only with our infrastructure. `TF_STATE_KEY` should be set to the domain name of the wiki instance required with hyphens replacing dots and ensure you have suitable AWS credentials for access to our core account in your environment.

### Docker
`docker/Makefile` can be used to build new images. Images will be tagged `YYYYMMDDhhmmss.abcd1234` where `abcd1234` is the short version of the most recent local commit hash. These images are available from [Docker Hub](https://cloud.docker.com/u/mysocietyorg/repository/docker/mysocietyorg/mediawiki).

Deployments are configured to use a specific build and at present updating this is a manual task. When a new image has been built and pushed you'll need to update the deployment JSON, run Puppet and re-deploy the stack. As noted above, local deployments still need some additional work.
