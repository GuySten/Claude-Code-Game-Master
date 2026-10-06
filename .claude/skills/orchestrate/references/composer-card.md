# Composer's card: a boss stage or a sting, on one page

Read this instead of the whole skill when you compose a boss's stage, its stings or its
endings from a stage plan. The plan (the translator's) decides the keys, tempi, core sound,
entry and peak; you write the music. Deeper reference only when something here is unclear:
the format docstring at the top of `lib/music/arrangement.py`, and `boss-music.md`.

## The rules the host's ears set (break none)
- **The tune is sacred.** Use it as written: `"tune": {"seed": "<who>", "written": <its
  object>, "key": "D4"}` (a new key moves tune and chords together; notes unchanged).
- **State it whole in every stage loop** at least once (a `"statements"` entry from its start
  to its end), the hook more often. Vary it by key, register, carrier, harmony, slower note
  values, the head alone. Inverted / reversed / altered notes only where the plan gives a
  story reason, after it has been heard straight. The critic checks.
- **A stage = a strong once-only entry + a loop body.** `"start": -<entry beats>`, `"loop":
  true`, `"loop_from": 0`, `"role": "battle"`. The entry (1-4 bars): most of the stage's
  forces, its signature figure, ff. The body: drop to the drive (about half the forces),
  build in waves, ONE peak a cycle with something held back for it, fall back to bar 1's
  texture for the seam. Body at least 150 s; something new every 8-16 bars.
- **Never** falling brass bends or slides (comic), harp / celesta / glockenspiel sparkle (reads
  as magic), the full texture from bar 1 ("a climax without the climax"), V-I inside a loop.
- **Stings** (not loops): break = impact + 3-6 s quiet, its `"length"` covering the quiet;
  hit = 1-3 s on the stage's tonic and fifth only; endings in the last stage's key.
- **Title:** `"title": "<who>: <its real name> (<what it is>)"` - the real name ends up in the
  file name for the host to learn after the campaign; the table never shows it.

## Write it fast
- Recurring material ONCE: `"motifs": {"hook": [[0, "D4", 1], ...]}`, placed in `"lines"` with
  `{"part": ..., "motif": "hook", "at": 96, "shift": 3, "octave": -1, "repeat": 4, "every": 12}`.
- An accompaniment ONCE: `"figures": {"waltz": [{"play": "bass", "range": [...], "pattern":
  "x--"}, {"play": "chord", "range": [...], "pattern": " oo", "vel": -6}]}`, played with
  `{"figure": "waltz", "part": "cellos", "spans": [[0, 132], [237, 432]], "vel": -12}`.
- Any harmony / patterns / rolls entry takes `"spans"` instead of from/to.
- A doubling: `"double": [{"part": "bassoons", "octave": -1}]` on the line.
- Chords: `"progression": "i bVI iv V"` with `"every"`/`"repeat"`, or `"chords"` [from, to, sym].
- A line carrying a tune that isn't the score's tune (an ally's phrase): `"lead": true`.
- No helper script needed for repeats - if you write one, keep it short.

## Parts and ranges
violins G3-E7, violins2 G3-C7 (also the viola register: there is no viola part), strings
C2-C7, tremolo C2-C7, pizzicato E1-C7, cellos C2-E5, basses E1-C4, flutes C4-C7, piccolo
D5-C8, oboe A#3-G6, english_horn E3-A5, clarinets D3-G6, bassoons A#1-C5, horns F2-F5,
trumpets F#3-A#5, trombones E2-C5, tuba E1-A#3, brass C2-C6, harp C1-G7, organ C1-C7,
timpani D2-G3, bells C4-F5, solo_violin G3-E7; voices: choir E2-A5, men_choir E2-A4, chorus
E2-E6, choir_oo / choir_oh A2-D#6; drums (patterns): kit, taiko, toms, reverse_cymbal.

## The loop
    P=<the orchestra's python>; A=lib/arrangement.py
    $P $A check score.json --quick     # 13 s: while writing
    $P $A fix score.json               # applies the mechanical fixes (ranges, quick doublings,
                                       # the tune's gain, the choir's level, the seam's dynamics)
    $P $A check score.json             # 21 s: the full critic (listens) - clean before rendering
    $P $A play score.json --out x.ogg  # 25 s for a 3-minute stage
Fix every ERROR and WARN; answer each NOTE in plan.md (fix it, or say why it's meant).
Report: the paths, the length and loop point, the critic's last line, where the tune is whole.
