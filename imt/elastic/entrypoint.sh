#!/bin/bash

# Start the run once job.
echo "Docker container has been started"

declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /container.env

# Setup a cron schedule
echo "SHELL=/bin/bash
BASH_ENV=/container.env
* * * * * /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 3 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 6 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 9 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 12 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 15 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 18 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 21 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 24 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 27 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 30 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 33 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 36 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 39 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 42 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 45 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 48 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 51 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 54 ; /elastic_index.sh >> /var/log/cron.log 2>&1
* * * * * sleep 57 ; /elastic_index.sh >> /var/log/cron.log 2>&1
# This extra line makes it a valid cron" > scheduler.txt

crontab scheduler.txt
cron -f
