#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:.:./ph_py/:./scraper
python ph_miner.py $@
exit_code=$?
# only for the execution of the script run w/o params
# (i.e., for retrieving featured posts)
if [ -z "$1" ]; then
    # check the exit code of the mining process
    DONE_FILE="./done.txt"
    ERRORED_FILE="./errored.txt"
    DATE=`date '+%Y-%m-%d'`
    # anything != 0 is error
    if [ "$exit_code" -ne 0 ]; then
        echo "$DATE" >> "$ERRORED_FILE"
    else
        echo "$DATE" >> "$DONE_FILE"
    fi
fi
