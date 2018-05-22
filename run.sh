#!/usr/bin/env bash
export PYTHONPATH=$PYTHONPATH:.:./ph_py/:./scraper
python phminer.py $1
