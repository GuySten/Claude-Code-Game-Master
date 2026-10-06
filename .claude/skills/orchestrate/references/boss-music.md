# Boss music in stages

A named boss's fight is scored as a small set of cues that follow its stages
(`gm-craft/references/boss-fights.md`): stage loops, transitions, endings. The
research behind this (video-game practice and adaptive-music technique, with
sources) is in the private campaigns repo, `research/gm-design/src-boss-music.md`.
Ordinary fights share one campaign battle cue and get none of this.

## What to score

1. **As many stages as the fight has triggers**, never more than four: two for a
   lieutenant, three for an arc boss (the rank is the GM's, in the boss's stage plan: a
   one-shot's boss may be an arc boss - `gm-craft/references/boss-fights.md` 1); a finale may add a short **pre-end** loop (30-60 s,
   high intensity, no melodic development, its last bar resolving into every ending;
   the GM plays it when the boss is one blow from falling or the last countdown starts). Each stage cue answers a
   trigger the GM can name in one line (bloodied, the transformation, the lair
   collapsing). A stage the table can't read is noise.
2. **The tune is the one thread.** Every stage carries the boss's tune (through `"tune"` and
   `"statements"`; only a statement counts as stated whole, `composing.md` 5) - and only the
   tune. Everything else belongs to the stage: a later stage feels like nothing before it
   except the tune [H, the Ashen Saint: "stage 2 should feel nothing like stage 1 except
   the tune"]. An unrelated new theme only when the boss turns out to be someone else.
3. **A later stage is a new world, built on its new concepts.** What changed in the story
   (the flame takes her, the mask falls) carries the stage; the earlier stage's concepts sit
   in the background or drop out [H: "it should focus on the new concepts; the old ones
   should be in the background or maybe even not at all"]. Change the pulse (a new rhythm,
   not the same drive faster), the instruments that lead, the harmony, the register, the
   choir's role - and the tune's setting with them. Turning dials on stage 1's sound is
   not a stage [H, the Saint v6: a step up, +12 bpm and a choir on the same march - "the
   second stage does not have more emotion; the change is minimal"]. The engine masters
   each later stage louder than the one before (`"stage": N`).
   **A boss is always the enemy: every stage carries negative emotion** - menace, dread,
   fury, agony, despair - and a "holy", "beautiful" or "ecstatic" concept is heard as a
   threat, never as joy or rapture [H: "a boss is always the bad guy so all his stages should
   carry negative emotions"]. Its concepts are their dark forms: holiness is corrupted holiness, power is
   tyranny (`concepts.md` R18). **A new world is still a boss's world:** every stage keeps low weight and menace
   (`composing.md` 7). Fast, bright and high with the bass thinned reads as playful, whatever
   the story says [H, the Saint's 6/8 fire-dance in F# major colours, piccolo and high choir
   over a thinned bass: "read as playful... certainly not boss music"]. A recipe or a
   research example never overrides a host verdict.
4. **The table must know the tune first; hold back its grandest form, not its notes.**
   A leitmotif is recognised in a reprise far more easily than in a variation, and stage 1
   is where the players learn the boss (the host could not tell whether a stage 2 had
   stage 1's tune). So every stage loop states the tune **whole, as written** at least
   once (a statement; a new key or register is fine - the critic checks), its hook
   more often. Vary it in ways that keep it recognisable: key, register, the carrier,
   slower or faster note values, the head phrase alone, new harmony under it. Inverted,
   reversed or altered notes only for a story reason (the corruption bending the tune),
   and after the tune has been heard straight. Held back for the last stage: the tune's
   biggest setting (full brass and choir, the top register). A theme that answers it
   (the party's, the campaign's, an ally's) enters only there - or in the cue of the
   turn that brings it (below).
4b. **A villain's fight is his, but never his theme again.** Recognition and "too similar" are
   separate judgements [R: `research/music-sources/villain-battle.md`]: the tune is recognised by its
   hook - the first 5-7 notes' exact intervals and their long-short pattern - while similarity is
   heard mostly in the surface - the instruments above all, then texture, groove and articulation
   [H, the Margrave's stage 1 on his theme's meter, tempo, key, carriers and waltz engine, with drums
   added: "a bit too similar to his theme"]. So: **keep** the hook's intervals and long-short pattern,
   stated clearly and exposed within the first 8 bars and again every 20-30 s, and one or two of his
   signature colours in a new job; **always change the carriers** (the theme's tune instruments drive
   the engine instead); **and change at least two more, decisively**: the engine (never the theme's
   accompaniment, never the hook looped in its own rhythm - build it from his harmony or a 2-3-note
   cell of the hook, re-rhythmed), the meter feel (every beat struck, or a new grouping, within the
   tempo cap), a distant key, a moving harmonic loop in place of a pedal, fragment-and-develop form.
   A mode change, added drums or more volume alone never make the difference. The whole tune, when it
   comes, comes in a form the theme never used.
5. **A turn the party may cause gets its own cue, never a place in a stage loop.** When
   the plan has an event the players can bring about in more than one stage - a
   counter-song, a ritual broken, an ally stepping in - and it changes the fight, score
   it as its own loop (`<boss>-<event>`, as long as the plan says it lasts), started at
   once over whichever stage is playing (`music boss "<boss>" stage <event>`) and left
   by the next stage or an ending. Its material - the answering theme above all - never
   sounds inside a stage loop: the table would hear the twist before anyone found it,
   and it might never happen. It keeps the boss's identity in it (the boss's tune, the
   current stage's core sound) with the answer on top.
6. **A stage may reveal rather than escalate.** When the second stage shows the boss's
   grief, madness or former self, its cue may be sparser, slower or sacred. Mark it
   `reveal` so the GM knows the drop is meant.
7. **The stage plan names each stage's score `"role": "stage"`** (a turn cue `"turn"`, the
   pre-end `"pre_end"`). **How a stage is written** - its strong entry, a body that keeps that energy, the breakdown,
   the one peak that brings something new, the length - is the composer's recipe:
   `composing.md` ("Boss stage"). This file plans the fight; that one writes it.

## The order of work

First the **intent page** (`briefs.md`): for each stage its Cue, Job (what the table must feel - always a threat, rule 3), Fable (what changed in the story), Ideas and Not-this, written before any notes and reviewed by a fresh agent (`brief-review.md`); a wrong intent can't be fixed in a bar map. Then the **stage plan**: every stage's key, tempo, carrying concept and own sound, decided together, and each stage's **bar map** - its entry and body sections as bar ranges (drive, statements, breakdown, rebuild, peak, fall-back), laid out on `arrangement.py grid` - so the composer fills a map instead of designing one (a
stage may move its key - up a step, a minor third). The plan is the composer's whole brief:
one role and one length (the bar map's), rule numbers from `composing.md`, and every sound it
names ("the engine", "the pedal") said in parts and notes, with the double a quick string
figure needs (`composing.md` 22) - a contradiction or a guess costs a composer minutes of thought.
Before handing it over, check the plan against the rules a composer will meet:
- **The bar map still serves the reviewed Job:** every feeling word or device in it is read against "this is the enemy" (rule 3; `briefs.md` P1). A composer who finds a line that contradicts it raises it before writing: a plan never overrides what the cue is.
- **Ranges**, in the stage's key: every figure inside its part (`composing.md` §4 - violins2
  can't take an F-minor root at F3).
- **One job per part at a time**: where the tune is on cellos, say who takes the engine's bass.
- **Every join says what carries across** (rule 3): a section that returns after a breakdown
  creeps in under what precedes it (the engine re-enters under the count), never all at once
  on a bar line.
- **The hook** is the notes `tune` marks: give its length in units, and make any slot for it
  fit it - or say which notes go there.
- **Parts, not families or adjectives** ("violins and cellos", not "strings"; "trumpet
  stabs off the beat", not "outbursts"); a range written as a range (`clarinets, range
  C4-Ab4`), notes as notes; a lift as a `keys` shift ("bars 57-60: keys +3"). Then the stages. Only then the
transitions and endings, written in the keys the stages ended up in: a rise or break in
the key of the stage it leads *into*, the endings in the last stage's key, and one
**hit** per key (`<boss>-hit-stage2` when stage 2 is in another key; the table plays
the current stage's). **Once the plan is written, compose in
parallel:** one composer per stage, and the stings in two (transitions and hits; endings),
all started together - the plan has fixed every key, so none waits on another (a whole
two-stage fight took about 20 minutes this way instead of 35 staggered). Each composer works
from `composing.md`, not the whole skill. A workflow test is run as written: a conflict it finds is fixed
in these rules, never by editing a step's output by hand (host: "we are testing the
workflow - you cannot override on a whim").

## Promoting a boss (a stage added later)

The GM may promote a boss whose fight is already scored - a lieutenant who escaped returns
as the arc boss (`gm-craft/references/boss-fights.md` 1). The new stage is planned like the
first ones (the stage plan first: its key, tempo, its own sound and concept, entry), with three things the
earlier stages already decided:
- **What the table has heard stays.** The tune and stages 1-2 as played are the boss's
  identity now; the new stage carries the tune into its own new world (rules 2-3).
- **The arc is re-planned with the new stage at its top** (rule 4 and `composing.md` 18: the fight's biggest
  moment is the last stage's). If the old last stage spent everything - full brass, the open
  choir, the tune's top register - either re-score that stage's peak to hold something back
  (only when the table hasn't heard it fight in that form, or a session has passed), or let
  the new stage arrive with something new rather than louder: the answering theme (an ally's,
  the party's; rule 4), a new tempo or key (a step up; mind chained lifts - self-parody),
  or a reveal (rule 5). Never louder alone (rule 3).
- **The endings move to the new last stage's key** (rules 11-14): re-render requiem, victory,
  escape and wipe; add the new stage's transition and its `hit-stageN`.
Record the promotion in the boss's stage plan (the rank, why, what changed).

## Transitions and accents (short one-shots, in the next stage's key)

8. **rise** - a one- or two-bar build (timpani roll, cymbal swell, tremolo crescendo)
   landing on the new stage's entry - its `"length"` ends exactly on that downbeat (the
   file says where: the table starts the new stage there while the rise's reverb rings,
   and the old loop plays on under the build): for a stage that grows out of the last
   (bloodied, reinforcements).
9. **break** - an impact (tutti hit, low brass and bass drum, choir) dying away into
   3 to 6 seconds of quiet: for a transformation or a reveal, under the GM's narration;
   then the new stage's entry lands - the transformation's climax - and its loop runs on.
   The impact cuts the old loop; its `"length"` covers the quiet (the new stage starts
   there).
10. **hit** - a one- to three-second accent over a stage loop, on that stage's tonic and
   fifth (one per stage key): a shield broken, a decisive blow. At most one a round.

## Endings (one-shots, in the last stage's key)

11. **victory** - a 4 to 10 second cadential tag sized to the boss's rank; then 3 to 10
    seconds of silence; then quiet aftermath music. Never loop the fight into the
    looting.
12. **requiem** - 30 to 90 seconds, through-composed: the boss's motif slowed on a solo
    voice or instrument, modal or minor, ending in silence. For a tragic or pitiable
    boss, instead of the victory tag; the motif never resolves in triumph.
13. **escape** - 4 to 8 seconds: the motif broken off on an unresolved chord (or, with
    no escape cue, the loop faded over 3 to 5 seconds). The story isn't over.
14. **wipe** - 2 to 5 seconds: a low hit, a falling cluster, then silence. Never back to
    the battle loop.

## Files and playing them

Render each cue to the campaign's `music/` as `<boss>-<cue>--<its real title>.ogg` (the
boss's name as a file stem, then the piece's own name: `ashen-saint-stage2--the-flame-takes-her.ogg`,
`countess-isolde-varnay-requiem--i-was-only-isolde.ogg`). The table finds a cue by what comes
before `--` and never shows what comes after: the title is for the host to learn after the
campaign, so it may name what the players haven't found yet. The GM plays them with
`gm-table.sh music boss "<boss>" stage N|pre_end|<event> [--via rise|break]`, `... hit`, and
`... end victory|requiem|escape|wipe`. A boss's cues cut in on time on every player's
page (combat starts at once; no fade-in): a rise builds over the old loop and the new
stage starts where the rise lands; a break's impact cuts the old loop and the new stage
starts after its quiet; an ending cuts the loop under its attack. The stage's entry plays
once, then its body loops (`"loop_from"`).


## At the table

14a. **An introduction only where the encounter has one.** When the boss is revealed slowly (a chapel
    entered, a ritual interrupted, words exchanged), their theme can play before initiative as the
    suspense, and the stage-1 entry lands when the fight begins. Not every boss gets one (the host: "not
    every boss should have a suspenseful introduction"): an ambush, a brawl or a boss who strikes first
    goes straight into the stage-1 entry. From initiative on, a stage is dark and exciting, never only
    dread - unless the story says otherwise and the Job names it (the host: "most fights should be
    energetic unless for example the party avenge a fallen comrade": grief turned to resolve).
15. **Switch on the narration of the trigger**, not on the dice. A stage that grows
    out of the last: **rise** into the new loop. A transformation: **break**, the
    pause under the GM's words, then the new loop. A turn the party caused: switch at
    once.
16. **No silence while the boss can act**, except inside a break.
17. **The same names and grammar for every boss** (`stage1`, `stage2`, `stage3`,
    `pre_end`, `rise`, `break`, `hit`, `victory`, `requiem`, `escape`, `wipe`), stage
    loops level-matched, accents a little louder: the table learns to read them.
