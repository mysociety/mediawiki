#
# Makefile for mysocietyorg Docker images
#

COMMIT := $(shell git log -1 --pretty=%h)
TIME   := $(shell date +%Y%m%d%H%M%S)
DISTRO  = buster

.PHONEY: build

build:
	@echo Building mysocietyorg/mediawiki:${DISTRO}
	docker pull mysocietyorg/apache-php-fpm:${DISTRO}
	docker buildx build --no-cache --platform linux/amd64,linux/arm64 -t mysocietyorg/mediawiki:${DISTRO} -t mysocietyorg/mediawiki:${DISTRO}.${TIME}.${COMMIT} -t mysocietyorg/mediawiki:latest --push .
