#!/bin/bash
rm features.csv > /dev/null
sort -ru temp.csv -o features.csv
