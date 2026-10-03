#!/bin/bash
# gm-cloud.sh - The online table, hosted by Claude from a cloud session
# (thin wrapper for lib/cloud_table.py; see CLOUD-TABLE.md)
#
#   gm-cloud.sh page OUT              Build the Artifact's page (the players' table)
#   gm-cloud.sh pull DIR              Replay the players' requests saved from the Artifact
#   gm-cloud.sh media                 Pictures/music shown that aren't uploaded yet
#   gm-cloud.sh uploaded FILE=URL...  Record uploaded assets
#   gm-cloud.sh push OUT [--full]     What the players should see now (ArtifactData writes)
#   gm-cloud.sh sync DIR OUT          pull, then push (one step per wake)
#   gm-cloud.sh status                The Artifact, the requests query, the round
#   gm-cloud.sh set-url URL           Remember the Artifact's link

source "$(dirname "$0")/common.sh"

if [ "$1" != "page" ]; then
    require_active_campaign
fi

$PYTHON_CMD "$LIB_DIR/cloud_table.py" "$@"
exit $?
