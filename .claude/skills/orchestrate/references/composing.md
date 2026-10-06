# Composing: the rulebook

Everything a composer needs, on one page. Read it whole; read nothing else unless a line
here sends you. A brief (the translator's) says WHAT the piece expresses; this says HOW to
write any piece well. Tags: **[H]** the host's verdict (their ears are final), **[R]** the
research (`research/` in the campaigns repo: many sources agree), **[r]** one source or an
inference. **(critic)** = `arrangement.py check` enforces it - you don't have to remember it.

## 1. The host's ears (never break these)
1. The tune is on top: at least +1 dB over everything else where it plays, aim +3. [H "now
   it's a lot better"] (critic; `fix` sets the gain)
2. A climax arrives: something nothing before it had - a register, a part, a chord, the
   tune's full form - after a build. A piece already at full texture has no climax. [H "a
   climax without the climax"] (critic)
3. The climax grows out of what came before: never stop what plays and start a new set in
   one bar. [H "the climax did not go with what was before"] (critic)
4. After a stage change the music starts strong - and stays strong: the body after an
   entry keeps its energy (within ~3 dB); dips come later. [H "start strong"; "it dies
   after the transformation"] (critic)
5. The tune is recognisable in every form: state it whole, as written, in every boss stage
   loop and every theme; vary its setting, not its notes. [H "I could not figure if the
   second stage had the same tune"] (critic, stages)
6. No falling bends or slides on brass or low reeds (comic); a slide gets a part of its own.
   [H "it sounds like he farts"] (critic)
7. Darker is not slower: menace keeps momentum and lives in colour (low register, weight,
   harmony); slow + low reads as mournful. [H, the Margrave]
8. Choirs sing held chords (a beat or more), never rhythms, and are heard where they sing.
   The "oo"/"oh" choirs speak late: long held chords only. [H "I do not hear the choir"]
   (critic: level)
9. A short piece carries one or two ideas, layered, not a chain of events. [H "too much
   story in ~50 seconds"]
10. Develop: the second statement differs (new carrier, key, harmony, or a breakdown and
    rebuild). [H "it does not develop into anything"]
11. A strong effect is a flash (about a beat, growing a little each time), not a section.
    [H, the madness violin]
12. Loops have no seams: the end meets the start in level and texture. [H] (critic; `fix`)

## 2. What the research adds
13. Themes the table can learn: short, distinct in rhythm and timbre, on a clear type
    (march, lament, waltz...), the same skeleton every return. [R]
14. Escalate by 2-3 audible dimensions at once - density, register, key (a step or a minor
    third up), choir, tempo - while separate pieces stay level-matched; volume alone is not
    a stage. Chained key lifts turn into parody. [R]
15. Every climax: a build, a peak above the earlier peaks, a release. One peak per loop
    cycle. [R]
16. Under talk, sit back: steady level, no melody spikes, no big tutti while people speak. [R]
17. Hold the grandest setting (full brass, open choir, top register) for the arc's biggest
    moment; the tune itself is heard early, its full setting late. [R]
18. Save a full V-I for real arrivals; open scenes end off the tonic. [r Lehman]
19. Meaning comes from stacks of features (tempo, register, harmony, timbre together);
    context decides. Heroes: diatonic, brass, rising fifths. Villains: chromatic but
    centred, low and heavy. Wonder: chromatic third relations, used sparingly. [R]
20. Repetition is fine; too little music is not. Long loops change something audible every
    8-16 bars; state the tune twice in different colours with a contrasting section. [R]

## 3. Recipes (length · form · what must be there)
- **Theme** (a character, a villain's scenes): 40-75 s; a loop if it holds under scenes.
  Vamp in, the tune small, the tune again developed to ONE climax, back to the vamp (loop) or
  a decided ending (held chord, roll and stroke, or a quiet echo). Villains also get a
  battle piece on the same tune.
- **Boss stage** (from a stage plan): an ENTRY played once (`"start": -<beats>`, `"loop":
  true`, `"loop_from": 0`): 1-4 bars, most of the stage's forces, its signature figure, ff.
  Then the BODY, at least 150 s: opens on the full drive (rule 4), the tune whole at least
  once (rule 5), a breakdown a third to halfway through, waves to one peak that brings
  something new (rule 2), back to the opening drive for the seam. Each later stage changes
  2-3 things (rule 14) on the same core sound and tempo grid.
- **Turn cue** (a party-caused event, e.g. a counter-song): a loop as long as the plan says;
  the boss's identity under, the answer on top (`"lead": true`). **Pre-end**: 30-60 s,
  intense, no development, resolving into every ending.
- **Rise**: 1-2 bars of build; its `"length"` ends exactly on the next stage's downbeat.
  **Break**: an impact dying into 3-6 s of quiet; `"length"` covers the quiet. **Hit**: 1-3
  s on the stage's tonic and fifth only. (Short one-shots are mastered a little hotter.)
- **Endings** (the last stage's key): victory 4-10 s, sized to the boss; requiem 30-90 s,
  the tune slowed on one voice, ending in silence, never triumphant; escape 4-8 s, the hook
  broken off on an unresolved chord; wipe 2-5 s, a low hit, a falling cluster, silence.
- **Place**: a long calm loop (60-180 s), mild dynamics, no events, the place's own colour.
- **A PC's anthem by story stage** (the tune's versions come from the tool, never by hand):
  seed 15-20 s, one instrument over almost nothing; theme small, then developed, a modest
  ending; heroic: brass from the climb, the choir may enter; legendary: the hook's rhythm in
  the intro, horns alone first, a harmonic surprise at the climax with choir and cymbal, the
  fullest return, a ritardando. Wounded: x0.75, a solo voice, no brass. Bonded: a second
  voice, add9/maj7. Darkened 1-3: one borrowed chord, then lower and heavier, then nearly the
  villain. Dark twin: the minor tune, low, bII colour, climax on bVI, the hero's hook faint at
  the very end - with momentum (rule 7).

## 4. Writing it fast
- The tune: `"tune": {"seed": "<who>", "written": <the tune file's object>, "key": "F4"}`
  (`key` moves tune and chords together). Statements: `{"at": 32, "shift": 0}` places it.
- Repeated material ONCE: `"motifs"` placed in `"lines"` (`at`, `shift`, `octave`,
  `stretch`, `repeat`/`every`; `invert`/`retro`/`alter` only for a story reason, after the
  tune was heard straight); accompaniment ONCE: `"figures"` played with `"spans"`;
  `"double"` for doublings; `"progression"` for chords. No helper scripts.
- Parts: violins, violins2 (also the viola register - there is no viola), strings, tremolo,
  pizzicato, cellos, basses, flutes, piccolo, oboe, english_horn, clarinets, bassoons,
  horns, trumpets, trombones, tuba, brass, harp, celesta, glockenspiel, bells, organ,
  timpani, solo_violin; voices choir, chorus, men_choir, choir_oo, choir_oh; drums kit,
  taiko, toms, reverse_cymbal (`"patterns"`). Ranges: `orchestra.RANGES` (the critic checks).
- Title: `"<who>: <its real name> (<what it is>)"`.
- Format details: the docstring at the top of `lib/music/arrangement.py` - look things up,
  don't read it through.

## 5. The loop
1. Plan in words: one line per section (who carries the tune, what builds, the peak).
2. Write the score.
3. `python lib/arrangement.py make score.json --out piece.ogg`: applies the mechanical
   fixes, runs the critic, renders when clean. Fix what it reports (an ERROR or WARN is a
   rule above; a NOTE is a question - fix it or say why it's meant), run it again.
4. Report: paths, length (and loop point), the critic's last line, and where the tune is
   whole - and tell the host what to listen for, with timestamps.
