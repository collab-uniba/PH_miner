#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:.:./ph_py/:./scraper
python ph_miner.py $1
# check the exit code of the mining process
# anything != 0 is error
exit_code=$?
DONE_FILE="./done.txt"
ERRORED_FILE="./errored.txt"
DATE=`date '+%Y-%m-%d'`
if [ "$exit_code" -ne 0 ]; then
    echo "$DATE" >> "$ERRORED_FILE"
else
    echo "$DATE" >> "$DONE_FILE"
fi
# only for the last execution of the script, run w/o params
# for safety, kill chromedriver and chromium browser dangling processes
if [ -z "$1" ]; then
    killall -9 chromium-browser > /dev/null
    killall -9 chromedriver > /dev/null
fi
