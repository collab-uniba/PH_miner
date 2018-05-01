#!/usr/bin/env bash
# Run:
#   $ crontab -e
#
# Ensure bash is used, set:
#   SHELL=bash
# New products are uploaded at 12.01 PST (just past midnight, 10am next morning in Italy):
# minute hour day-of-month month day-of-week command
#   30     9       *          *       *        /path/.../to/PH_miner/run.sh /var/log/ph_miner.log 2>&1
#
# Run:
#   $ sudo ln -s ph_miner.logrotate /etc/logrotate.d/ph_miner

cd "$(dirname "$0")";
# modify the path to the virtualenv folder
# instead, for conda, replace with:
# source activate <environment name>
source .env/bin/activate
sh run.sh
deactivate
