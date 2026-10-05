---
name: orchestrate
description: Compose and orchestrate the game's music as written notes for the sampled orchestra (JSON scores played by lib/arrangement.py) - a character's theme or anthem at any point of their story (seed, theme, heroic, legendary, wounded, bonded, darkened), a dark twin, a villain's theme, a boss-fight loop, or any piece the table needs. Use it whenever music is to be written, arranged, revised or judged - including when the host says a piece sounds wrong ("I can't hear the choir", "too quiet", "boring", "doesn't sound like him"), asks for a new version of someone's music, or a story moment calls for a theme to change - even if they don't say "arrangement" or "orchestra".
---

# Orchestrate

You write the music the way a film composer does: the character's tune comes from
the leitmotif generator (it is theirs, always exact), and you decide everything
around it - who plays it when, the harmony under it, the countermelodies, the
build, the climax, the ending. The orchestra (real instrument recordings) plays
what you write.

**You can't hear.** Everything you know about how a piece sounds comes from two
places: the score critic (`arrangement.py check`, which renders the piece and
measures what a listener would notice) and the host's ears. Your past mistakes
were all things a listener heard at once - a choir 20 dB too quiet to exist, a
tune buried under its own accompaniment, violins too slow to speak quick notes.
So the loop below is not optional ceremony; it's how you hear.

## The loop

0. **Main characters: write the tune yourself** (the host clearly preferred
   hand-written tunes to the generator's): `references/tunes.md`. Write three
   candidates, different in hook and rhythm, and let the **host judge** pick
   (below). Everyone else gets the generator's (gen 2).
1. **Read the tune.**
   `python lib/arrangement.py tune "<seed>" --class <Class> [--minor] [--stage N] [--dark N]`
   (on the host's laptop: `bash tools/gm-music-compose.sh tune "<name>" [--minor]`).
   It lists every note with its time, the key, meter, mode and length. The seed is
   the character's name exactly as the table knows it (a Hebrew name stays
   Hebrew); `--minor` is the villain's version of a tune (villains, dark twins).
2. **Plan in words first** - a short paragraph per section: who carries the
   tune, what the harmony does, how it builds, what the climax does that nothing
   before it did, how it ends (or how a loop rejoins its start). Deciding this
   before the JSON is what makes a piece *composed* rather than filled in.
3. **Write the score** as JSON (the format: the docstring at the top of
   `lib/arrangement.py`; read it the first time). Save it in the campaign's
   `music/arrangements/<who>-<version>.json`.
4. **Run the critic** - `python lib/arrangement.py check <file>` - and fix every
   ERROR and WARN. Each NOTE is a question: confirm it's what you meant (a
   half-step sigh you wrote on purpose) or fix it. Re-run until clean. The critic
   names the fix it expects ("gain": 5, a doubling, a range): take it unless you
   have a musical reason not to.
5. **Play it** - `python lib/arrangement.py play <file> --out <file.ogg>` (laptop:
   `gm-music-compose.sh arrange <file>`).
6. **Rate it** (when the rater is set up: `gm-music-compose.sh setup --rater`) -
   `python lib/music_rate.py <file.ogg>`: Meta's Audiobox Aesthetics, 1-10, for
   enjoyment, usefulness, complexity, production quality. Know what it hears: the
   *sound*, not the music. It couldn't tell the host's favourite tune from the one
   they found lacking (a tune alone on a clarinet scores 7.2-7.6 whatever the
   notes), a lone clean instrument outscores a full orchestra, and an independent
   review (Cyanite, 2026) found its scores cluster at 7-8 across genres and track
   catchiness and familiarity rather than merit. So use it for coarse problems
   *within* a piece - a wrong note in one part (it caught a trumpet tritone), a
   squashed passage, a weak instrument - and to compare two mixes of the same
   arrangement. Never to choose a tune, and never as a verdict on the music:
   that's the host's ears (and, for tunes, `lib/tune_score.py` as a floor check).
7. **Tell the host what to listen for** - timestamps and what happens there ("0:24
   - the climax lands on E major instead of home: the lift"), and ask what doesn't
   work. When they answer, record it in `references/table-feedback.md`: their
   ears are the final judge, and that file is how the next piece benefits.

Run the scripts with a Python that has numpy, soundfile and tinysoundfont (the
host's `.compose-venv`, set up by `gm-music-compose.sh setup --orchestra`).

## The host judge: the host's taste, so they only listen when it matters

The host can't audition everything, and can't tell a 9 from a 10 - nobody can;
people judge pairs, not scores. `lib/host_judge.py` approximates their taste with
the judges that matched their verdicts (the audio models, Audiobox and SongEval,
did no better than a coin flip on our music):

- **Tunes are chosen by their finished music, not alone.** The host put it
  plainly: which tune they like bare isn't which makes the best piece once the
  orchestra is added (in the 2x2, the simpler tune richly set matched the bold
  one plainly set). So bare-tune judging only narrows the field:
  `host_judge.py tunes prepare a.json b.json c.json --out DIR` drops red-flagged
  candidates and writes blind pairs; a **fresh agent** (it must not know which is
  which, or that one is yours) reads `DIR/README.txt` and writes
  `DIR/verdicts.json`; `host_judge.py tunes decide DIR` names two **finalists** -
  candidates that also hold up as a leitmotif in every form (seed, heroic,
  legendary, darkened, the villain's: `versatility`).
- **Then the finals:** arrange each finalist for the same role with the same care,
  budget-matched (a bold tune plainly set, a simple tune richly set), check both
  clean, and `host_judge.py finals prepare a-score.json b-score.json --out DIR`;
  a fresh agent reads the scores blind; `host_judge.py finals decide DIR` picks
  the piece - and with it the tune.
- **Arrangements:** the critic clean, and the surprise budget balanced.
- **Close calls only go to the host:** when `finals decide` says `ask_host`, send
  the two finished pieces (`host_judge.py clips a-score.json b-score.json --out
  DIR`) and ask which they prefer - "can't tell" is a fine answer. Never ask the
  host to choose between bare tunes for the final pick.
- **Record every preference the host states** - an A/B answer, or "this one's
  better" about anything - with `host_judge.py record WINNER.json LOSER.json
  [--tie] [--note "their words"]`. Their verdicts live in the campaigns folder
  (`taste/verdicts.json`); `host_judge.py validate` re-checks the automatic
  judges against all of them - run it after changing a rule, and if agreement
  drops, the rule is wrong, not the host.

## What makes it good

**The tune is sacred; everything else is yours.** Never change its notes - that
is what makes it recognizable across a campaign. Vary the instrument carrying it,
its octave, the harmony under it, the tempo, the texture. A theme heard as a lone
horn, then soaring violins, then the whole orchestra is one theme growing up.

**Pass the tune around.** Each section of the tune (its statements, its climb, its
return) gets a different carrier, and the carrier should *mean* something: a solo
voice is intimate or lonely, horns are noble, trumpets triumphant, low brass
menacing, a choir is fate. The first statement is usually the smallest.

**The climax grows out of what came before.** The host's ear catches a seam at
once ("the climax did not go with what was before"): never drop what's playing and
start a new set of instruments in one bar. Keep the accompaniment that defines the
piece (its pulse, its bass, its pad) running through every section, carry a line
across each seam (the tune's old carrier turns countermelody), build the bars before
the climax (a crescendo, a roll, a rising line), and bring new instruments in waves -
a few bars apart. The critic warns at a seam or a sudden doubling of the orchestra.

**Build to one climax, then make it different.** Dynamics rise toward the tune's
highest note. Give that moment something nothing before it had: a harmonic
surprise (a chromatic mediant like bIII or bVI under the held top note), the
first cymbal, the choir's entry, a timpani roll into it. Afterwards, the return
home is the fullest statement, and the ending is decided - a held chord with a
roll and a final stroke, a ritardando, or a last quiet echo of the tune.

**Develop the theme; don't just state it.** One pass through the tune is a
sketch. A composed piece takes the theme somewhere: a second statement that is
*different* (a key change up a step or a third - "keys" plus a statement
"shift" - a new harmonization, a new carrier and texture), the hook alone tossed
between instruments (call and response, a sequence climbing through keys), a
breakdown to almost nothing and a rebuild, a countermelody that later becomes the
main line. In side-by-side tests the more developed versions (a modulated second
statement, a breakdown) were rated higher than compact ones. Let the piece be as
long as its development needs: themes ~40-60 s, legendary ~50-75 s, battle loops
~75-120 s - not padding, but more happening.

**Keep several lines moving.** Think in layers: the tune; an answer or
countermelody; a rhythmic engine (an ostinato, a walking or pulsing bass,
arpeggios - harp, pizzicato, strings); harmony (pads); percussion. A pad only
changes chords - it isn't motion. Where the tune holds a long note, something else
should move. Big music (battle, the legend's return) keeps three or more lines
in motion at once besides the tune; the critic counts them (give a battle score
`"role": "battle"`). The professional tracks that outscored ours were the denser
ones.

**Spend the surprise once: the tune or the setting.** In the host's 2x2 test
(a simple vs a surprising tune, in a supportive vs a rich arrangement) the
winners were the simple tune richly set and the surprising tune plainly set;
both-plain and both-rich were weaker. So a bold, surprising tune gets plain,
supportive harmony and no key change - let it lead; a simple tune gets the key
change, the chromatic lift, the breakdown. The critic measures both (the tune's
surprise against real tunes, the setting's chromatic chords and key changes)
and notes an unbalanced pair.

**Harmony that moves, and moves with intent.** Change chords every half bar to a
bar; hold one longer only for effect. Use the mode's own colour (bVII in
Mixolydian, bII in Phrygian, #IV in Lydian) and end with a cadence that fits:
bVII-I epic, V-I classical, bII-i Phrygian dread, bVI-bVII-I triumphant. The
device catalogue: `references/harmony.md`.

**Respect what the instruments can do.** Every instrument has a range, and some
recordings speak slowly (the choir takes ~1.2 s to bloom, violins ~0.5 s): quick
notes on them smear into nothing. Double quick passages with a quick instrument
(horns, trumpets, flutes, clarinets, bassoons, pizzicato) - the quick one gives
the attack, the slow one blooms behind it. A choir sings held chords of a beat or
longer, never rhythms; brass and drums carry rhythm. Details and a table:
`references/orchestration.md`.

**The tune on top.** The tune's notes are mixed as their own layer ("lead", 4 dB
by default); the critic measures each section and wants the tune at least ~1 dB
over everything else (aim for +3). Every instrument is already evened out (the
same velocity is the same loudness), so balance by writing - fewer parts, softer
pads - and by "gain" on a melody entry, before reaching for "mix".

**Loops (villain themes, battles) have no ends.** No ritard, no final stroke; the
end's dynamics and texture must meet the start's (the critic measures the seam).
Start and end on a vamp or ostinato over the tonic so the wrap is invisible; put
the intro's material at the end of the cycle too.

## From concepts to a brief (the translator)

A character, place or moment stands for concepts (holiness, nobility, cunning, decay,
the sea, a farewell...); `references/concepts.md` translates each into music, from the
research and the documented conventions (189 concepts, each with Cues, Melody, Harmony,
Colours and devices, With / against, Intensity, Not). Before composing, write the
composer's brief this way - the same for every character, so nothing is tuned to one:
1. **Concepts.** From the description (npcs.json, the world bible, their deeds, how the
   host defines them), list the concepts and weigh each: the one that *carries* the piece,
   the *strong* ones, the *colours* - only **distinctive** concepts, what sets this subject
   apart; the subject's **defining trait carries**. A battle or a lament is the cue's job,
   the frame (the format's `role`: tempo, drive, form), never a concept - combat and war only
   where the fighting is the subject (a war, a siege, a defining duel). Always decide **stature** (how much they weigh in the
   story: a king or archvillain gets one grand climax, a minor figure stays small).
   Find them in `references/concepts-index.md` (keywords per concept).
2. **Read only those entries** in `concepts.md` (search "#### <name>"), and its section 1
   (how concepts combine: agreeing cues add up; conflicting ones go on different layers
   or moments, never averaged; a short piece carries one or two ideas, layered).
3. **The brief:** at most ~200 words, in musical terms - tempo and pulse, register,
   colours, articulation, harmony, dynamics and how big it gets, texture, the melody's
   shape, the devices and how they relate, what to avoid. Name the concepts used (so a
   weak result can be traced to an entry). No section-by-section plan: that's the
   composer's.
4. The composer writes from the brief, the tune and the format; the critic checks; the
   host listens. A verdict on character goes into `table-feedback.md` and, if it shows an
   entry is wrong, into that entry - never as a patch for one character.

## Characters: a portrait in devices

A character's music is a portrait, not a mood: read who they are in the campaign
(npcs.json, the world bible, their deeds) and build their piece from the **character
devices** in `references/devices.md` - the façade, the madness, the lament, the power,
the corruption... - each with how to write it, the convention and evidence behind it,
and the host's verdicts; its trait table maps a description to devices. Some are code
(`lib/devices.py`: `madness()`). Ask the host for a brief in their own words when you
can (their reference pieces taught more than any measurement), and for one listen at
the end: no model judges a piece's character for them (`table-feedback.md`).

## Pieces and versions

What each kind of piece needs - a hero at each story stage, wounded, bonded,
darkened, the legendary finale, the dark twin, a villain's theme, a boss fight -
is in `references/recipes.md`. Worked examples, with the choices that made them
work: `references/examples.md`. Full scores from play live in the campaign's
`music/arrangements/` folder - read one before writing a similar piece.

## When the host says something sounds wrong

Believe them over any measurement, then find out why with the critic: render the
part they mention alone against the rest (see the "listening" checks in
`check()`), compare levels, check what that instrument can do. Fix the cause
(the writing, a missing doubling, a balance), not just that one piece - if it's
a rule, add it to `references/orchestration.md` or `table-feedback.md`, or a
check to the critic, so it doesn't happen again.
