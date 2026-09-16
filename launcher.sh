#!/bin/sh

set -eu

sleep 5
APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$APP_DIR"
export DISPLAY=:0.0
exec python3 main.py
