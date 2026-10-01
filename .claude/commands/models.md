# /models - Choose which Claude models run the game

$ARGUMENTS - optional preset: recommended | budget | premium | inherit (plus `--gm opus|sonnet|haiku`)

The GM is this session; 15 helper agents handle side jobs (story, lookups, book import).
A preset sets all of them at once.

## Steps

1. If `$ARGUMENTS` names a preset, run it and skip to step 3:
   ```bash
   bash tools/gm-models.sh $ARGUMENTS
   ```
2. Otherwise show the current setup (`bash tools/gm-models.sh`), then ask with
   AskUserQuestion which preset to use. Options, recommended first:
   - **Recommended** — Opus GM, Sonnet story helpers, Haiku lookups, Opus book import.
     Best balance of story quality, speed and cost.
   - **Budget** — Sonnet GM, Haiku helpers. Cheapest that still plays well.
   - **Premium** — Opus GM and story helpers, Sonnet lookups. Quality first, costs most.
   - **Inherit** — every helper uses the GM's model (the original setup).
   Then run `bash tools/gm-models.sh <preset>`.
3. Tell the player, in one or two lines: what changed, that helpers switch from the next
   session, and that they can switch the GM right now with `/model <gm model>`. If friends
   are about to play online, mention `/fast` (faster replies from the same model, at a
   higher price). Do not run /model or /fast yourself — they are the player's commands.
