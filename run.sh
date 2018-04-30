#!/usr/bin/env bash
# run crontab -e
# new products are uploaded at 12.01 PST (just past midnight, 10am next morning in Italy)
# minute hour day-of-month month day-of-week command
#   30     9       *          *       *        sh /path/to/PH_miner/run.sh

cd "$(dirname "$0")";
export PYTHONPATH=$PYTHONPATH:.:./ph_py/:./scraper
python phminer.py
