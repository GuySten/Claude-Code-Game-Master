# Recipes: what each piece needs

Starting points, not templates - every character should sound like themselves.
Tune stages and arcs are in lib/character_arcs.py (stage 0 seed, 1 theme, 2
heroic, 3 legendary; dark 0-3; wound; warm from bonds). Read the tune at the
stage you're arranging: `arrangement.py tune "<seed>" --class X --stage N --dark N`.

## A hero's theme, by story stage

- **Stage 0, the seed (a lone voice):** one instrument carries the short tune
  (horn, oboe, clarinet, solo violin line) over almost nothing - a held low note,
  a soft pad. ~15-20 s. Intimate; no percussion, or a single soft timpani.
- **Stage 1, the theme:** the tune as written, ~40-60 s. Stated small first,
  then developed: a second statement with a new carrier and texture (often a step
  up), an answer or countermelody in the held notes, an engine under it (arpeggios,
  a pulse, pizzicato), one build to its top note. A modest ending (a held chord,
  or the hook once more, alone), no fanfare yet.
- **Stage 2, heroic:** the tune reaches higher (the generator raises its climax).
  Brass join from the climb; trumpets on the climax; snare or taiko driving the
  build; choir may enter at the top. Ending with a roll and a stroke.
- **Stage 3, legendary (the finale):** everything, but earned: an intro that
  foreshadows the hook's rhythm (timpani/low strings), a first statement still
  small (horns alone), the second with a countermelody, the climb with the
  orchestra building and the snare in the hook's rhythm, the climax on a
  harmonic surprise with choir and cymbal, the return as the fullest statement
  (choir singing the tune, flutes an octave up), a ritardando, a held final chord
  with a timpani roll and a final stroke. ~35-45 s.

## Story colours (on top of the stage)

- **Wound (grief, loss, failure):** slower (x0.75), softer, smaller: the tune in
  a solo voice (oboe, english horn, cello) over sustained strings; minor
  borrowings (iv, bVI) under its major notes; no brass, no drums or one muffled
  timpani; a lament bass descending under it; an unresolved or quiet ending.
- **Healing:** the wound version's opening, then warmth returning in the
  second half - the full chords come back, the major restored on the return.
- **Bond (warm):** a second voice joins the tune - a countermelody in thirds or
  a dialogue (strings answer horns); add9/maj7 colours; harp arpeggios; warmer
  register (cellos, horns, clarinets).
- **Darkness 1-3:** the tune itself borrows dark notes; the arrangement follows:
  1 - one minor borrowing at a cadence, a shadow (low strings, a sus chord);
  2 - lower, heavier, brass lower, harmony mostly borrowed from minor;
  3 - nearly the villain: low brass and taiko, Phrygian bII, the tune's
  heroism only in its rhythm.

## The dark twin (what a hero could become)

The `--minor` version of the hero's tune. Same rhythm and hook, so it's
recognizably *them*. Slower; low register (cellos, bassoons, horns an octave
down); war drums if they're a fighter type; Phrygian bII and the borrowed V;
the climb leaning on its tritone; the climax on bVI. An oboe or solo instrument
playing a fragment of the *heroic* hook, faintly, at the very end - the person
they were - is a strong, cheap effect.

## A villain's theme (looping while they're on stage)

Built from who they are: an aristocrat (organ, bells, an elegant solo - english
horn, a menuet-like pizzicato), a brute (low brass, taiko, a slow heavy beat), a
schemer (pizzicato, clarinets low, celesta, tremolo), an ancient evil (choir,
low drones, gong). A loop of 45-60 s: an ostinato or vamp that begins and ends
it, the tune once (soft solo -> fuller), one climax (aug6 / bVI7, bells, a
cymbal), and a return to the opening texture so the wrap is seamless.

## A boss fight (a loop for a whole battle)

Relentless but not monotonous, 75-120 s, `"role": "battle"`. At every moment
at least three lines move besides the tune - typically an eighth-note ostinato
(cellos + bassoons), a second ostinato or countermelody up high (violins2 +
clarinets, horns answering the tune's phrases), a moving bass, and the drums -
and each section changes something (key, carrier, texture). A breakdown (drums
and choir alone, a solo instrument on the hook) before the last build gives the
table a breath and makes the return hit harder. Typical shape:
- a drum-and-ostinato vamp (i | bII or i | bVI per bar) with the choir holding a
  chord per bar and brass stabs on downbeats - the intro and the break;
- statement 1: the villain's tune in low brass (horns + trombones an octave
  down), choir chords under it, cello/bassoon eighth-note ostinato, snare
  backbeats, taiko;
- the break: the vamp again, toms, a roll into...
- statement 2: the full orchestra - trumpets and horns on the tune, violins an
  octave up, tuba below, the choir wide in two octaves, crashes on the climaxes;
  better still a step or a third higher ("keys" + statement "shift") or with a
  new countermelody, so it isn't the first statement louder;
- optionally a climax section: the tune's second half fragmented, augmented
  (slower, in the brass) or over a new chord (bVI7, the aug6), gong;
- back into the vamp (the loop's start).
Tempo 120-150. Keep the end's dynamics near the start's.

## Other pieces the table may need

- **Tavern, festival:** no orchestra tutti - pizzicato, flutes, clarinets, harp,
  a light snare or triangle; dance meters (6/8, 3/4); bright major.
- **Mystery, exploration:** tremolo and pads, celesta or harp figures, clarinets
  low, sparse; lydian or dorian colour; no strong cadences (it should not end).
- **Mourning, a funeral:** strings and choir, a slow lament bass, a single
  tolling bell, the dead character's hook played slowly by a solo oboe.
