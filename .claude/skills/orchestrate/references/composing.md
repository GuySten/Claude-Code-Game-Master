# Composing: the rulebook

Everything a composer needs, on one page. Read it whole; read nothing else unless a line
here sends you. A brief (the GM's) says WHAT the piece expresses - its Job line says what the
table must feel; this says HOW to write any piece well. A brief line that contradicts its Job or
the cue's role (a bright, dancing boss) is raised with the GM before writing, never followed. Tags: **[H]** the host's verdict (their ears are final), **[R]** the
research (`research/` in the campaigns repo; several sources agree), **[r]** one source or an
inference. **(critic)** = `arrangement.py make` checks it: follow the rule and you pass.

## 1. The host's ears (never break these)
1. The tune is on top: at least +1 dB over everything else where it plays, aim +3. [H "now
   it's a lot better"] (critic; `make` sets the gain of a melody entry and of a `"lead": true`
   line)
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
9. The number of ideas matches the length: about one per 15-20 seconds - a seed one, a
   30-45 s theme two, a 60-75 s theme three, a 2-3 minute loop four or five, each given its
   own section - layered over the one that carries, never a chain of events. [H "too much
   story in ~50 seconds"; "the number of ideas should match the length of the piece"]
10. Develop, never repeat: inside a statement, the carriers and the setting grow phrase by
    phrase; a second statement differs (new carrier, key, harmony, or a breakdown and
    rebuild); where the tune holds, something else moves. [H "it does not develop into
    anything"; "all the new themes feel a bit repetitive" - the shorter one, its tune stated
    once and passed round, won; the remedies r] (critic: a theme holding still 10 s or more
    before its peak)
11. A strong effect is a flash (about a beat, growing a little each time), not a section.
    [H, the madness violin]
12. Spend surprise once: a bold tune gets a plain setting; a simple tune gets the key
    change, the chromatic lift or the breakdown. [H, the 2x2 test] (critic: note)
13. Use the sound set's strengths, blended. Its best sounds: the held `strings` ensemble (the
    bed under almost everything), violins in octaves, the choir, flutes with clarinets. Its
    weakest, exposed: brass (trumpets most) and low reeds as a lone lead, and dry repeated-note
    riffs of cellos, basses and bassoons in bare fifths. Carry the tune in a blend (flutes +
    clarinets, horns + violins, violins in octaves + flutes); brass and bassoons go with
    strings or underneath, for weight. A start can be quiet - it can't be made of the weak
    sounds. A deep floor needs a key whose tonic sits in the basses' lowest octave (E1-D#2;
    their B1 is thin). [H, Kestrel: "a weak start and weaker instruments, and weaker combination"; "it's
    not always good to start strong"; the brass "really weak" as a lead] (critic: the tune on
    brass or low reeds alone)
    The voices can't run: a sampled choir changing notes faster than every 0.7 s sounds like an
    instrument [H, the Saint's hymn on eighths at 126: "the choir cannot do fast changes, they sound
    like an instrument"; again of a men's choir at 0.56 s a note] - give the voices the tune's long
    notes and held chords, the quick notes to strings or woods. The `men_choir` stays at E4 and below
    (its top "sounds like an instrument" [H]); a line that rises higher moves to the `chorus`. And the brass section is jarring in repeated short stabs [H: "the trumpets are
    too jarring", ~45 stabs a minute]: a few, held longer, or the hits on low strings, timpani and
    trombones blended. (critic)
    Dissonance is a spice, not a bed: a semitone clash sounding most of the time is "painful to hear"
    [H, the Saint's violated hymn, a clash 97% of the time; the liked pieces 11-21%] - keep the grind for
    cadences, cracks and the peak, over chords that otherwise sound clean. (critic)
    Electric guitar: never the General MIDI distortion guitar - "like someone was trying to hurt the
    guitar instead of playing it" [H]: a harsh 3 kHz buzz (distortion recorded with no speaker cabinet) and
    no pick attack. The real recorded guitar (Unreal Instruments' Standard Guitar, through an amp and
    cabinet, double-tracked hard left and right, mostly dry, ~6 dB under the orchestra; chords ringing on
    the strong beats, palm-muted chugs between, never choked notes): "great" [H]. **The electric guitar
    is only for a boss's later stages** (stage 2 and on, and their cues) [H: "electric guitar will only be
    used on bosses' later stages. It is a special surprise"] - never a theme, a place, a player's theme or a
    first stage (critic). An acoustic or classical guitar is an ordinary instrument, fine anywhere [H: "a
    regular guitar is ok. Only electric is the surprise"]. Its palm-muted chugs (`guitar_mute`) sound boomy
    and sag [H: "chug-current is the worst"]: drive with short open power chords on `guitar` (root,
    fifth, octave, held ~60-70%, even velocity) [H: "chug-open is the best"]. A short lead solo on
    `guitar_lead` (one overdriven voice near centre, legato, delayed vibrato; E2-G5) where the chant rests,
    in a later stage [H: "a short solo guitar to higher notes could lift it up"]; no falling bends (comic).

## 2. What the research adds
14. Themes the table can learn: short, distinct in rhythm and timbre, on a clear type
    (march, lament, waltz...), the same skeleton every return. [R]
15. Inside a piece, escalate by 2-3 audible dimensions at once - density, register, key (a
    step or a minor third up), choir, tempo or double the motion; volume alone is not a
    build, and chained key lifts turn into parody. [R] A boss's later stage is more than an
    escalation: a new world sharing only the tune (`boss-music.md` 2-3). [H]
16. Every climax: a build, a peak above the earlier peaks, a release; one peak per loop
    cycle. [r]
17. Under talk, sit back: steady level, no big tutti; music meant to play under scenes and
    places carries no melody spikes, and a place loop no melody at all. [R]
18. Hold the grandest setting (full brass, open choir, top register) for the arc's biggest
    moment; the tune itself is heard early, its full setting late. [R]
19. Save a full V-I for real arrivals; open scenes end off the tonic. [r Lehman]
20. Meaning comes from stacks of features (tempo, register, harmony, timbre together);
    context decides. Heroes: diatonic, brass, rising fifths. Villains: chromatic but
    centred, low and heavy. Wonder: chromatic third relations, used sparingly. [R]
21. Long loops change something audible every 8-16 bars and state the tune twice in
    different colours with a contrasting section; loops have no seams - the end meets the
    start (a stage: the body's start): end on a swell, a pickup or a roll into bar 1, not on
    a quiet offbeat. [r] (critic: seam, measured as heard on a repeat - a step means
    write the swell, roll or pickup into the last bar; `dynamics` alone won't do it)
22. Slow speakers (strings, tremolo, oboe, english_horn, organ, the choirs) need held notes; a
    quick note of theirs - the tune's too - needs a quick double at the same moment and
    pitch (the critic names one: flutes, clarinets, bassoons, horns, trumpets, pizzicato;
    `make` adds it to `lines`, you add it to `melody`). The string sections are not slow in
    quick notes: on violins, violins2, cellos and basses a note under 0.3 s plays from real
    short-note recordings (staccato/spiccato) that speak at once - automatic, in every
    score; write the figure as it is, with no pizzicato double to make it heard. Their
    notes from 0.3 s to the time the sustained recording takes to speak (violins 0.75 s,
    violins2 0.39, cellos 0.36) still smear: shorter (a lower `"legato"`) or held. A part
    never restarts a pitch still sounding - a second choir at the peak goes on another
    choir part. [r] [H "strings A is clearly better"] (critic)

## 3. Recipes (length · form · what must be there)
- **Theme** (a character, a villain's scenes): short - a first theme about 30-45 s, the
  tune stated ONCE and developed as it goes: a short vamp in, then the one statement passed
  round the orchestra (a new carrier and a fuller setting each phrase), building to ONE
  climax, then a decided ending (held chord, roll and stroke, or a quiet echo) - or back to
  the vamp, for a loop that holds under scenes. A second statement only when the piece has
  grown longer (later story stages, a loop): never the tune twice the same way. It makes a strong
  impression of who the character is from the first statement: small means fewer forces,
  never timid; a held-back trait is one layer or moment, not the piece's level [H, Kestrel:
  "stronger impression, strong character"].
  **The model the host called exceptional** (Kestrel's theme, 34 s at 66 in 6/8; measured
  from its render):
  - *The start* ("the low bass is very good"): the bass alone for its first ~2 s (`basses`
    holding one note a bar in their lowest octave, E1-D#2 - 81% of the sound under 120 Hz),
    a plucked stride over it (`pizzicato` roots on the two beats, `taiko` with them), then
    held `strings` quietly above and the tune on `flutes` + `clarinets`.
  - *The growth*: never flat - parts join phrase by phrase (3 -> 15 over the first 20 s) in
    one long crescendo (about +14 dB) up to the peak.
  - *The climax* ("exceptional"), at about two-thirds of the piece: reached in two waves - a
    timpani roll on the dominant into a crash and a first peak, a dip, then higher - over held
    `choir` chords and an offbeat snare; at the top the tune in three octaves (`violins` +
    `flutes` up an octave, `horns` as written, `trombones` an octave down), a IVmaj7 lift
    before it. The `trumpets` are saved for the climb into it: heard once, on the tune's
    falling phrase with the horns and violins ("its trumpets at the end are great"). Then a release (the horns echo the hook, 6-8 dB down) and a decided close on
    bVI-bVII-I: a roll and one stroke, under the peak.
  A model of what works, not a template: take the principles (a deep held floor, then the
  tune in a blend; growth every phrase; two waves, three octaves, the peak at about two-thirds,
  a release and a decided close).
  Villains also get a battle piece on the same tune.
- **Boss stage** (`"role": "stage"`, from a stage plan): an ENTRY played once (`"start":
  -<beats>`, `"loop": true`, `"loop_from": 0`): 1-4 bars, most of the stage's forces, its
  signature figure, ff. Then the BODY, at least 150 s: the full drive (rule 4), the tune
  whole at least once (rule 5), a breakdown a third to halfway through (never silent),
  waves to one peak that brings something new (rule 2), back to the opening drive for the
  seam. A later stage shares only the tune with the one before: its own carrying concept,
  pulse, leading instruments and harmony (`boss-music.md` 2-3); give it `"stage": N`. A stage the
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
- **A PC's theme grows with the character.** Its first version carries who they are now
  (one idea, a second as colour). Each growth the GM records (`gm-craft`: growth, bond,
  wound, darkness, light) adds that moment's idea to the theme - a new layer or a new
  section, or it replaces a colour - and the theme grows longer to hold it (rule 9); the
  carrying idea and the tune stay. Ideas the story hasn't given them yet wait. The GM's
  to-do list (`score_music.wanted`) asks for the rewrite with the moments listed; the score
  says how many it holds: `"use": {"as": "anthem", ..., "story": 4}`.
- **A PC's anthem by story stage** (the tune's versions come from the tool, never by hand):
  seed 15-20 s, one instrument over almost nothing; theme small, then developed, a modest
  ending; heroic: brass from the climb, the choir may enter; legendary: the hook's rhythm in
  the intro, horns alone first, a harmonic surprise at the climax with choir and cymbal, the
  fullest return, a ritardando. Wounded: x0.75, a solo voice, no brass. Bonded: a second
  voice, add9/maj7. Darkened 1-3: one borrowed chord, then lower and heavier, then nearly the
  villain. Dark twin: the minor tune, low, bII colour, climax on bVI, the hero's hook faint at
  the very end - with momentum (rule 7).

## 4. Writing it
- See the tune first: `python lib/arrangement.py tune "<who>" --written music/tunes/<who>.json
  --key F4` (in the piece's key: every note, its time, the hook's notes marked - "the hook" is
  those notes, after the pickup - the tune's
  length, and per bar - counted from the first downbeat, as `grid` counts - a menu of chords
  that hold it, chromatic ones included; the choice, and its surprise, are yours).
- Let the tool do the arithmetic: `python lib/arrangement.py grid "<who>" --written <tune>
  --tempo 168 --entry 4` prints the bar grid in units and seconds, the body length (in whole
  sections), where a whole statement lands on a bar line after its pickup, and where the
  breakdown and the peak fall. Lay the piece out on it; don't compute beats in your head.
- The tune: `"tune": {"seed": "<who>", "written": <the tune file's object>, "key": "F4"}`
  (`key` moves tune and chords together). Statements: `{"at": 32}`; a statement's
  `"shift": 2` needs `"keys": [{"from": 32, "to": 64, "shift": 2}]` too, or the chords stay
  in the old key. `"stretch": 4` augments a statement at the piece's own tempo (a chant
  over a fast engine) - keep `"tempo"` the real tempo. Who plays it: `"melody": [{"from": 0, "to": 32, "parts": {"horns": 0}}]`
  (semitones from as written) - every statement needs one (critic).
- Chords: `"progression": "i bVI iv V"` (`every`, `repeat`) or `"chords"` [from, to,
  symbol]; they sound only through `"harmony"` parts (`"play"`: chord, bass, root, third,
  fifth, root5, octaves, or arpeggio - one chord tone per pattern hit, for flowing figures).
  Numerals count from the tonic's MAJOR scale: in F minor iv = Bbm, bIII = Ab, bVI = Db,
  bVII = Eb, V = C. `"keys"` alone (no statement there) lifts a passage's chords; give
  motifs placed there the same `"shift"`. Every tune note needs a chord under it (critic:
  error).
- Repeated material ONCE: `"motifs"` placed in `"lines"` (`at`, `shift`, `octave`,
  `stretch`, `repeat`/`every`; `invert`/`retro`/`alter` only for a story reason, once the
  tune has been heard straight - here or in an earlier piece - and a motif never counts as
  the tune stated whole); accompaniment ONCE: `"figures"` played with `"spans"`; any
  harmony / patterns / rolls / hits entry takes `"parts": [...]`, a hit `"at": [...]` (a
  tutti written once); `"double"` for doublings (its octave counts from the line as
  placed). `alter` indexes count in the whole motif, also inside a `take`; `at` places the
  first note taken. Timpani on the chord's root or fifth:
  `"patterns"` or `"hits"` with `"note": "root"`, not `"harmony"`. No scripts that generate notes (a short one
  that edits the score is fine).
- `"dynamics"`: the velocity curve, [[time, velocity], ...] - the critic finds the peak at
  its top. Velocity changes a sampled note's attack and colour more than its level: the
  growth you hear comes from parts joining and doubling (raising a phrase from 80 to 92
  measured as nothing).
- Parts: violins, violins2 (also the viola register - there is no viola; its short notes are
  real violas), strings, tremolo, pizzicato, cellos, basses - their notes under 0.3 s play real
  short-note recordings by themselves (crisp, as loud as a held note; no pizzicato double
  needed); flutes, piccolo, oboe, english_horn, clarinets, bassoons,
  horns and trombones (real sections), `horn_solo` (one real horn, F2-F5: the voice for a
  tune that must cut through - a call, a hero's line over the band; it carries a tune more
  clearly than the section [H "6b is the best"]), trumpets, tuba, brass (the brass sits drier
  than the strings: less hall), harp, celesta, glockenspiel, bells, organ,
  timpani, solo_violin; voices choir, chorus, men_choir, choir_oo, choir_oh; drums kit,
  taiko, toms, reverse_cymbal (`"patterns"`); real struck percussion, let ring: `gong` (a big
  tam-tam - for transformations and the biggest arrivals; the kit's "gong" is a crash cymbal),
  `anvil` and `brake_drum` (metal hits, sparingly), `bass_drum` (orchestral: weight);
  `guitar` / `guitar_mute`: a real electric guitar through an amp, double-tracked L/R (open power
  chords ringing / palm-muted chugs, B1-E5), `guitar_lead` (its solo voice, one note at a time,
  E2-G5) - only in a boss's later stages (stage 2+ and their
  cues; critic), a surprise, never a bed; power chords only (root5, root, octaves: a third turns to mud).
  `rock_organ`: a rock organ, for stage 3+ only (critic) - the church organ gone wild: chords and riffs, the rotating speaker fast (`"organ"` slows it). Ranges: violins G3-E7, violins2 G3-C7, cellos
  C2-E5, basses E1-C4, flutes C4-C7, piccolo D5-C8, oboe A#3-G6, english_horn E3-A5,
  clarinets D3-G6, bassoons A#1-C5, horns and horn_solo F2-F5, trumpets F#3-A#5, trombones E2-C5, tuba
  E1-A#3, timpani D2-G3, men_choir E2-A4, chorus E2-E6, choir_oo/oh A2-D#6 (critic). A
  low root may fall below a part (an F-minor arpeggio on violins2 starts on Ab3 or C4). A
  part plays one job at a time: where cellos carry the tune, the engine's bass moves to
  the basses; one `"range"` serves every part an entry lists.
- `"title"`: `"<who>: <its real name> (<what it is>)"`. Scores: `music/arrangements/<who>-
  <version>.json`; a boss's cues render to `music/<boss>-<cue>--<title>.ogg`.
- Anything else in the format: the docstring at the top of `lib/music/arrangement.py` -
  look things up, don't read it through.

## 5. The loop
Python: the orchestra's (`.compose-venv/bin/python`, set up by `gm-music-compose.sh setup
--orchestra`), or the one your brief names.
1. Plan in words: one line per section (who carries the tune, what builds, the peak).
2. Write the score.
3. `python lib/arrangement.py make score.json --out piece.ogg`: applies the mechanical fixes
   (writing them into the score), runs the critic, renders only when no ERROR or WARN is
   left. Fix what it reports - each is a rule above; a NOTE is a question: fix it or say
   why it's meant - and run it again.
4. Report: paths, length (and loop point), the critic's last line, where the tune is whole,
   and what the host should listen for, with timestamps.
