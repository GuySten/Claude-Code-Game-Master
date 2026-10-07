# After-session review

Run it after `gm-session.sh end` and `gm-recall.sh arc`, before the next prep. It answers one
question: did the table get fair, informed, shared play, and what do we change? Numbers point to
`design-directives.md`; V1-V6 are the host's verdicts.

## Where it lives, and what never goes in it

- Append one dated section to `world-state/campaigns/<campaign>/gm-review.md`. Campaign data
  is git-ignored and stays on the host's machine; the review is for the GM and the host only.
- **Players appear only as their PC's name.** Record in-game play and preferences only. No real
  names, contact details, ages, locations, health or anything said in the players' side chat
  (which you never read anyway). Keep the host's feedback as game feedback, not about people.
- Ruling precedents also go to `gm-note.sh rules` so scene context carries them next time.

## Data to read

- The table's message log (`table/log.jsonl` in the campaign folder): actions per PC,
  narration, whispers (`to`), loot and heroic beats.
- `gm-referee.sh log` and `report`: every roll, DC, advantage and free roll.
- `gm-player.sh party`, the session summary, `gm-npc.sh` updates, `gm-location.sh list`.
- The host's messages in the terminal, and any stars and wishes collected at the table.

## 1. Per-PC ledger (V3)

One row per PC. Count roughly; look for what persists and what the story doesn't explain.

| PC | Beats they drove | Clue routes reached them | Whispers received | Credited by name | Rewards (XP, award, loot, gold) | Heroic / grow | Kind of fun seen |
|---|---|---|---|---|---|---|---|

Then ask:
- Did anyone go a long stretch without a beat that mattered to *them*? (38, 51)
- Did openings, help from NPCs or heroic moments keep landing on the same PC for my reasons,
  not the story's? (39)
- Did someone get less because they wanted less (fine), or because I forgot them (fix)? (49)

## 2. Clue routes (V2)

For each conclusion in play: | Conclusion | Clues delivered | Route (thing, person, place, skill) | To whom, public or whisper | Reached? |

- Three or more routes per conclusion? Any core clue behind a roll? (19, 20)
- Did every PC hold a piece? Who held none? (21)
- Anything whispered that concerned the whole table, or another PC? (22, 36, T6)
- Where did the table stall, and how long before a lead came to them? (26)

## 3. Rulings and DCs (V3)

| Task | Conditions | Ladder word | Reason given | Same as precedent? |

- Same task, same conditions, same DC across PCs and sessions? Every difference explained in
  the fiction before the roll? (30)
- Any `--secret` roll that the PCs could have known? Any re-roll without a rule? (32, 33)
- The same check rolled again for the same task in a scene, or a crossed route rolled again? HP
  lost to a move whose fall wasn't named as the stake first? (65; CLAUDE.md Dice)
- Disputes or private challenges: answered, and ruled in public? (35)

## 4. Information, map and money (V4, V5, V6)

- Did any decision get made blind: a fight joined without a read on the enemy, a risk taken
  without the cost said? Any setback they couldn't explain afterwards? (8, 10, 47)
- Did any PC go down or die? Was the danger telegraphed, with an exit? After a round down, did
  their player get a channel, and their death saves through the referee? (9, 41, 42)
- Records true to play: every move through `gm-session.sh move`, dead NPCs marked, clocks matching
  the fiction, corrections filed as rulings, shared-objective XP to every PC present? (48, 71, 37)
- Every place visited on the map, its ways out connected, important places described? (72)
- Every gold and item change narrated with numbers, and persisted? Loot holders recorded? (74, 78)

## 5. What each player enjoyed

Per PC: when did they write more, faster, in character, with jokes; when did they go quiet?
Which kind of fun did that look like (fight, tactics, signature move, character drama, story,
discovery, loot, company)? Update the preference note; it's a guess, not a label. (49, 54)

## 6. The host's feedback and stars and wishes

- Write the host's verdict in a sentence, close to their words (game feedback only).
- Read it in three layers: what was said, what problem it names, what they want underneath.
  The host's verdict outranks your own read. (86)
- Stars and wishes, if collected: best moment, most frustrating, wanted to do but couldn't.

## 7. Turning findings into changes

1. **Filter.** Keep only imbalances that persist across a session or an arc and that the story
   doesn't explain (V3). One quiet scene is not a finding; a quiet session might be.
2. **State the problem in one line** ("Kael has found no clue in two sessions"). (87)
3. **Find the cause:**
   - *Play slip* (a directive existed and wasn't followed): add it to next session's playtest
     questions and the prep "each PC" list.
   - *Prep gap*: add or sharpen a line in `prep-checklist.md`.
   - *Missing rule*: draft a directive or a SKILL.md sentence; propose it to the host in the
     terminal; once approved, edit, and cite the verdict or review date that prompted it.
   - *Missing tool*: note it as a feature request for the host; meanwhile use the nearest
     real mechanism.
4. **Prefer one fix that solves two problems**; never contradict a host verdict.
5. **Test it next session** as a playtest question; keep it after it works, revert it if not.
6. **Correct imbalances forward, through the fiction:** the next strong start, lead or reward
   goes to who was short. Never by retconning what happened.

## Entry template

```
## Session N, <date>
Playtest questions: … → answers …
Ledger: (table)
Clue routes: (table)
Rulings: (table) · new precedents logged: …
Info/map/money misses: …
Enjoyment notes: <PC>: …
Host feedback: "…" → problem: … → want: …
Changes: problem → cause → fix → test next session
```
