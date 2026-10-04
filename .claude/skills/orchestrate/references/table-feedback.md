# What this table liked (and didn't)

The host's reactions to the music, newest last. Read before writing; add to it
whenever the host says how a piece sounded. Their ears are the final judge.

- They want a **real orchestra, not AI-generated audio**: the sampled orchestra
  playing written notes, not MusicGen.
- The **hand-written arrangement** of a legendary theme sounded "a lot better"
  than the rule-based one: the tune passed around the orchestra, a
  countermelody, a harmonic surprise at the climax, a real ending.
- **A boss battle should have a choir** - and it must be clearly heard ("I do not
  hear the choir" was the complaint before the mix was evened out).
- After the instruments were evened out and the tune mixed over the rest:
  "now it's a lot better".
- They care whether a theme is **memorable** - main characters' themes should be
  recognizable at once.
- They asked for **Meta's Audiobox Aesthetics** ratings (lib/music_rate.py) next
  to the critic. First ranking (enjoyment CE): the game's professional library
  6.2-8.0 (light, melodic tracks highest; boss tracks 7.2-7.3); our villain theme
  7.3, bard tests 7.4-7.6, wounded tests 7.0-7.2, our boss fights 6.4-6.8, the
  legendary theme 6.5 (rule-based 6.2, MusicGen 6.1). Weakest areas: boss fights
  and the heroic legendary - the denser, more developed versions scored higher.
- **Tunes (a blind-ish "tune only" test: the same clarinet, tempo, key and drone,
  only the notes different):** "v2 is clearly better than v1, but you clearly beat
  both" - the GM's hand-written tunes beat the generator's, and the fixed generator
  (long notes on the beat, a developing climb) beat the old one. Write main
  characters' tunes yourself (references/tunes.md); the generator (gen 2) for the
  rest.
- The rater marked trumpets carrying the tune down by 0.6-0.8 (the sound set's
  trumpet is among its weakest recordings alone); horns carry a tune better.
- **The surprise budget (a 2x2 on Kestrel's legendary theme):** simple tune + rich
  arrangement and surprising tune + supportive arrangement were "better" than
  both-plain and both-rich - "the difference is not huge", but consistent. Spend
  the surprise in the tune or in the setting, not both, and not neither.
- The Audiobox rater put a Beethoven overture (Egmont, a professional recording)
  at 7.44 - level with our pieces: its scale is flat; don't read it as quality.
- **The Margrave's finals (two villain waltz loops, the same setting on two tunes):**
  "A is better overall" (the Velvet Waltz) - but "neither is very appropriate for a
  villain song": the setting (English horn and clarinet, plucked waltz, harp, bells)
  was elegant, not menacing. A villain's theme needs menace in its *colour* -
  low register, dark instruments, weight - even when the tune is elegant.
- **Uneven quality inside a piece** is heard: "the quality of the work changes a lot"
  within each of them. Where: "the trumpets in B's climax are really weak" (it was the
  horns and trombones carrying the tune - there were no trumpets) and "adding a choir
  in A was a lot better". So: **never give the climax's tune to the brass** in this
  sound set (its brass is its weakest-sounding section as a lead: horns, trombones and
  trumpets alike); carry it on strings in octaves, with the choir in held chords over
  it, and use brass only underneath, for weight and punctuation. Windowed ratings
  (8-second windows) showed the same dip at both climaxes - use them to find a sagging
  passage (a drop of 0.5 or more; their noise is about 0.2), never to rank fixes.
- **Better instruments (a blind A/B, the same brass-led climax, only the brass
  samples differing):** Virtual Playing Orchestra's horn and trombone sections beat
  MuseScore_General's horns and trombones ("A is better") - "but I want more
  quality". The sound set itself limits the music: better free samples are worth
  their setup.
- **Many instruments entering in the same bar** (piece A's climax: five at once, vs
  the same instruments brought in over a few bars): "I cannot tell". Not a rule
  worth enforcing for this music; the climax's weakness was its brass lead.
- **Timing (slow instruments started early so they're heard on the beat):** on a new
  tune the host couldn't judge it; they asked for **a tune they already know
  independently** - Ode to Joy, the same notes with and without the early start:
  "B is clearly better" (the early start). The orchestra now does it for every piece
  (orchestra.ADVANCE). Lesson for every listening test of the *sound* (timing,
  instruments, mix): play it on a tune the host knew before this campaign, so the
  ear can tell what's off from what's new.
- **Instruments from another sample set (Ode to Joy, trumpets and flutes A/B):** "I
  think the difference is mainly in the acoustics." Measured: Virtual Playing
  Orchestra's recordings carry their own room and stereo width (2-4x wider than
  MuseScore_General's near-mono recordings, which take their space from our hall), so
  they sounded like another room. Instruments from different sets must be placed in
  the same space (width, position, hall send) before they're compared or mixed;
  orchestra.ROOM sends each recording to the hall by the room it already carries.
