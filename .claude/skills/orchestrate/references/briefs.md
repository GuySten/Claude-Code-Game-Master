# Briefs: what the piece must make the table feel, before how

The brief is where most of the host's verdicts were lost. The composer did what the brief said;
the brief said the wrong thing (a king's theme asked for narrow dynamics and no brass; a fallen
champion's for brass stabs with falling tails; a player character's for a rage held down for the
whole piece; a boss's second stage for "her core sound goes on", then for "rapture... an ecstatic
fire-dance"). Each line of those briefs was a faithful translation of a word; nobody had stated
what the whole should make the table feel and checked the lines against it. The research says
the same of film practice: directors brief the story and the feeling, composers choose the
means, and briefs fail by ambiguity, missing context and precise-sounding instructions that
misstate the intent (`research/music-sources/composer-briefs.md` in the campaigns repo).

This file is the whole brief process, for every piece: themes, villains, places, boss stages.
The GM writes the brief (`SKILL.md`); `concepts.md` and `devices.md` are where the means come
from, never where the brief starts.

## The order

1. **Read what the host has said about this kind of piece** (below) and the subject's notes
   (npcs.json, the world bible, their deeds, how the host defines them).
2. **Write the Job** - one sentence: what the table must feel by the last bar, and why music
   plays here. Everything after it serves it.
3. **Fill the rest of the brief** (the template), every prescriptive line with its "because"
   pointing at the Job.
4. **Read it as the table will hear it**: imagine the sound the instructions make (tempo, mode,
   register, colours, a dance or a march), ignoring the brief's own labels, and say in a
   sentence what a listener would feel. If that isn't the Job, the brief is wrong.
5. **Review by a fresh agent** (`brief-review.md`): it gets the brief, a subject card and the
   host's verdicts for this kind - not the GM's reasoning - and answers PASS or REVISE. A
   REVISE is about the feel: fix the brief and review again. Its craft notes go to the
   composer with the brief. Checked blind on ten past briefs, each with only the verdicts
   that existed then (`research/brief-review-validation/` in the campaigns repo): it caught
   five of the seven the host rejected - every one whose overall feel contradicted the role -
   and passed the near-good one; it misses craft faults no verdict has named yet, and it holds
   the verdicts strictly. It is a check before the host's ears, never instead of them.
6. **Store it** in the campaign: `music/briefs/<cue stem>.md` (the brief, the review, and later
   the host's verdict on the piece), so a verdict traces to the brief line behind it.

For a boss, steps 2-5 are the **intent page** of the stage plan - each stage's Cue, Job, Fable
(what changed in the story), Ideas and Not-this - written and reviewed before any bar map
(`boss-music.md`, "The order of work"). The bar map is mechanics; it can't fix a wrong intent.

## The template (one line or a few per field; about 250 words)

```
Cue:        what it is and where it plays at the table - role, length, loops / ends
Job:        what the table must feel by the last bar, and why music is here (one sentence)
Fable:      2-4 sentences from inside the subject now - one concrete image or line
Ideas:      the one that carries + colours, as many as the length holds (P4); named
            concepts or devices, each with what it means here
Sound:      meter, tempo, mode, who carries the tune and where it passes - each with
            "because ..." when it matters
Shape:      where it grows, where the peak falls, how it ends (or how the loop seams)
Ours:       optional - up to two of our own pieces, each "take: ... / leave: ..."
Not this:   1-3 exclusions, each with its reason (what it would make the table feel)
Fixed/free: which lines are musts; where the composer should surprise
```

Name only the orchestra's own parts (the parts list in `lib/music/arrangement.py`'s
docstring): there is no viola section - a viola line is `violins2` in the viola register.
Describe a sound by an adjective, an image and a contrast ("lonely, like one lantern on a
moor; not sad-romantic"), never a bare adjective.

## The principles (each stated once; the host's verdicts behind them are in `table-feedback.md`)

- **P1. The cue's role sets the emotional bounds.** A boss is always the enemy: every stage
  carries negative emotion - menace, dread, fury, agony, despair - and the boss's concepts are
  their dark forms (`concepts.md` R18: holiness -> corrupted holiness, power -> tyranny). A
  villain's menace keeps momentum and control; darker is not slower, and slow and low reads as
  mourning. A player character is a protagonist, never a minor figure: their theme states who
  they are with conviction (R17). A word that fits the concept but not the role (rapture,
  light, dance, play, a major cadence in a boss stage) is wrong in this brief.
- **P2. The subject's defining trait carries; the cue's job is the frame.** A battle, a lament
  or a march is the form (the `role`: tempo, drive, a loop), never a concept. Only distinctive
  concepts: combat and war only where the fighting is the subject (a war, a siege, a defining
  duel); heroism for paladins and heroes, not every adventurer - a situation's concept is a
  moment, played as the subject's own theme in that form. A defining trait sits in the
  foreground, never a subtle layer.
- **P3. Stature sets the peak.** A king or archvillain gets one grand climax, however
  restrained the surface; a minor figure stays small.
- **P4. As many ideas as the length holds** (about one per 15-20 s; one carries). A portrait
  of who they are, not a retelling of what they did. A player character's theme holds only
  what the story has made of them so far.
- **P5. A boss's later stage is built on what changed in the story,** inside P1: its own pulse,
  lead, harmony, register and choir role; the earlier stage's concepts recede or drop out; only
  the tune carries over. The goal is the stage's Job, not contrast: the opposite of stage 1 is
  not a stage.
- **P6. A verdict says what was felt; it never points to the opposite pole.** When answering
  one, restate the Job and ask which feeling was missing ("the change is minimal" asked for a
  new world of the same enemy, not for brightness; "leashed" asked for conviction, not for
  noise; "not dark enough" asked for evil, not for gloom).
- **P7. Recipes, research examples and lexicon entries give means.** A means that doesn't serve
  the Job is dropped however well sourced; the host's verdicts override all of them. A lexicon
  entry has several readings (fire as light or as destruction); the Job picks the reading.
- **P8. Every prescriptive instruction carries its reason,** so the composer can keep the
  intent if the means must change; a composer who finds a line that contradicts the Job or
  the role raises it before writing.

## What the host has said, by kind

Read the list for the piece's kind (and "Every piece") before writing the Job; give the same
list to the reviewer. When a verdict comes in, add one line here under its kind, and the full
entry in `table-feedback.md`.

**Every piece**
- A choir must be clearly heard; the tune sits on top of everything.
- A climax arrives (something new) and grows out of what came before - never a set of parts
  swapped in one bar.
- The sound set's strengths, blended: held strings as the bed, the tune in a blend (flutes +
  clarinets, horns + violins, octave tutti); a dry bare-fifth riff or brass alone on the tune
  sounds weak.
- Falling bends on brass or low reeds are comic ("it sounds like he farts").
- Too much story in a short piece feels dense; repetition of the whole tune feels repetitive.

**Villain themes**
- A king-like villain needs a grand, epic climax (stature); narrow dynamics with no brass missed it.
- "Good for a grey villain, not a really evil mastermind": evil needs low, dark colours and tense
  harmony, with momentum - the slow, gloomy rewrite "sounds less evil".
- The host's evil: a character portrait (madness, isolation, inevitability) - Homelander's lone
  fast, jarring high violin; Evil Morty's sad human choir (a villain may mourn, sung).
- An evil mastermind (the Margrave): low, dark colours - no harp, no plucked lightness; tense
  diminished chords for the bright dominants; a pedal under it; dissonant low choir and organ at
  the climax; an ending that never resolves. A villain needs two pieces on the tune: the theme,
  and a battle piece (fast, an ostinato engine, drums).
- A complex villain is a portrait in layers, each heard at its moment ("the Margrave is a complex
  character"): the face (his elegant waltz), the guilt (a mourning choir), the power (the climax),
  the mind fraying (the violin). The portrait built this way: "dramatically better".
- Madness is instability, not crispness ("too crisp - it signals structured evil"): a violin that
  plays along with the orchestra and suddenly misbehaves - "turns too high, breaks pitch and
  stride"; the strings follow its madness when they accompany it. Audible all through ("I
  thought we agreed it should accompany the whole piece"); each flash short and growing ("every
  madness is felt clearly, so it should not take a lot of duration"); the piece starts briefly
  and ends with the violin alone.

**Boss fights**
- Combat is the frame; the boss's defining trait carries, in the foreground ("the corruption is
  too subtle for a main feature").
- Each stage starts strong (a transformation is a climax) and the body keeps that energy ("it
  dies after the transformation").
- The table must recognise the tune in every stage; a stage needs its own peak with something
  held back.
- A later stage "should feel nothing like stage 1 except the tune", focused on the new concept,
  the old ones in the background or gone; turning stage 1's dials is "minimal".
- Fire written as sparkle (harp, glockenspiel, celesta, flute rings) reads as magic.
- Fast, bright, high with the bass thinned reads as "playful... certainly not boss music".
- "A boss is always the bad guy": every stage negative; holiness corrupted, power as tyranny.

**Player-character themes**
- The liked model (Kestrel's original, 34 s): a deep low bass alone at the start, the tune once,
  passed round the orchestra and growing every phrase, a hope chord, the peak at about two-thirds
  ("exceptional": the tune in three octaves over the choir), trumpets saved for the climb, a
  release and a decided close. "It's not always good to start strong."
- "Stronger impression, strong character": a trait held down for the whole piece makes a weak
  theme. Shorter is better than two or three whole statements.
- Heroism belongs to heroes, not every player; a theme grows with the character's story.
- Izrin (a poised killer in hiding), a 6/8 prowl at about 60 in dorian, rising in a dark blend: liked
  as music, "but it does not suit an assassin" - it read as brooding and wistful, not cold menace.

**Places and moments**
- No host verdicts yet; the research is in `research/music-sources/place-music.md`.
