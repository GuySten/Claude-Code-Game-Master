#!/bin/bash
# json-get.sh - read a value (or list the keys) in a JSON file; works without jq.
#   bash tools/json-get.sh FILE dotted.path [DEFAULT]
#   bash tools/json-get.sh FILE path --keys
source "$(dirname "$0")/common.sh"
cd "$CALLER_PWD" 2>/dev/null || true
json_get "$@"
