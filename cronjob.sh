#!/usr/bin/env bash
# Run:
#   $ crontab -e
#
# Ensure bash is used, set:
#   SHELL=bash
# New products are uploaded at 12.01 PST (just past midnight, 9.00am next morning in Italy):
# minute hour day-of-month month day-of-week command
#  35      8       *          *       *       /path/.../to/PH_miner/cronjob.sh >> /var/log/ph_miner.log 2>&1
#
#  05      20       *          *       *       /path/.../to/PH_miner/cronjob.sh --update --credentials=credentials_updater.yml >> /var/log/ph_miner_updates.log 2>&1
#
# To scan also newest product that do NOT get featured, run every 15 min:
#  */30     *       *          *       *       /path/.../to/PH_miner/cronjob.sh --newest --credentials=credentials_updater.yml >> /var/log/ph_miner_newest.log 2>&1
#
# To enable the rotation of logs, run:
#   $ sudo ln -s ph_miner.logrotate /etc/logrotate.d/ph_miner

cd "$(dirname "$0")";
# change the path to the virtualenv folder
# instead, for conda, replace with:
# source activate <environment name>
source .env/bin/activate
sh run.sh $@
# for conda, change to: source deactivate
deactivate
