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
- **The same test with the acoustics matched** (each VPO recording narrowed and placed
  like the current one, its hall reduced): the current flutes are "crisper and
  better", and VPO's trumpets "horrible". The automatic instrument judge (Audiobox on
  probe phrases) had picked VPO for both: it failed both checks, so it doesn't choose
  instruments. It most likely rewarded the wide, roomy recordings rather than the
  instruments. The earlier "VPO brass is better" was heard with VPO's own room left in,
  so it may have been the room too. Narrowing a stereo recording (summing its two
  microphones) can also make it hollow - another reason not to swap sample sets lightly.
- **Brass only (Ode to Joy, horns and trombones), the current brass given +9 dB more hall
  to match VPO's stereo width:** the current one "feels smoothed", VPO's "crisper". The
  smoothing is likely the extra hall, not the instrument. "Crisp" keeps coming up as
  what the host notices and likes (the flutes too): the hall may be too much overall.
- **"Crisp" is measurable** ("I am sure even you can detect that"): the rise in level in
  the 30 ms after each note starts. It agreed with all three of the host's crispness
  verdicts (the flutes, the trumpets, the brass alone), and showed our hall smoothing
  the attacks (more hall, softer attacks). The hall now leaves a 35 ms gap before its
  echo and keeps the direct sound at full strength: attacks +0.9 dB against +0.24 on
  Ode to Joy, its width kept.
- **The crisper hall, heard on Ode to Joy:** "hall B [the old one] is a bit better", but
  "for fast or changing tunes the difference will be a lot more" - and the host isn't
  sure Ode to Joy was a good test of it. The old hall is back until a fast, changing
  tune (In the Hall of the Mountain King, accelerating) settles it. Measured there, the
  new hall's attacks are sharper only in the slow opening (+0.7 dB), not in the fast end.
- **The crisper hall on fast music:** Mountain King (accelerating) for the full orchestra
  "too close"; brass only, the old hall "slightly crisper, but not sure"; Flight of the
  Bumblebee (brass) "almost the same". The hall tweak isn't heard - the old hall stays.
  The attack measure tracks big differences (an instrument, 9 dB more hall), not
  this small one (it leaned the other way on the brass Mountain King).
- **What was wrong with the Margrave's piece B, in the host's own words, remembered:**
  "the climax did not go with what was before" - not the brass. At its climax the
  harp, the countermelody and the tune's carriers stopped as six new parts started
  (the orchestra jumped from 6 to 10 parts in one bar). So brass may carry a climax's
  tune again; what's forbidden is the seam. The critic now warns at a seam (parts
  stopping as others start) and at a sudden doubling of the orchestra. (Heard as
  20-second excerpts, the old render of that climax also beat both timing-fixed
  renders - unexplained; the timing fix stays on, from Ode to Joy.)
- **The Margrave v2 (the Velvet Waltz as one piece that grows: a running plucked waltz,
  bass and pad; the cellos carried across as a creeping line; horns, then tremolo,
  trombones and a timpani roll, then the choir, in waves; brass on the climax tune):**
  "the climax fits much better now". The seam was the problem, and the fix works.
- **The Margrave v2:** "good music but not dark enough - good for a grey villain, not a
  really evil mastermind", and "it does not fit as a piece during battle". An evil
  mastermind's theme: slower and heavier, low and dark colours (no harp, no plucked
  lightness), tense diminished chords for the bright dominants, a pedal under it all,
  dissonant low choir and organ at the climax, an ending that never resolves. And a
  villain needs **two pieces on the tune**: the theme for their scenes, and a battle
  piece (fast, an ostinato engine, drums) - the table plays the battle piece in any
  fight they're in.
- **Timpani rolls** (14 strokes a second, each a full ringing hit, alternating strong and
  weak): "painfully fast" in the Margrave's battle piece and "a bit too fast" even in
  his theme - the one instrument far faster than everything else. Rolls are now about
  9 strokes a second, each ringing into the next, swelling smoothly (and a battle's
  roll stays under velocity ~104).
- **Darker is not slower:** the Margrave's "dark" rewrite (72 bpm, organ pedal, low
  cellos/bassoons/trombones on the tune, diminished chords, low choir clusters)
  "sounds less evil" than the grey-villain version it replaced. Slow and low reads as
  mournful, not evil; an evil mastermind keeps the momentum and the control. Push
  menace through power or coldness on a moving piece, not gloom.
- **What evil sounds like to this host** (their references: Homelander's theme, Evil
  Morty's theme, the Imperial March). Homelander's, in their words: "a lone fast violin
  that is a bit jarring", with "very high notes" - "it presents him as lonely and
  crazy". Evil here is a character portrait (madness, isolation, inevitability), not
  gloom: one exposed voice, fast and obsessive, high and grating, over almost nothing.
  (Don't describe a piece you can't hear as fact - the GM's guess at Homelander's theme
  was wrong; ask the host to describe it.) The orchestra now has a solo violin.
  Evil Morty's theme, in their words: what stands out is "the human sad choir" - a
  villain's music can carry their sorrow, sung by human voices.
