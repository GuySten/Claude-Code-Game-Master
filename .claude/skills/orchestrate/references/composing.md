# Composing: the rulebook

Everything a composer needs, on one page. Read it whole; read nothing else unless a line
here sends you. A brief (the translator's) says WHAT the piece expresses; this says HOW to
write any piece well. Tags: **[H]** the host's verdict (their ears are final), **[R]** the
research (`research/` in the campaigns repo; several sources agree), **[r]** one source or an
inference. **(critic)** = `arrangement.py make` checks it: follow the rule and you pass.

## 1. The host's ears (never break these)
1. The tune is on top: at least +1 dB over everything else where it plays, aim +3. [H "now
   it's a lot better"] (critic; `make` sets a melody entry's gain; a `"lead": true` line:
   raise its `vel`)
2. A climax arrives: after a build, something nothing before it had - a part, a higher
   register, the tune's grandest setting. [H "a climax without the climax"] (critic: a theme
   that starts at full texture fails; in a stage, the peak - the top of `"dynamics"` - needs
   a part or a higher top note that the body's first 16 bars lacked)
3. The climax grows out of what came before: never stop what plays and start a new set in
   one bar; keep the piece's pulse or bass running through it. [H "the climax did not go with
   what was before"] (critic)
4. After a stage change the music starts strong and stays strong: the body after an entry
   keeps its energy - level and rhythm within ~3 dB (body `dynamics` within ~10 of the
   entry's) - while one part and the top register wait for the peak; dips come later. The
   entry has most of the stage's parts (the critic counts them against the body's), and
   parts carry across the entry-body join. [H "start strong"; "it dies after the
   transformation"] (critic)
5. The tune is recognisable in every form: state it whole, as written (a `"statements"`
   entry from its start to its end), in every boss stage loop and every theme; vary its
   setting, not its notes. [H "I could not figure if the second stage had the same tune"]
   (critic, stages)
6. No falling bends or slides on brass or low reeds (comic); a slide gets a part of its own.
   [H "it sounds like he farts"] (critic)
7. Darker is not slower: menace keeps momentum and lives in colour (low register, weight,
   harmony); slow + low reads as mournful. Fast, bright and high with no low weight reads
   as comic, not danger. [H, the Margrave; R]
8. Choirs are heard where they sing (critic: level) [H "I do not hear the choir"]. They
   sing held chords; chorus and men_choir may chant in quarter notes [r]. Prefer chorus,
   men_choir, choir; choir_oo/oh only for long pads [H "works only from midway"].
9. A short piece carries one or two ideas, layered, not a chain of events. [H "too much
   story in ~50 seconds"]
10. Develop: the second statement differs (new carrier, key, harmony, or a breakdown and
    rebuild), and where the tune holds, something else moves. [H "it does not develop
    into anything"; the remedies r]
11. A strong effect is a flash (about a beat, growing a little each time), not a section.
    [H, the madness violin]
12. Spend surprise once: a bold tune gets a plain setting; a simple tune gets the key
    change, the chromatic lift or the breakdown. [H, the 2x2 test] (critic: note)

## 2. What the research adds
13. Themes the table can learn: short, distinct in rhythm and timbre, on a clear type
    (march, lament, waltz...), the same skeleton every return. [R]
14. Escalate by 2-3 audible dimensions at once - density, register, key (a step or a minor
    third up), choir, tempo (+8-15 bpm, or double the motion) - while separate pieces stay
    level-matched; volume alone is not a stage. Chained key lifts turn into parody. [R]
15. Every climax: a build, a peak above the earlier peaks, a release; one peak per loop
    cycle. [r]
16. Under talk, sit back: steady level, no big tutti; music meant to play under scenes and
    places carries no melody spikes, and a place loop no melody at all. [R]
17. Hold the grandest setting (full brass, open choir, top register) for the arc's biggest
    moment; the tune itself is heard early, its full setting late. [R]
18. Save a full V-I for real arrivals; open scenes end off the tonic. [r Lehman]
19. Meaning comes from stacks of features (tempo, register, harmony, timbre together);
    context decides. Heroes: diatonic, brass, rising fifths. Villains: chromatic but
    centred, low and heavy. Wonder: chromatic third relations, used sparingly. [R]
20. Long loops change something audible every 8-16 bars and state the tune twice in
    different colours with a contrasting section; loops have no seams - the end meets the
    start (a stage: the body's start): end on a swell, a pickup or a roll into bar 1, not on
    a quiet offbeat. [r] (critic: seam; `make` fixes the dynamics)
21. Slow speakers (the strings, oboe, english_horn, organ, the choirs) need held notes; a
    quick note of theirs - the tune's too - needs a quick double at the same moment and
    pitch (the critic names one: flutes, clarinets, bassoons, horns, trumpets, pizzicato;
    `make` adds it to `lines`, you add it to `melody`). A part never restarts a pitch
    still sounding - a second choir at the peak goes on another choir part. [r] (critic)

## 3. Recipes (length · form · what must be there)
- **Theme** (a character, a villain's scenes): 40-75 s; a loop if it holds under scenes.
  Vamp in, the tune small, the tune again developed to ONE climax, back to the vamp (loop) or
  a decided ending (held chord, roll and stroke, or a quiet echo). Villains also get a
  battle piece on the same tune.
- **Boss stage** (`"role": "stage"`, from a stage plan): an ENTRY played once (`"start":
  -<beats>`, `"loop": true`, `"loop_from": 0`): 1-4 bars, most of the stage's forces, its
  signature figure, ff. Then the BODY, at least 150 s: the full drive (rule 4), the tune
  whole at least once (rule 5), a breakdown a third to halfway through (never silent),
  waves to one peak that brings something new (rule 2), back to the opening drive for the
  seam. Each later stage changes 2-3 things (rule 14) on the same core sound. A stage the
  plan marks `reveal` may be sparser, slower or sacred; its entry and body stay level.
- **Turn cue** (`"role": "turn"`, no `loop_from`): a loop as long as the plan says; the
  boss's identity under, the answer on top (`"lead": true`). **Pre-end** (`"role":
  "pre_end"`): 30-60 s, intense, no development, resolving into every ending.
- **Rise**: 1-2 bars of build; its `"length"` ends exactly on the next stage's downbeat.
  **Break**: an impact dying into 3-6 s of quiet; `"length"` covers the quiet. **Hit**: 1-3
  s on the stage's tonic and fifth only. All three in the next (or current) stage's key.
- **Endings** (the last stage's key): victory 4-10 s, sized to the boss; requiem 30-90 s,
  the tune slowed on one voice, ending in silence, never triumphant; escape 4-8 s, the hook
  broken off on an unresolved chord; wipe 2-5 s, a low hit, a falling cluster, silence.
- **Place** (`"role": "place"`): a long calm loop (60-180 s), mild dynamics, no events, no
  melody line, the place's own colour.
- **A PC's anthem by story stage** (the tune's versions come from the tool, never by hand):
  seed 15-20 s, one instrument over almost nothing; theme small, then developed, a modest
  ending; heroic: brass from the climb, the choir may enter; legendary: the hook's rhythm in
  the intro, horns alone first, a harmonic surprise at the climax with choir and cymbal, the
  fullest return, a ritardando. Wounded: x0.75, a solo voice, no brass. Bonded: a second
  voice, add9/maj7. Darkened 1-3: one borrowed chord, then lower and heavier, then nearly the
  villain. Dark twin: the minor tune, low, bII colour, climax on bVI, the hero's hook faint at
  the very end - with momentum (rule 7).

## 4. Writing it
- See the tune first: `python lib/arrangement.py tune "<who>" --written music/tunes/<who>.json`
  (every note, its time, the tune's length, and per bar a menu of chords that hold it -
  chromatic ones included; the choice, and its surprise, are yours).
- The tune: `"tune": {"seed": "<who>", "written": <the tune file's object>, "key": "F4"}`
  (`key` moves tune and chords together). Statements: `{"at": 32}`; a statement's
  `"shift": 2` needs `"keys": [{"from": 32, "to": 64, "shift": 2}]` too, or the chords stay
  in the old key. Who plays it: `"melody": [{"from": 0, "to": 32, "parts": {"horns": 0}}]`
  (semitones from as written) - every statement needs one (critic).
- Chords: `"progression": "i bVI iv V"` (`every`, `repeat`) or `"chords"` [from, to,
  symbol]; they sound only through `"harmony"` parts. Every tune note needs a chord under
  it (critic: error).
- Repeated material ONCE: `"motifs"` placed in `"lines"` (`at`, `shift`, `octave`,
  `stretch`, `repeat`/`every`; `invert`/`retro`/`alter` only for a story reason, once the
  tune has been heard straight - here or in an earlier piece - and a motif never counts as
  the tune stated whole); accompaniment ONCE: `"figures"` played with `"spans"`; any
  harmony / patterns / rolls / hits entry takes `"parts": [...]`, a hit `"at": [...]` (a
  tutti written once); `"double"` for doublings. Timpani on the chord's root or fifth:
  `"patterns"` or `"hits"` with `"note": "root"`, not `"harmony"`. No helper scripts.
- `"dynamics"`: the velocity curve, [[time, velocity], ...] - the critic finds the peak at
  its top; `make` edits its last point for the seam.
- Parts: violins, violins2 (also the viola register - there is no viola), strings, tremolo,
  pizzicato, cellos, basses, flutes, piccolo, oboe, english_horn, clarinets, bassoons,
  horns, trumpets, trombones, tuba, brass, harp, celesta, glockenspiel, bells, organ,
  timpani, solo_violin; voices choir, chorus, men_choir, choir_oo, choir_oh; drums kit,
  taiko, toms, reverse_cymbal (`"patterns"`). Ranges: violins G3-E7, violins2 G3-C7, cellos
  C2-E5, basses E1-C4, flutes C4-C7, piccolo D5-C8, oboe A#3-G6, english_horn E3-A5,
  clarinets D3-G6, bassoons A#1-C5, horns F2-F5, trumpets F#3-A#5, trombones E2-C5, tuba
  E1-A#3, timpani D2-G3, men_choir E2-A4, chorus E2-E6, choir_oo/oh A2-D#6 (critic).
- Title: `"<who>: <its real name> (<what it is>)"`. Scores: `music/arrangements/<who>-
  <version>.json`; a boss's cues render to `music/<boss>-<cue>--<title>.ogg`.
- Anything else in the format: the docstring at the top of `lib/music/arrangement.py` -
  look things up, don't read it through.

## 5. The loop
Python: the orchestra's (`.compose-venv/bin/python`, set up by `gm-music-compose.sh setup
--orchestra`).
1. Plan in words: one line per section (who carries the tune, what builds, the peak).
2. Write the score.
3. `python lib/arrangement.py make score.json --out piece.ogg`: applies the mechanical fixes
   (writing them into the score), runs the critic, renders only when no ERROR or WARN is
   left. Fix what it reports - each is a rule above; a NOTE is a question: fix it or say
   why it's meant - and run it again.
4. Report: paths, length (and loop point), the critic's last line, where the tune is whole,
   and what the host should listen for, with timestamps.
