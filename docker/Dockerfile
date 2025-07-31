FROM mysocietyorg/apache-php-fpm:bookworm
LABEL maintainer="sysadmin@mysociety.org"

RUN apt-get update \
      && apt-get install -y \
          composer \
          imagemagick \
          mediawiki \
          php-apcu \
          php-curl \
          php-intl \
          php-mail \
          php-net-smtp \
          php-wikidiff2 \
          php-zip \
          unzip \
          zip \
        --no-install-recommends \
      && rm -r /var/lib/apt/lists/*

# Extra extensions
COPY ./extensions /var/lib/mediawiki/extensions

# Run composer including the AWS extension to pull in dependencies.
ARG COMPOSER_ALLOW_SUPERUSER=1
COPY composer.local.json /var/lib/mediawiki/composer.local.json
WORKDIR /var/lib/mediawiki
RUN /usr/bin/composer update

# Apache Modules needed for mySociety deployment
RUN a2enmod authz_groupfile \
  && a2enmod rewrite \
  && a2disconf mediawiki \
  && ln -sf /var/lib/mediawiki /var/www/html/mediawiki

# Updated Apache configuration.
COPY apache.conf /etc/apache2/sites-available/000-default.conf

# Add user and update php-fpm to use it.
# We'll leave `listen.group` set to `www-data` so Apache can talk to the socker.
RUN set -ex; \
  adduser --shell /bin/bash --disabled-password --gecos "Wiki User" --uid 4415 wiki; \
  sed -i -e 's/^user .*/user = wiki/' /etc/php/8.2/fpm/pool.d/www.conf; \
  sed -i -e 's/^group .*/group = wiki/' /etc/php/8.2/fpm/pool.d/www.conf; \
  sed -i -e 's/^listen.owner.*/listen.owner = wiki/' /etc/php/8.2/fpm/pool.d/www.conf;
