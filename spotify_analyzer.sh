#!/usr/bin/env bash
# Simple shim to run the rediscovery analyzer in the current directory.
# Usage: ./spotify_analyzer.sh [path]
set -euo pipefail
PATH_ARG="${1:-.}"
python3 "$(dirname "$0")/spotify_rediscover_cli.py" "$PATH_ARG" --min-ms 0 --exclude-podcasts --html report.html
