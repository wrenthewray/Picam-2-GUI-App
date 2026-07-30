#!/bin/sh
# launcher.sh
# navigate to home directory, then to this directory, then execute python script, then back home

cd /
cd home/wren-thewray/Documents/Picam-2-GUI-App
export DISPLAY=:0.0
python main.py
cd /
