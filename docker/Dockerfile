FROM mysocietyorg/apache-php-fpm:20190829120946.1d9903f
MAINTAINER sysadmin@mysociety.org

RUN apt-get update \
      && apt-get -t stretch-backports install -y \
          mediawiki \
          php-wikidiff2 \
        --no-install-recommends \
      && apt-get install -y \
          imagemagick \
          php-zip \
          php-intl \
          php-apcu \
          php-net-smtp \
          php-mail \
          unzip \
          zip \
        --no-install-recommends \
      && rm -r /var/lib/apt/lists/*

RUN curl -fSL https://getcomposer.org/download/1.7.3/composer.phar -o /usr/local/bin/composer \
  && chmod 0755 /usr/local/bin/composer

# Extra extensions
COPY ./extensions /var/lib/mediawiki/extensions

# Run composer against the AWS extension to pull in dependencies.
RUN cd /var/lib/mediawiki/extensions/AWS && /usr/local/bin/composer install

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
  sed -i -e 's/^user .*/user = wiki/' /etc/php/7.0/fpm/pool.d/www.conf; \
  sed -i -e 's/^group .*/group = wiki/' /etc/php/7.0/fpm/pool.d/www.conf; \
  sed -i -e 's/^listen.owner.*/listen.owner = wiki/' /etc/php/7.0/fpm/pool.d/www.conf;
