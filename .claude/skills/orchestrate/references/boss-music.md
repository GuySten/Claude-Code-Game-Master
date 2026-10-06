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
2. **One identity throughout.** Every stage carries the boss's motif and its concepts,
   on a shared core sound (low strings, timpani...) and the same tempo grid or a simple
   ratio of it. Write the motif once (`"motifs"`) and place it transformed in each
   stage. Game scores almost always vary the boss's theme across phases; an unrelated
   new theme only when the boss turns out to be someone else.
3. **Change two or three things a stage, audibly**: tempo (+8 to 15 a minute, or the
   same tempo with double the motion), key (up a step or a minor third), choir (one
   option: entering at stage 2 or 3 is the common escalation; a finale, or a boss whose
   concepts call for voices, may have it from stage 1 at pad level and open it up later),
   density of percussion and ostinato, register (the theme an octave up, brass taking it
   from strings). Loudness or one instrument alone is not a stage; everything at once
   breaks the identity.
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
5a. **A turn the party may cause gets its own cue, never a place in a stage loop.** When
   the plan has an event the players can bring about in more than one stage - a
   counter-song, a ritual broken, an ally stepping in - and it changes the fight, score
   it as its own loop (`<boss>-<event>`, as long as the plan says it lasts), started at
   once over whichever stage is playing (`music boss "<boss>" stage <event>`) and left
   by the next stage or an ending. Its material - the answering theme above all - never
   sounds inside a stage loop: the table would hear the twist before anyone found it,
   and it might never happen. It keeps the boss's identity in it (the boss's tune, the
   current stage's core sound) with the answer on top.
5. **A stage may reveal rather than escalate.** When the second stage shows the boss's
   grief, madness or former self, its cue may be sparser, slower or sacred. Mark it
   `reveal` so the GM knows the drop is meant.
6. **Every stage opens strong, then builds again.** A stage change is itself a climax
   (the host: "after stage change the music should start strong - there is a kind of
   climax when the boss transforms"; the games: the music restarts in its new form,
   opening with the boss's signature attack - Malenia, FFXIV). So a stage cue is an
   **entry** played once and a **loop body** after it (`"start"` negative, `"loop":
   true, "loop_from": 0`: the table plays the entry, then loops the body without a gap):
   - **the entry**, 1 to 4 bars: most of the stage's forces at once on its new key and
     tempo, the new form's signature figure (stage 2: the motif in its new shape, the
     choir's first entrance), ff. Stage 1's entry is the boss's arrival, at stage 1's size.
   - **the loop body** drops back to the drive (about half the forces) and climbs in
     waves to a peak of its own, holding something back for it (the tune's full form, the
     top register, full brass), then falls back for the seam - not to the entry's level,
     which never comes back. The host on a stage that sat at its full texture throughout:
     "it does not develop into anything... like a climax without the climax".
   - **across the fight**: escalate in colour, not level - tempo, key, density, choir,
     register, how complete the tune's setting is (rule 3). The stage loops are
     level-matched (mastering brings every file to the same loudness; within about 2 LU),
     stings a little hotter. Stage 1's entry is an instant switch into combat; what it
     holds back is colours (the choir opening up, the top register, the tune's grandest
     setting), not size. The fight's single biggest moment is the last stage's.
   The critic checks a stage's entry is strong and judges the climax on the body alone.
7. **Long loops with change inside.** A table stage lasts 10 to 40 minutes: a loop body
   of 2.5 minutes at least (the research: 3 to 5), something new every 8 to 16 bars (a new
   carrier, a breakdown and rebuild, a key move), so the loop doesn't show. One peak a
   cycle: a swell every 30 seconds reads as false escalation - the players trust the
   music's intensity like a barometer (`"loop": true`, `"role": "battle"`; the critic
   warns under 150 s). Write repeats with `"motifs"` and `"repeat"`, not by hand.

## The order of work

First the **stage plan**: every stage's key, tempo and core sound, decided together (a
stage may move its key - up a step, a minor third). Then the stages. Only then the
transitions and endings, written in the keys the stages ended up in: a rise or break in
the key of the stage it leads *into*, the endings in the last stage's key, and one
**hit** per key (`<boss>-hit-stage2` when stage 2 is in another key; the table plays
the current stage's). A workflow test is run as written: a conflict it finds is fixed
in these rules, never by editing a step's output by hand (host: "we are testing the
workflow - you cannot override on a whim").

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


15. **Switch on the narration of the trigger**, not on the dice. A stage that grows
    out of the last: **rise** into the new loop. A transformation: **break**, the
    pause under the GM's words, then the new loop. A turn the party caused: switch at
    once.
16. **No silence while the boss can act**, except inside a break.
17. **The same names and grammar for every boss** (`stage1`, `stage2`, `stage3`,
    `pre_end`, `rise`, `break`, `hit`, `victory`, `requiem`, `escape`, `wipe`), stage
    loops level-matched, accents a little louder: the table learns to read them.
