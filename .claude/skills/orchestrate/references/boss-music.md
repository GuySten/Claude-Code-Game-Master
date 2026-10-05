# Boss music in stages

A named boss's fight is scored as a small set of cues that follow its stages
(`gm-craft/references/boss-fights.md`): stage loops, transitions, endings. The
research behind this (video-game practice and adaptive-music technique, with
sources) is in the private campaigns repo, `research/gm-design/src-boss-music.md`.
Ordinary fights share one campaign battle cue and get none of this.

## What to score

1. **As many stages as the fight has triggers**: two for a lieutenant, three for an
   arc boss; a finale may add a short **pre-end** loop. Each stage cue answers a
   trigger the GM can name in one line (bloodied, the transformation, the lair
   collapsing). A stage the table can't read is noise.
2. **One identity throughout.** Every stage carries the boss's motif and its concepts,
   on a shared core sound (low strings, timpani...) and the same tempo grid or a simple
   ratio of it. Write the motif once (`"motifs"`) and place it transformed in each
   stage. Game scores almost always vary the boss's theme across phases; an unrelated
   new theme only when the boss turns out to be someone else.
3. **Change two or three things a stage, audibly**: tempo (+8 to 15 a minute, or the
   same tempo with double the motion), key (up a step or a minor third), choir (in at
   stage 2 or 3, not before), density of percussion and ostinato, register (the theme
   an octave up, brass taking it from strings). Loudness or one instrument alone is
   not a stage; everything at once breaks the identity.
4. **Hold back the theme's full form.** Stage 1: the motif in fragments over the drive.
   Stage 2: longer, recoloured. Last stage: the whole theme, recognisable. A theme
   that answers it (the party's, the campaign's) enters only there.
5. **A stage may reveal rather than escalate.** When the second stage shows the boss's
   grief, madness or former self, its cue may be sparser, slower or sacred. Mark it
   `reveal` so the GM knows the drop is meant.
6. **Long loops with change inside.** A table stage lasts 10 to 40 minutes: stage
   loops of 1 to 3 minutes with something new every 8 to 16 bars, so the loop doesn't
   show (`"loop": true`, `"role": "battle"`).

## Transitions and accents (short one-shots, in the next stage's key)

7. **rise** - a one- or two-bar build (timpani roll, cymbal swell, tremolo crescendo)
   landing on the new stage's first chord: for a stage that grows out of the last
   (bloodied, reinforcements).
8. **break** - an impact (tutti hit, low brass and bass drum, choir) dying away into
   3 to 6 seconds of quiet: for a transformation or a reveal. The new stage starts
   after it, while the GM narrates.
9. **hit** - a one- to three-second accent over any stage loop, on the shared tonic and
   fifth so it fits every loop: a shield broken, a decisive blow. At most one a round.

## Endings (one-shots, in the last stage's key)

10. **victory** - a 4 to 10 second cadential tag sized to the boss's rank; then 3 to 10
    seconds of silence; then quiet aftermath music. Never loop the fight into the
    looting.
11. **requiem** - 30 to 90 seconds, through-composed: the boss's motif slowed on a solo
    voice or instrument, modal or minor, ending in silence. For a tragic or pitiable
    boss, instead of the victory tag; the motif never resolves in triumph.
12. **escape** - 4 to 8 seconds: the motif broken off on an unresolved chord. The story
    isn't over.
13. **wipe** - 2 to 5 seconds: a low hit, a falling cluster, then silence. Never back to
    the battle loop.

## Playing them

14. **Switch on the narration of the trigger**, not on the dice. A stage that grows
    out of the last: **rise** into the new loop. A transformation: **break**, the
    pause under the GM's words, then the new loop. A turn the party caused: switch at
    once.
15. **No silence while the boss can act**, except inside a break.
16. **The same names and grammar for every boss** (`stage1`, `stage2`, `stage3`,
    `pre_end`, `rise`, `break`, `hit`, `victory`, `requiem`, `escape`, `wipe`), stage
    loops level-matched, accents a little louder: the table learns to read them.
