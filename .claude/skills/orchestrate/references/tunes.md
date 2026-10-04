# Writing a character's tune

The host preferred tunes written by hand to the generator's, clearly. Write the
tune of every main character (the party, the main villains); the generator
(gen 2) covers the rest. A written tune uses the generator's own shape, so its
villain version, story stages and darkening all still work:

    {"seed": "<their name>", "meter": "6/8", "mode": "mixolydian", "kind": "jig", "hook": 5,
     "pickup": [], "motif": [[0,1],[4,1],[5,1],[7,2],[6,1], [4,1],[5,1],[4,1],[2,3]],
     "again": [...], "climb": [...], "home": [...]}

Degrees in the mode (0 the tonic, 7 the octave, negative below), lengths in units
(beats, or eighths in 6/8). Modes: ionian, lydian, mixolydian, dorian, and for
villains aeolian, phrygian, harmonic. The key comes from the seed (same as the
generator's) unless "key" is given. Save it in the campaign's
`music/tunes/<who>.json`; use it in an arrangement as `"tune": {"seed": ...,
"written": {...}}`.

## What made the winning tunes win

- **A hook with an identity in its first bar** - a rhythm you could tap and one
  interval that isn't the obvious one: the bard's arpeggio up to the octave and the
  mode's flat 7th ("a wink"), the barbarian's long-short stomp leaping to the 5th
  and the flat 7th like a war cry, the dragon's dotted stomp, a rising 5th and the
  minor 6th grinding against it.
- **Long notes on strong beats.** Phrases land on the beat; a held note starting a
  sixteenth or an eighth late sounds unsettled, not syncopated. Syncopation should
  be a short, deliberate figure.
- **Rhythmic life fit to the character.** A restless bard runs in eighths; a
  barbarian stomps long-short; a dragon is slow and heavy with dotted figures.
  Not every phrase "three quick notes then a long hold".
- **The second phrase answers the first** - the same opening, a different ending
  (a question that rises or lands on the 2nd/5th), not the same phrase a step up.
- **The climb develops the hook** - its head in sequence, quicker, a new rhythm -
  to one climax note, held, about 60-65% through; then a fall (a scale run or by
  thirds) that leads home.
- **Home is the hook again, ending on the tonic on a downbeat, held.**
- Singable: range up to ~16-19 semitones, leaps up to an octave (filled in by
  steps afterwards).

## Check it

`python lib/tune_score.py --json <tune.json>` scores it against 3,000 real folk
and fiddle tunes (surprise, rhythm, held notes, notes on the beat, repetition).
Read the per-feature notes: long notes off the beat, a repeat share past the 95th
percentile, or a rhythm with no variety are real problems. Its surprise scale is
skewed for film-style themes (held notes and leaps are rarer in folk tunes), so
compare candidates with each other rather than chasing the target. Then hear it
alone: render it on one instrument over a drone (as the "tune only" test did) and
rate it - the arrangement can't rescue a weak tune.
