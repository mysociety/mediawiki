#
# Makefile for mysocietyorg Docker images
#

COMMIT := $(shell git log -1 --pretty=%h)
TIME   := $(shell date +%Y%m%d%H%M%S)

.PHONEY: all build push

build:
	@echo Building mysocietyorg/mediawiki:${TIME}.${COMMIT}
	docker build -t mysocietyorg/mediawiki:${TIME}.${COMMIT} .
	docker tag mysocietyorg/mediawiki:${TIME}.${COMMIT} mysocietyorg/mediawiki:latest

push:
	@echo Pushing mysocietyorg/mediawiki
	docker push mysocietyorg/mediawiki

all: build push
