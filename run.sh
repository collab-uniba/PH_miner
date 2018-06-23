#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:.:./ph_py/:./scraper
python ph_miner.py $1

# only for the last execution of the script, run w/o params
if [ -z "$1" ]; then
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
fi
