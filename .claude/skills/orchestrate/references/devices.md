# Character devices

A library of musical devices, each with what it signals, how to write it in the
arrangement format, where the convention comes from, and what the host thought of it.
A character's music is a **portrait in layers**: pick the two to four devices their
description calls for, give each its moment, and let one carry the piece (the Margrave:
façade + lament + madness + power).

How to use it:
1. Read the character in the campaign (npcs.json, the world bible, their deeds). Note
   their traits in plain words (elegant, tired, cruel, grieving, unhinged, devout...).
2. Pick devices from the **trait table** at the end; check each one's "with" and "not".
3. Write the portrait: one device carries the piece (its texture runs throughout), the
   others enter at their moments; the climax grows out of what came before (SKILL.md).
4. For a character who changes, the devices are the dials of their versions (a hero's
   growth, a villain's descent): the same piece, one device turned up per step.
5. Run the critic; then the host listens once and says what to change.

Sources, in brief (details and citations: `research.md`):
- **Conventions** - film/TV/game scoring tropes, as catalogued by TV Tropes' *Score and
  Music Tropes* and *Evil Music Index* (named below in quotes);
- **Evidence** - music-psychology findings on which features express which emotions
  and how music evokes, fits and grows on listeners (Juslin & Sloboda (eds.), *Handbook
  of Music and Emotion*, 2010: fifteen of its chapters, esp. Gabrielsson & Lindström,
  ch. 14);
- **Practice** - how one film composer's themes are built and transformed (Lehman,
  *Complete Catalogue of the Musical Themes of Star Wars*);
- **This table's ears** - `table-feedback.md` (the host's verdicts win over all of these).


Entries marked **(from knowledge)** are general film and game scoring practice written from memory (the Heroic Music Index, Genre Motif and Regional Riff pages were reviewed from the host's paste; the Mood Motif page's examples were folded away, so instrument colours are general practice); names marked † were not checked against the site. The orchestra has no piano, harpsichord, guitar, accordion, saxophone, bagpipes, harmonica, xylophone or steel drums: where a device names one, it says what to write instead.

---

## Villains and darkness

### Façade - the elegant dance ("Sinister Tango Music")
- **Signals**: sophistication, control, a civilised surface over something rotten.
- **Write it**: a dance meter that never stops (a waltz in 3/4, a tango's habanera in
  2/4), the tune on a velvet colour (cellos low, then violins), a plucked or light pulse
  (pizzicato on 2-3, harp), plain functional harmony in a minor key; moderate tempo
  (~80-90). It is the texture that runs through the piece; other devices crack it.
- **Host**: the Margrave's Velvet Waltz - "good music", "good for a grey villain";
  alone it is too gentle for real evil, but it is the face the other devices break.
- **Not**: slowing it down and darkening it into gloom ("sounds less evil").

### Madness - the voice that plays along and breaks ("'Psycho' Strings", "Tuneless Song of Madness")
- **Signals**: a mind fraying; instability, not structured menace.
- **Write it**: a solo violin (`solo_violin`) plays along with the orchestra, audible
  (about 3 dB under it), in tune and in time. At chosen moments it **breaks**: its notes
  jump an octave or two too high, slide off pitch and waver (`{"slide", "wobble"}`),
  rush and drag off the beat, stick on a note; the **string section follows it**
  (`"unhinge"`: each string part drifts its own way) while woods, brass, harp and choir
  stay true; then it falls back in line. Each break is a **short flash** (about a beat),
  growing a little each time; the piece begins and ends with the violin alone (composed
  at the start, unravelled at the end). Generator: the Margrave's `madviolin.py` pattern
  (tune notes -> violin line with break windows; windows -> unhinge stretches).
- **Dial** (descent): more breaks, longer, higher sooner, wider slides; the waltz falters
  (its pulse drops out) in the last ones; at the bottom it never comes back in line.
- **Host**: Homelander's theme ("a lone fast violin, a bit jarring, very high notes -
  lonely and crazy"); "turning mad means a violin that follows along with the orchestra
  suddenly misbehaves - turns too high, breaks pitch and stride"; "the string instruments
  should represent madness, following the violin"; breaks "should not take a lot of
  duration". Even, crisp fast notes read as "structured evil", not madness.
- **Not**: a separate violin intruding from outside; a violin mixed so low it vanishes;
  long unhinged stretches.

### Lament - the villain's grief ("Villainous Lament", "One-Woman Wail")
- **Signals**: the sorrow under the villain - guilt, the victims, what they lost.
- **Write it**: a human choir (`choir`) in held chords, soft, minor, the top voice
  falling by step; entering under the façade (not over it), swelling at the climax,
  and holding the last chord before the exposed ending. Held notes only (a choir can't
  do quick rhythms).
- **Host**: Evil Morty's theme - what stands out is "the human sad choir", "they sound
  like they are mourning"; adding a choir to a climax was "a lot better".

### Power - the march of the unstoppable ("'Bringer of War' Music", the Imperial March)
- **Signals**: inevitability, force, an army; the villain at war.
- **Write it**: an ostinato that never lets go (Holst's *Mars* is in 5/4; a march in
  4/4 or a waltz "in one"), low brass and timpani on the beats, the tune in octaves,
  minor with blunt chord shifts (i-bVI, i-bII); fast enough to drive (battle: ~160 in
  3/4). This is the villain's **battle piece** ("Boss Remix" - the theme re-made for the
  fight); the table plays it in any fight they're in.
- **Host**: the Imperial March named as evil; the Margrave's battle piece "fine" (once
  the timpani rolls were slowed).
- **Not**: brass on a climax tune in a seam - the climax must grow out of what came
  before (that, not the brass, was what failed in the Margrave's piece B).

### Corruption - the theme turned ("Corrupted Leitmotif", "Dark Reprise")
- **Signals**: change for the worse, of the same character.
- **Write it**: the same tune, never different notes - imperfectly: the madness breaks,
  a darker colour (low register, dark instruments), a harmony made tense (diminished for
  the dominants), a falter in its pulse. Use it for a hero's darkening (character_arcs
  `dark`) and a villain's descent (`"use": {"as": "theme", "dark": n}`).

### Dread - the drone ("Drone of Dread", "Tense Tremolo", "Heartbeat Soundtrack")
- **Signals**: something is wrong; waiting.
- **Write it**: a held low pedal (basses, organ, low tremolo) under moving music, a slow
  timpani heartbeat; never the whole piece.
- **Host**: slow and low *as the whole piece* read as mournful, not evil.

### Innocence corrupted ("Ominous Music Box Tune", "Creepy Children Singing", "Ironic Nursery Tune")
- **Signals**: childhood, nostalgia, wrongness under sweetness.
- **Write it**: celesta or glockenspiel, high, simple, slightly too slow; alone or over a
  dark drone; a wavering pitch (`wobble`) on a long note.

### Doom ("For Doom the Bell Tolls", "Deathly Dies Irae", "Ominous Pipe Organ", "Ominous Latin Chanting")
- **Signals**: death, judgment, the sacred turned against the heroes.
- **Write it**: tubular bells (`bells`) tolling on the tonic; the *Dies irae* chant
  (public domain) quoted in the bass or the choir; full organ chords; a choir in
  rhythmic unison on the low register.

### Shock ("Scare Chord", "Last Note Nightmare")
- **Signals**: a sudden reveal; the turn at the end.
- **Write it**: one loud dissonant tutti hit (a cluster or a bII chord over the tonic),
  after a quiet bar; or a calm piece whose last bars turn sinister. Once per piece.

### The ghost's voice ("Ghost Song")
- **Signals**: a haunting, a voice from the dead, a cursed place that remembers; grief
  that will not leave.
- **Write it**: one soft, high line with no clear source - a few `choir` voices on a
  single held vowel-line (long notes only), or a flute or solo violin far above a near
  silence - wandering in a minor or modal tune that never cadences; a slight `wobble`
  and a small `slide` off its long notes; a hollow fifth or a drone below, little else.
  It comes and goes rather than starting and ending.
- **Not**: a full choir in chords (that is a lament or a chant, a body of people, not a
  ghost).

### The other-worldly glide ("Theremin", "Freaky Electronic Music")
- **Signals**: something not of this world: an aberration, a far realm, a star-spawn,
  an artificer's strange device, a mind-flayer's presence.
- **Write it**: no theremin here: its sound is a pure, high, gliding voice with a wide
  vibrato - write it as a solo violin or flute line, high and soft, every note joined to
  the next by a `slide`, with a wide `wobble`; over held tremolo on an unrelated chord
  (two chords a tritone apart), celesta or glockenspiel ticking irregularly.
- **Not**: a steady beat or functional harmony - the alien does not resolve.
- **Also heroic**: the same glide, warm and in major over a steady pulse, reads as retro
  science-fiction wonder - the strange made friendly.

### The villain conducts ("Conducting the Carnage")
- **Signals**: a villain in total command: the music obeys them, each gesture lands.
- **Write it**: at the table, the GM cues `hits` and stabs to the villain's actions (a
  chord as the hand falls, a timpani stroke for each order); in a written piece, the
  orchestra in strict unison rhythm on the villain's motif, the dynamics jumping on
  their accents, silence when they pause. Precision is the point.
- **Not**: chaos - this is control.

## Heroes and light
- **Fanfare / Theme Music Power-Up**: brass on the tune, the climax of an anthem at a
  heroic moment (the table plays the anthem then). Brass climaxes are fine when they
  grow out of what came before.
- **Victorious Chorus / Triumphant Reprise**: the choir and full orchestra on a theme
  that was heard sad or small before - the finale of an arc (stage 3, "legendary").
- **Love Theme / bond**: strings, warm, a second voice answering the tune (character
  arc `warm`).
- **Boléro Effect**: one figure repeated, the orchestra growing around it - a build.

## Sorrow and tension
- **Simple Score of Sadness / Lonely Piano Piece / Playing the Heart Strings**: few
  instruments, slow, soft, stepwise falling lines (a wound: the arc's `wound`).
- **Sad Battle Music**: a lament over the fight's pulse - a costly battle.
- **Tense Tremolo / Tick Tock Tune / Drumbeat of Chaos**: tremolo strings; a ticking
  ostinato (pizzicato, woodblock-like high strokes); fast drums - urgency.

## Places ("Regional Riff", "Location Song")
- **Holy Pipe Organ** - temples, shrines (the sketcher's "sacred" colour).
- **Avian Flute** - forests, the wild (flutes, high, birdlike figures).
- **Accordion to Most Sailors** - the sea, harbours (no accordion here: clarinets and
  a drone).
- **High-Class Harpsichord / Haunting Harpsichord** - nobility, old money; the uncanny.

## Heroes and triumph

### The horn call (from knowledge; "Fanfare" in its knightly form)
- **Signals**: a summons, honour, the knight, the hunt, a hero setting out; the "call to
  adventure" a paladin or ranger answers.
- **Write it**: horns in unison or octaves, `mf`-`f`, a short figure built on the open
  intervals (rising fourth and fifth, the major triad, a dotted rhythm: long-short-long),
  answered by a second horn call a bar later or by trumpets an octave up. Hold the last
  note while the strings enter under it on I or IVadd9. In the open, leave space after
  it (a bar of only a held fifth in the basses) - a call wants an echo.
- **Not**: a fast busy brass passage; a call needs the silence around it.

### Saved by the Church Bell ("Saved by the Church Bell")
- **Signals**: salvation, the siege lifted, dawn after the long night, a wedding, a
  town's rejoicing. The bright twin of Doom's toll.
- **Write it**: `bells` pealing in **major**, many strokes, not one: a descending scale
  pattern (8-7-6-5-4-3-2-1 of the key, quarter notes, repeated with the order shuffled,
  like change-ringing), plus glockenspiel doubling the top notes; under it the full
  orchestra on I and IV, choir on open "ah" chords, a timpani roll into the first peal.
  Loud, fast enough to ring (~120), then let the bells keep going over a held chord as
  the rest fades.
- **Not**: a single slow toll on the tonic - that is a funeral, not a rescue.

### Cherubic Choir ("Cherubic Choir")
- **Signals**: the danger is over; innocence safe; a blessing, a healer's grace, the
  dawn after the battle; a child saved.
- **Write it**: `choir` kept high (top voice around A4-E5, nothing below C4), soft (`p`
  to `mp`), major, slow-moving held chords (I, IV, vi, Isus4-I), doubled by `celesta` or
  `glockenspiel` on the top note and `harp` arpeggios. Enter after a pause or a dark
  chord, on the first major chord. Short: 8-16 beats is enough.
- **Not**: a full mixed-voice choir in the low register (that reads as solemn or ominous).

### National Anthem ("National Anthem")
- **Signals**: a realm, a faction, an order, a city's pride; a coronation; a loyal
  soldier's or a patriotic noble's identity.
- **Write it**: 4/4 or 3/4, moderate (~72-84), a singable tune (range of about a tenth,
  mostly stepwise, one climb to the high point near the end), block chords that change
  every beat or two (I-IV-V-I with ii and vi, an applied V/V before the last cadence),
  a plain perfect cadence to end each phrase. Brass choir (horns, trumpets, trombones,
  tuba) or full tutti, strings doubling; snare roll (`rolls`) and a cymbal on the
  last downbeat. Play it twice: once brass alone, once tutti with choir.
- **Not**: minor keys and syncopation - an anthem must sound like a whole people could
  sing it.

### The climax ("Climactic Music", "Dramatic Choir Number")
- **Signals**: the decisive moment: the final blow, the ritual's last word, the gate
  giving way.
- **Write it**: the piece's theme at its highest and loudest, prepared, not dropped in:
  over 8-16 beats raise the dynamics in steps, thicken the texture one family at a time
  (strings, then woods, then brass), drive the bass up by step, put a timpani roll
  into the arrival. At the arrival: a key change up a step (`keys` and the statement's
  `shift: 2`) or an unexpected major chord (bVI or IV instead of I), choir enters on
  held chords behind the tune ("the choir joins the soloist"), cymbal hit. Hold the
  peak no more than a phrase, then a release.
- **Not**: a climax that starts from silence or arrives at a seam where everything else
  stops (the host's rule: it grows out of what came before).

### The turning tide ("Near Victory Fanfare", "Songs in the Key of Panic", "Variable Mix")
- **Signals**: the battle's state: losing (low hit points, time running out, the
  ritual nearly done), and winning (the boss reeling).
- **Write it**: as **layers of one loop** (Variable Mix): the battle piece written so
  parts can be added or removed without a seam. *Panic*: the same loop up a semitone or
  a tone (`keys`), tempo +10-15%, tremolo strings and a fast pizzicato or snare
  ostinato on every eighth, brass stabs off the beat, the bass on the tonic only.
  *Near victory*: the hero's or party's tune cuts through the battle in trumpets and
  horns over the same pulse, major (or the relative major), with the choir; the
  villain's ostinato drops out bar by bar.
- **Not**: a new, unrelated piece for each state - the change must be heard as the same
  fight turning.

---

### Rallying ("Music for Courage", "Song of Courage", "Pep-Talk Song", "\"Gaining Confidence\" Song")
- **Signals**: fear turning into courage: the speech before the charge, a frightened
  hero finding their nerve, allies taking heart.
- **Write it**: the hero's tune heard first unsure - one soft voice (a clarinet or solo
  violin), broken phrases with rests, minor or over an unstable chord, no pulse - then
  steadied: a pulse enters (low strings, then timpani on the beats), the tune doubled in
  octaves, the harmony moving to major (the borrowed chords resolving home), horns
  joining, the dynamics climbing in steps. Confidence is steadiness first, loudness
  second.
- **Not**: starting loud - the change is the device.

### Themes in conflict ("Hero vs. Villain Duet")
- **Signals**: a showdown, a parley, a debate of wills; two characters whose themes the
  table knows.
- **Write it**: the two motifs in alternation, each in its own colour (the hero's on
  horns or violins, the villain's on low brass or cellos), cutting each other off sooner
  each time; then together in counterpoint, one high and one low, over a shared pulse,
  their harmonies clashing (the villain's motif in a key a semitone or tritone away);
  whichever wins the last statement wins the scene.
- **Not**: blending them into one comfortable harmony before the story decides.

### The hero's breakdown ("BSoD Song")
- **Signals**: a hero shattered - a death, a failure, a betrayal; numbness, not darkness.
- **Write it**: the theme in fragments: its first notes only, on one quiet instrument
  (a solo oboe, a cello, celesta), each fragment stopping before it resolves, long rests,
  a slow bare accompaniment (one held note or none); the tempo slower, the key the same.
- **Not**: Corruption (the theme turned dark) - here it is broken, not changed.

### The sidekick's answer ("Sidekick Song")
- **Signals**: the companion, the comic friend, the loyal squire: lighter than the hero,
  tied to them.
- **Write it**: their own short motif, quicker and higher (piccolo, clarinet, pizzicato,
  bassoon for the comic one), that answers the hero's phrases in the gaps - often built
  from the hero's motif's rhythm; it can play alone in their scenes.
- **Not**: a second grand theme - the sidekick's music stays smaller than the hero's.

### Voice and register ("Innocent Soprano", "Tenor Boy")
- **Signals**: youth, innocence, idealism in a high, bright voice; age, weight and
  authority in a low one.
- **Write it**: put a young idealist's or innocent's tune high (flutes, violins, oboe,
  high clarinet, a high choir line), a veteran's, a ruler's or a mentor's low and warm
  (cellos, horns, bassoons, a low choir); a character who grows up can move down an
  octave over their arc, and a fallen innocent can lose the top of their range.
- **Not**: a young hero carried by tuba and basses (unless the joke is the point).

## Themes across a campaign

### Leitmotif practice ("Leitmotif", "Establishing Character Music", "Recurring Riff", "Bootstrapped Leitmotif", "Musical Nod")
- **Signals**: who someone is, before they speak; that something has come back.
- **Write it**: give every recurring character, faction, place and object one short
  identifying figure (2-4 bars: a contour and a rhythm you can recognise from three
  notes). Play the full tune the **first time** they appear (Establishing Character
  Music: the portrait); afterwards use fragments: the first bar in the horns under the
  tavern music when the villain's agent walks in, the rhythm alone on timpani. A piece
  that becomes associated with a moment by repetition at the table can be adopted as
  that character's motif later (Bootstrapped Leitmotif). Callbacks across the campaign
  (Musical Nod): quote one bar of an old place's theme when the party returns to it.
- **Not**: a theme so long or so smooth that a fragment is unrecognisable; motifs for
  everything (one per important thing, not per NPC).

### Theme and variations ("Theme-and-Variations Soundtrack", "Rearrange the Song")
- **Signals**: the same person in another circumstance: at rest, at war, in grief, in
  love, older.
- **Write it**: keep the tune's notes (the generator's tune), change everything else:
  meter (4/4 to 3/4 makes a waltz, to 6/8 a jig or a lullaby), tempo, mode
  (`"mode": "minor"`), register and instrument (horns to solo oboe), accompaniment
  pattern (march, waltz, ostinato, held chords), harmony under the same notes (re-
  harmonise a I with vi or bVI). One dial per variation reads as the same person; three
  dials at once read as someone else.
- **Not**: changing the notes of the tune itself.

### Softer and slower ("Softer and Slower Cover", "Moody Trailer Cover Song")
- **Signals**: poignancy; a bright theme remembered in sorrow; a premonition of a dark
  time (heard before it happens, like a trailer's slowed cover).
- **Write it**: a bright, fast theme at half the tempo or less, `p`, a single sustained
  instrument (english_horn, solo cello line in `cellos`, flute low) over sparse held
  chords (`strings` at -20) or harp alone; replace some major chords with their minor
  relatives (I -> vi, IV -> iv) and end on a suspension that resolves late. Strip any
  pulse.
- **Not**: keeping the original's rhythmic accompaniment at the slow tempo - it then
  just sounds slow, not tender.

### Withholding and the last reprise ("Theme Music Withholding", "Last Episode Theme Reprise")
- **Signals**: a payoff: the hero's theme comes back when it is earned; the campaign's
  first theme closes the campaign.
- **Write it**: after the hero's theme is established, keep it out of the music for a
  while (fragments only, or not at all, during a dark stretch), then let the full tune
  return at a turning point, in its original key and colour or its stage-3 form. For a
  finale, bring back the campaign's opening theme (or the party's first anthem) under
  the climactic scene, at full orchestra, then once more softly at the very end.
- **Not**: playing the hero's full theme in every scene - it stops meaning anything.

### The party in counterpoint ("Massive Multiplayer Ensemble Number")
- **Signals**: the party together on the eve of the battle; everyone's thread coming
  together; a council of rivals.
- **Write it**: two or three characters' tunes **at the same time**, in different
  registers and instruments (one in cellos low, one in horns middle, one in flutes or
  violins high), over one shared chord progression and tempo. Introduce them one by one
  (8 bars each), then stack them. Write each tune's notes as `lines` transposed into a
  common key; keep each line's rhythm distinct (one long notes, one moving, one
  rhythmic) so the ear can follow all three. A shared climax: all on the same chord.
- **Not**: stacking tunes whose rhythms are the same - they mush together.

### Foreshadowing and the lie ("Musical Spoiler", "The Day the Music Lied")
- **Signals**: something is about to happen - or the GM wants the table to think so.
- **Write it**: *Spoiler*: let the threat's motif slip into the place music before it
  appears (two notes of the villain's tune in the basses, a drone appearing under a
  calm loop). *The lie*: build tension (tremolo, a rising line, a crescendo, a held
  dominant) to a moment and resolve it on nothing - a quiet major chord, or silence -
  then strike for real a few beats later with the Shock. Use the lie once per session.
- **Not**: a lie on every corridor; the table stops trusting the music at all.

---

## Action and battle

### Encounter battle music ("Battle Theme Music")
- **Signals**: an ordinary fight - bandits, wolves, a goblin ambush - as distinct from a
  villain's battle piece (Power) or a set-piece battle.
- **Write it**: a seamless `loop` of 16-32 bars, 140-170 bpm, minor or Dorian, a
  driving ostinato in the low strings (repeated eighths on the root, accents in 3+3+2:
  `"xooxooxo"`), a snare or toms pattern, brass stabs on chord changes (i-bVI-bVII-i),
  a short melody in horns or violins on top. Keep three lines moving (the critic's
  "battle" role checks this). Mild: it will repeat for many minutes.
- **Not**: a big tune with long held climaxes - it tires in a loop; heavy cymbals every
  bar.

### The great battle ("Orchestral Bombing")
- **Signals**: a war: armies clashing, dragons in the sky, a siege, a fleet battle;
  sweep and scale rather than a single foe.
- **Write it**: full orchestra, fast (~150) in 4/4 or a driving 6/8, sweeping string
  runs (`lines` of fast scales up the violins, an octave apart in violins2), horns
  carrying a broad tune in long notes **over** the fast strings (two speeds at once:
  urgency and grandeur), trombones and tuba on the bass, taiko and timpani on
  syncopated accents, choir in held chords at the climaxes. Change keys every 8-16
  bars to keep the scale growing.
- **Not**: a single ostinato at one dynamic - a war needs waves.

### Happy Battle Music ("Happy Battle Music")
- **Signals**: a fight that is fun: a tavern brawl, a swashbuckler's duel on the
  rigging, an easy victory, a gnome's mechanical mayhem.
- **Write it**: major (or mixolydian, with bVII), fast (~150-170), bouncy articulation
  (staccato woods, pizzicato), a tune that leaps, syncopated brass stabs, snare
  rimshot-like accents, triangle; a swashbuckling 6/8 works well. Mischievous key
  changes up a semitone.
- **Not**: heavy low brass and timpani - they turn it into a war.

### Rock drive ("Autobots, Rock Out!")
- **Signals**: modern adrenaline in an action scene; a reckless brawler, a punk-ish
  barbarian or bard, a chase.
- **Write it**: the `kit` playing a rock beat (bass drum on 1 and 3, snare on 2 and 4,
  `ride` or `cymbal` on eighths), the low strings and trombones on power chords
  (`"I5"`, `"bVI5"`, `"bVII5"`) in driving eighths, palm-muted feel with staccato
  (`legato` short), the tune in unison horns and violins. Minor or Dorian,
  ~130-160.
- **Not**: using it for every fight in a medieval setting - it is a colour, chosen.

---

## Comedy and mischief

### Mickey Mousing ("Mickey Mousing", "Walking in Rhythm")
- **Signals**: the music follows the body: a pratfall, a tiptoe, a waddle, a pompous
  stride; slapstick and cartoonish characters (gnomes, kobolds, a clumsy apprentice).
- **Write it**: every step a note (pizzicato or bassoon staccato on each footfall, the
  pitch rising as they climb, falling as they descend), a fall as a fast downward run
  or a long `slide` down an octave in trombone or violins, a bump as a `hit` (bass drum
  plus a brass stab), a sneaky stop as a held note under a fermata. For a character who
  strides to the beat, write the walking bass (pizzicato quarter notes) at their
  walking tempo (~100-112).
- **Not**: in tragic or tense scenes - it turns anything into a cartoon.

### Sneaking (from knowledge; "Sneaky Pizzicato"†)
- **Signals**: tiptoeing, a heist, a thief or a halfling burglar, mischief in the dark.
- **Write it**: pizzicato in short notes, `p`, a chromatic or minor tune that moves by
  step and stops on rests, bassoon or clarinets doubling in staccato, an occasional
  tremolo held note when they freeze; tempo ~100-120, 4/4 or 2/4. Add a low clarinet
  slide for a near miss.
- **Not**: loud - the joke is that it tries to be quiet.

### The circus, both faces ("Happy Circus Music", "Creepy Circus Music")
- **Signals**: *happy*: a fair, a travelling show, a festival, a showman. *Creepy*: a
  mad jester, an evil carnival, a puppeteer, a fey revel that is not what it seems.
- **Write it**: *happy*: a fast march or galop (2/4, ~140), an oom-pah bass (tuba on 1,
  trombones and horns on 2: `"xo"`), chromatic runs up and down in clarinets and
  piccolo, glockenspiel and triangle sparkle, cymbal crashes. *Creepy*: the same
  oom-pah, but a waltz (3/4) slowed to ~70-80, the tune in a high register on `celesta`
  or solo violin with `wobble`, chromatic lines that slide down a semitone at phrase
  ends, the oom-pah's chord a half step off now and then (bII), dynamics too even. Can
  begin happy and turn (Descent).
- **Not**: a creepy circus at full speed - the menace is in the too-slow cheer.

### Mock melodrama ("Soap Opera Organ Score", "The Mel Brooks Number", "Melodramatic Pause")
- **Signals**: a trivial thing treated as tragedy; a vain noble's swoon, a gossip's
  "revelation", a pompous villain's overacting.
- **Write it**: the full apparatus of tragedy at a scale too large: `organ` held chords
  with diminished sevenths and a sudden stab (`hits`), a tremolo swell from nothing to
  `ff` on one word, a minor-key lament in exaggerated legato with sighing slides
  (`slide: -1` on each phrase end), and then an exaggerated pause: full orchestra on a
  diminished chord, cut off, silence for a bar. Short - a few bars.
- **Not**: playing it for a scene that is really sad; the table must know it is a joke.

### Deflation ("Letting the Air out of the Band", "Record Needle Scratch", "Musical Gag")
- **Signals**: the plan fails, the boast falls flat, the reveal is a let-down; a
  comic interruption.
- **Write it**: *the band runs down*: the playing tune slows (`ritard` from where the bad
  news lands, amount 0.6-0.8) and sags in pitch (`slide: -2` on the last held notes of
  the melody, `unhinge` the strings briefly), ending on a low trombone note with a
  downward slide (the "sad trombone": three falling steps then a long note sliding down).
  *Scratch*: one fast upward-then-downward `slide` in violins and a stop dead, silence.
  A musical gag: quote a well-known public-domain tune for a pun (a funeral march for a
  dead plan).
- **Not**: more than once a scene; it deflates the table too.

### Showman's bookends ("Minsky Pickup", "Shave and a Haircut")
- **Signals**: entrances and exits with a wink: the bard takes the stage, the con man
  makes his pitch, a scene ends on a joke.
- **Write it**: *Pickup*: before the downbeat, a brassy upbeat figure - trombones or
  trumpets rising in a short chromatic or arpeggio run with a `slide` up into a held
  note, cymbal on the arrival, then the tune. *Button*: end with the seven-note knock
  (long-short-short-long-long, rest, long-long; 5-1-1-2-1, rest, 7-1) in pizzicato and
  woods, or just two `hits` (V then I) after a rest.
- **Not**: on serious characters - it makes anyone a showman.

### The dreadful bard ("Dreadful Musician", "Hollywood Tone-Deaf")
- **Signals**: a terrible performer: the bard who can't play, the troll who sings, the
  village band.
- **Write it**: a solo line (`solo_violin`, oboe or a single trumpet) that is wrong in
  specific ways: notes `slide` into pitch, a `wobble` too wide on long notes, a note a
  semitone off at the cadence, a rhythm that drags; the accompaniment (pizzicato, harp)
  stays correct and patient. Keep it short.
- **Not**: random noise - funny bad playing is a recognisable tune played wrong.

### Stings ("Sting")
- **Signals**: a punctuation mark at the table: a reveal, a joke landing, a critical hit,
  a level-up, a door slamming shut.
- **Write it**: 1-4 beats of music. Dramatic: a tutti chord after silence (minor with a
  bII, or a diminished seventh), timpani roll into it, held under a fermata.
  Comic: two staccato notes (V-I) in pizzicato and bassoon. Triumphant: a brass chord
  rising I-IV-I with a cymbal. Keep a small set per campaign and reuse them (they become
  motifs).
- **Not**: long stings - more than a bar and it is a cue, not a sting.

---

## Wonder and magic

### Ethereal Choir ("Ethereal Choir")
- **Signals**: the otherworldly: angels, the fey, a spirit realm, a god's presence, a
  star-touched oracle; beauty that is not human.
- **Write it**: wordless `choir`, soft, high and wide-spaced, chords that do not
  resolve or that move in parallel (I - bVII - IV - I, or Lydian I - II), held long
  (2-4 beats at least); `harp` arpeggios and `celesta` sparkle; `strings` sustained
  very soft underneath; a slight `wobble` on a top line for a shimmer. Slow (~60).
- **Not**: a rhythmic or low choir (that is Ominous Latin Chanting) or a cadence that
  settles too firmly.

### Wonder and discovery (from knowledge)
- **Signals**: awe: the first sight of a sky-city, a cathedral-sized cavern, a dragon
  asleep, the sea at dawn.
- **Write it**: a slow swell (dynamics from `p` to `f` over 8-16 beats), major with the
  raised fourth (Lydian: I - II - I, or I - IVmaj7 with the #4 in the tune), wide
  spacing (basses low, violins high, nothing in between at first, then the middle
  fills), horns on a broad rising sixth, harp glissando-like runs and a cymbal roll into
  the peak. Then stillness.
- **Not**: a march or busy rhythm - wonder stands still.

### Spellcraft (from knowledge)
- **Signals**: magic being worked: a wizard's study, a spell, an enchanted object, a
  portal opening.
- **Write it**: shimmering high textures: `celesta`, `glockenspiel` and `harp` in fast
  arpeggios of whole-tone or augmented chords (I+, bVI+), `tremolo` violins high and
  soft, a flute run up; for power, the low strings sliding up (`slide`) into a held note.
  A wizard's character: a playful tune in clarinets and bassoons for a tinkerer, a
  slow modal tune in english_horn for a sage.
- **Not**: a whole piece of glitter; a sparkle needs a melody or a still harmony under it.

### Dream and hallucination ("Disney Acid Sequence")
- **Signals**: a dream, a vision, intoxication, a fey glamour, a mind-spell, the Far
  Realm seeping in.
- **Write it**: harmony that drifts: chords a third apart without a home (I - bIII - bVI
  - III), whole-tone runs in celesta and flutes, a waltz that keeps losing its downbeat;
  `unhinge` **all** parts gently (small drift, long windows) so the whole orchestra
  floats; slides on melody notes; tempo ritards and speeds up. Return to true pitch on
  waking.
- **Not**: the madness device - madness is one voice breaking; a dream is the whole world
  soft.

### The half-remembered tune ("Dream Melody")
- **Signals**: a past someone has lost: an amnesiac, a changeling, a reincarnated soul,
  a soldier who forgot home; a clue in a melody.
- **Write it**: a character's (or their homeland's) tune heard only in **fragments**: the
  first phrase, unfinished, in a solo voice (flute, oboe, celesta), with a `wobble`,
  stopping before the cadence; later appearances get a little further each time. The
  full tune, with its proper cadence, when the memory returns.
- **Not**: the whole tune early - the point is the missing ending.

---

## Romance and tenderness

### Seduction ("Sexophone")
- **Signals**: allure, a courtesan, a charmer, a rakish rogue, a vampire's or a fiend's
  temptation.
- **Write it**: no saxophone - a low `clarinets` or `english_horn` solo, slow (~60-70),
  with a swung or lazy rhythm, slides into notes (`slide` from -1 or -2), chromatic
  lower neighbours; chords with sevenths and ninths (i7, iv7, bVImaj7, V7), brushed pulse (`kit` `ride` very soft on the off-beats),
  pizzicato walking bass. For a dangerous seducer, let the chords tilt minor and the
  violins enter in tremolo.
- **Not**: loud or fast; seduction is close and unhurried.

### The missing answer ("Un-Duet", "Solo Duet")
- **Signals**: a broken bond: a lover gone, a betrayal, a friend dead or estranged; or
  loneliness shown as a conversation with oneself.
- **Write it**: take the Love Theme's two voices (the tune and its answering second
  voice). *Un-Duet*: play the first voice exactly as before, and where the answer used
  to come, leave a rest - one held chord or nothing. *Solo Duet*: one instrument (a
  solo oboe, solo_violin) plays both the question and the answer, the answer an octave
  lower and softer. Thin accompaniment.
- **Not**: a new theme; it only works if the table has heard the duet first.

### Sentimental Music Cue ("Sentimental Music Cue")
- **Signals**: reconciliation; the conflict is resolving; an apology accepted; a
  homecoming.
- **Write it**: warm `strings` swelling from `pp` to `mf` on a major progression with
  suspensions (I - IVadd9 - vi7 - IV - Isus4 - I), the tune (or the Love Theme) in
  violins in octaves or in horns, harp arpeggios; slow (~66-72). Enter just after the
  words that turn the scene, not before.
- **Not**: entering before the turn - then it spoils it (it becomes a Musical Spoiler).

### Lullaby ("Soundtrack Lullaby")
- **Signals**: sleep, safety, a child, a mother's memory, a guardian's watch, peace
  before the storm; the gentle side of a giant or an old soldier.
- **Write it**: rocking meter (6/8 or 3/4) at ~50-60, a tune in a narrow range falling
  at phrase ends, `celesta` or `harp` or flute, soft `strings` on I and IV with a pedal
  in the bass, `p` throughout; end on a held I with a ritard. A lullaby slightly out of
  tune (`wobble` on long notes) or in minor becomes Innocence corrupted.
- **Not**: brass, drums, wide leaps.

### Wedding processional ("Lohengrin and Mendelssohn")
- **Signals**: a wedding, a betrothal, a noble alliance sealed; a coronation's entrance.
- **Write it**: both stock pieces are public domain (Wagner's bridal chorus, Mendelssohn's
  wedding march), but for character use write a processional: a stately 4/4 march at a
  walking pace (~72-80), dotted rhythms, a trumpet fanfare opening (Mendelssohn's style:
  repeated notes in triplets rising to a chord), `organ` or strings on full
  major chords, bells at the end. For an ill-fated wedding, the same march with the
  Dread drone under it, or turned minor at the last phrase (Last Note Nightmare).
- **Not**: quoting either piece where it would make a scene a joke.

---

## Sorrow and death

### Leitmotif upon Death ("Leitmotif upon Death")
- **Signals**: a character dies; the table hears their theme one last time.
- **Write it**: the character's own tune, slowed (half tempo or more), `p`, on one
  solo voice (the instrument that played it first, or english_horn/solo_violin), over
  held strings; the harmony darkened only at the end (the last chord iv or vi instead of
  I); **stop before the last note** or let it fade on a held note with no cadence. An
  echo of the opening phrase in the harp or celesta after a silence.
- **Not**: a generic sad piece - it must be their tune, or the death is anonymous.

### Funeral hymn ("Amazing Freaking Grace"; the funeral march, from knowledge)
- **Signals**: a funeral, a vigil, a fallen comrade honoured; a temple's rites for the
  dead; a paladin's oath at a grave.
- **Write it**: a **chorale**: a plain hymn tune in slow quarter and half notes (~56-63),
  four-part block chords on every beat (organ, or a brass choir of horns, trombones and
  tuba, or strings), plain diatonic harmony with plagal endings (IV - I, "amen"), soft
  `bells` on the tonic at each phrase end. The funeral march variant: 4/4 at ~50, minor,
  a dotted rhythm (long-dotted-short-long) on muffled timpani and low strings. The
  character's theme can be re-cast as the hymn tune.
- **Not**: crying strings over it - a hymn's dignity is its plainness.

### Melancholy Major Key ("Melancholy Major Key")
- **Signals**: bittersweet: a farewell, a happy memory of the dead, an old hero's last
  ride, an autumn town, a mentor's pride in a student who will leave.
- **Write it**: a major key, slow (~60-72), soft, legato; falling lines; borrowed minor
  chords (iv, bVI) at the turns; suspensions (4-3, 9-8) that resolve late; a solo voice
  (english_horn, horns, cellos) and few instruments; end on I with the added sixth or
  ninth (`I6`, `Iadd9`) so it does not quite close.
- **Not**: bright and fast; then it is simply happy.

### Opera Means Drama ("Opera Means Drama")
- **Signals**: grand tragedy, fate, a death with spectacle; a theatrical villain or a
  diva; a duel at the opera house.
- **Write it**: a soaring operatic line in the highest voice (`violins` in octaves, or
  the choir's top line alone in long notes) over a pulsing orchestra (repeated chords
  in strings, `"xooo"`), harmony with strong applied dominants and diminished sevenths,
  big dynamic swells, a sustained high note at the climax and a ritard into the final
  cadence. Minor for tragedy.
- **Not**: restraint - this device is excess on purpose.

---

## Tension and suspense

### Silence and the stop ("Dramatic Pause", "Sudden Soundtrack Stop")
- **Signals**: the moment everything hangs: a blade at the throat, the dragon opening an
  eye, a confession, a failed save revealed.
- **Write it**: the music **stops dead** (all parts end at the same beat; a cut-off on an
  unresolved chord - V, a diminished seventh, a sus4) and stays silent for 1-4 beats or
  until the reveal, then comes back with the Shock, the Lament, or nothing. In a loop,
  write the stop as a separate short cue.
- **Not**: a fade-out - a fade releases tension; a stop holds it. (Expect the critic to
  flag the seam: here it is intended.)

### Bell ostinato ("Chaos of the Bells")
- **Signals**: relentless, mounting dread in action: a ticking ritual, a winter hunt, a
  cult's procession, a pursuit through the frozen city.
- **Write it**: a four-note figure in minor 3/4 (one bar: a high note, the step below,
  back, and a step lower again - the *Shchedryk* contour, public domain) repeated every
  bar without change in `bells`/`glockenspiel` and pizzicato, while everything else
  grows around it (Boléro Effect): strings in tremolo, then low brass, choir chanting held
  chords, taiko; tempo ~100-140; end with the figure alone, or cut off.
- **Not**: a cheerful major version in a tense scene - the minor and the stubborn
  repetition are the device.

### Descent ("Descent into Darkness Song")
- **Signals**: a piece that starts innocent and ends dark: a character's fall told in one
  piece; a festival that becomes a massacre; a lord's tour of his estate that ends in
  the dungeon.
- **Write it**: begin bright (major, light accompaniment, upper register) and darken in
  steps across the piece, each step one dial: the mode turns minor, the bass drops an
  octave, a drone enters, the tempo slows a little, a dissonant note joins the chords
  (add the bII), the light instruments drop out, low brass and choir enter. The end in
  the darkest colour, quiet or loud.
- **Not**: one sudden switch (that is Last Note Nightmare); a descent has stairs.

### Mystery and investigation (from knowledge)
- **Signals**: a puzzle, a crime scene, a library of secrets, an inquisitor or a
  detective, a cryptic sage.
- **Write it**: a light, steady, unresolved pulse (pizzicato or harp on eighths,
  `p`), modal or whole-tone harmony that avoids V-I (i - ii° - i, or sus chords that
  never resolve), a curious melody in clarinets or flute with questioning upward leaps,
  celesta for a clue, a held tremolo for a realisation. Loopable, ~90-100.
- **Not**: dread - a mystery is curious, not afraid.

---

## Horror and the uncanny

### Creepy jazz ("Creepy Jazz Music")
- **Signals**: a smooth, amused menace: a crime lord, a hag playing host, a devil
  offering a contract, a con artist.
- **Write it**: swung rhythm (lines in long-short pairs), a pizzicato walking bass
  (quarter notes moving by step and chromatic approach), `kit` `ride` softly on the
  off-beats, a melody in low clarinets or trombone with slides, chords full of
  sevenths and flat ninths (i7, iv7, bII7, V7 - and diminished passing chords),
  ~80-100, `p`-`mp`. A muted-brass stab at the end of phrases.
- **Not**: fast and bright - it should sound like a smile that doesn't reach the eyes.

### Backwards ("Creepy Backwards Music")
- **Signals**: something against nature: a ghost, a time curse, necromancy that
  reverses death, a mirror world.
- **Write it**: the format cannot reverse audio, so write the **shape** of reversed
  sound: notes that start from nothing and swell to a sudden cut-off (`reverse_cymbal`
  into a downbeat, strings crescendo on a held note then stop dead); the tune played in
  **retrograde** (its notes in reverse order) by celesta or solo_violin; harmony
  progressions backwards (V-IV-I becomes I-IV-V, never resolving).
- **Not**: overusing the reverse cymbal - it becomes a transition effect, not an omen.

### Dance of the bones ("Xylophones for Walking Bones")
- **Signals**: skeletons, a necromancer's dance, the dead rising at midnight, a lich's
  court.
- **Write it**: no xylophone - dry, hollow clicks: pizzicato and `glockenspiel` in low
  octaves and staccato, doubled by high `toms`/woodblock-like `kit` strokes; a
  macabre **waltz** (3/4, ~120-140; Saint-Saëns' *Danse macabre* is public domain: the
  midnight bell strikes twelve, then a violin tuned with a tritone plays the dance); the
  solo_violin on the tritone (A - Eb) and a sly minor waltz tune, bassoons for the
  rattle.
- **Not**: long held notes - bones click, they do not sing.

### Soundtrack Dissonance ("Soundtrack Dissonance")
- **Signals**: horror by contrast: a cheerful tune under a massacre, a calm melody as a
  sadistic villain works, a lullaby as the house burns. A villain who enjoys it.
- **Write it**: a sweet, major, regular piece (a minuet, a music box, a pastoral flute
  tune), **played straight and unchanged** while the scene is dreadful; at most a
  low drone underneath. The horror is the music's refusal to react.
- **Not**: bending the music toward the scene - the moment it reacts, the irony is gone.

### The haunting (from knowledge)
- **Signals**: a ghost, a haunted manor, a banshee, the memory of a death clinging to a
  place.
- **Write it**: a solitary high voice (flute low and breathy, `solo_violin` high and soft,
  or one choir line) with a slow `wobble` and `slide` at phrase ends, coming from
  nowhere over silence or a very soft high tremolo cluster; an old tune (a waltz, a
  ballad) half-heard in fragments; occasional celesta notes. Very slow, very soft.
- **Not**: loud scares - a ghost is felt first.

### The infernal (from knowledge)
- **Signals**: devils, demons, a fiend's pact, the Nine Hells, a warlock's patron.
- **Write it**: the tritone everywhere (I - #IV°, the bass leaping a tritone), low brass
  and choir in **parallel** fifths or tritones, `organ` low pedal, rhythmic `taiko` and
  `toms` in an uneven meter (7/8 or 5/4 grouped 3+2), a fanfare in trombones that
  inverts the hero's horn call (falling where it rose). A devil's fiddle: solo_violin
  playing a fast, virtuosic minor tune (wild but precise, unlike Madness).
- **Not**: confusing it with Doom (sacred and Latin) or Madness (a mind breaking).

---

## Mood colours

### Merry in Minor Key ("Merry in Minor Key")
- **Signals**: cheer with an edge: a dwarven drinking song, a rogues' tavern, a nomad
  dance, a pirate crew, a trickster's game.
- **Write it**: minor (Dorian or the harmonic minor), but fast (~130-170), dance meter
  (a 6/8 jig or a 2/4 polka), staccato and accented, a stamping pulse (timpani or
  `toms` on 1, pizzicato off-beats), the tune doubled by clarinets and violins,
  accelerando at the end.
- **Not**: slow - minor plus slow reads as sad no matter what.

---

## Places and peoples ("Regional Riff", "Genre Motif"; fetches blocked, from knowledge where marked)

### Instrument colours ("Mood Motif"; from general orchestration practice)
- **Signals**: what each instrument tends to say on its own - some associations feel
  natural (a low clarinet is dark, a celesta ethereal), others are learned conventions
  (the oboe pastoral, the organ sacred, the trumpet royal or military) and work because
  listeners share them (research §7.5).
- **Write it** - a palette, not rules:
  - *flute*: air, birds, innocence, magic, the wild; *piccolo*: whimsy, a fife's march;
  - *oboe*: pastoral, plaintive, a lonely voice; *english horn*: distance, solitude,
    longing; *clarinet*: low - dark, sly, secretive; high - playful, bright; *bassoon*:
    comic when quick and staccato, grave when slow and low;
  - *horns*: heroism, nobility, the hunt, distance and nature, a call across a valley;
    *trumpets*: royalty, the army, alarm, triumph; *trombones*: solemnity, judgement,
    the sacred, doom, weight; *tuba*: mass, menace, or comedy;
  - *strings*: feeling, warmth, longing; *tremolo*: tension, shimmer; *pizzicato*:
    sneaking, comedy, a clock; *solo violin*: intimacy, the fiddler, the devil's
    instrument of folklore; *solo cello*: grief, nobility, a human voice; *basses*:
    the ground, the deep, dread;
  - *harp*: heaven, magic, elegance, water; *celesta*: fairies, a music box, enchantment;
    *glockenspiel*: childhood, sparkle; *bells*: church, celebration, death, a city's
    hour; *organ*: the sacred, the gothic, horror;
  - *choir*: the sacred, the epic, a people, mourning, the ominous (low, chanting);
  - *timpani*: thunder, fate, a heartbeat; *snare*: the army; *bass drum*: doom, a march,
    footsteps; *gong*: ceremony, a far land, an ending; *triangle*: sparkle.
- **Not**: an instrument used against its colour without meaning to - a tuba lead for an
  elf princess is a joke, so only do it as one.

### A genre as a people's sound ("Genre Motif")
- **Signals**: a subculture known by its music: smooth city criminals, a frontier, a
  merry town, an old court, a youth in revolt.
- **Write it**: borrow the genre's rhythm and harmony, played by the orchestra:
  - *swing* (jazz feel: long-short pairs of eighths, 7th and 9th chords, walking
    pizzicato bass, a muted or sly clarinet lead, snare brushed on 2 and 4 as `kit`
    snare softly) - a smooth rogue, a thieves' guild, a gambling den;
  - *the open frontier* (open fifths and wide spacing, horns and strings, a hoedown's
    quick fiddle tune on violins over a pizzicato "oom-pah", plain I-IV-V) - a frontier
    town, cattle-drovers, a wide plain;
  - *the oompah band* (tuba on 1, horns or trombones on 2-3 or the offbeat, clarinets
    on the tune, 2/4 or 3/4, major) - a jolly town, a beer hall, a festival;
  - *driving rock* - see the rock drive; *folk* - the tavern; *the court* - the court
    dance; *ambient* - dungeon ambience.
- **Not**: a modern genre where the setting can't bear it, unless the anachronism is the
  point.

### Regional colour - borrowing a real tradition ("Regional Riff")
- **Signals**: where we are. In this world the peoples are invented, so a real
  tradition is a palette to build one from: take its scale, rhythm and colour, change
  it, and give the people their own motif.
- **Write it** (the orchestra has none of these instruments; the substitutes):
  - *South Asian*: a held drone (tonic and fifth, strings or organ), a melismatic oboe
    or english horn with slides and ornaments, toms in a long cycle;
  - *Japanese*: harp plucked sparsely (koto), a breathy flute with bends (shakuhachi),
    the in scale (1 b2 4 5 b6), silence between phrases, taiko for warriors;
  - *Chinese*: pentatonic, a solo violin with expressive slides (erhu), harp or
    pizzicato tremolo (zither), gong to mark a scene;
  - *Mongolian / the steppe*: a low choir drone with a high flute floating over it
    (throat singing's overtone), horse-gait rhythms in toms;
  - *Southeast Asian*: interlocking celesta, glockenspiel, bells and harp in a five-note
    scale, layered cycles (gamelan);
  - *Middle Eastern*: the Phrygian dominant (Hijaz) or a minor scale with a lowered
    second, an oud's plucked chords on harp, a solo voice line (oboe), frame-drum toms;
    see Desert;
  - *Armenian / Caucasian*: a low, slow english horn or clarinet with soft ornaments
    over a drone (duduk); a fast dance in 6/8 (lezginka) on violins and toms;
  - *Greek / Italian*: fast pizzicato tremolo (bouzouki, mandolin), the tarantella's
    quick 6/8;
  - *Spanish*: strummed pizzicato chords, the Phrygian cadence (iv - bIII - bII - I),
    claps as `kit` snare or toms, castanet-like quick ticks;
  - *Central European*: the oompah band; a cimbalom's shimmer as harp with celesta;
    *Alpine*: horns on natural notes with echoes;
  - *Klezmer*: clarinet and violin with bends and laughing slides, the freygish mode
    (Phrygian dominant), a dance that speeds up;
  - *Russian*: a deep male choir (basso profundo: low `choir` on long notes), a
    balalaika as pizzicato tremolo, the peasant choir's open harmonies;
  - *Georgian*: a choir in close, clashing three-part harmony resolving to open fifths;
  - *Scandinavian*: a fiddle tune with drones (Hardanger fiddle: solo violin over held
    open strings); see The north;
  - *British / Irish*: stately ceremonial brass (England), Highland pipes (see that
    entry), a jig on fiddle and flute (the tavern), a Welsh male voice choir;
  - *American*: a Sousa march (brass, piccolo, snare), the frontier's open fifths, a
    jazz clarinet's slide up into a big-city tune;
  - *Latin American*: trumpets in thirds over strummed pizzicato in a fast 3/4
    (mariachi), a breathy pentatonic flute (Andes quena), layered samba toms, snare and
    taiko (batucada);
  - *Australian*: a basses' drone with rhythmic accents (didgeridoo);
  - *the cold far south, or space*: silence, wind-like tremolo, a held drone, very slow
    consonant music.
- **Not** - the clichés the convention itself counts as discredited or lazy: one
  "oriental riff" for every eastern people; generic "war drums" for any native people;
  generic jungle drums and chanting for a whole continent; the Hijaz scale for every
  people from Morocco to India; bagpipes for Ireland, mariachi for all of Latin
  America. A people is more than its stereotype - give them a motif of their own and
  vary the palette.

### The road ("'Setting Off' Song", "Wanderlust Song")
- **Signals**: travel, the journey begun, a wanderer, a caravan, the open road.
- **Write it**: a walking pulse (pizzicato or `cellos` on quarter notes, 4/4 at ~100-112,
  or a 6/8 lope), open harmony (I - IV/I - I - bVII, the bass staying on the tonic as a
  pedal), the tune in horns or flute, wide in range with a long rise; a new key each
  time it returns ("over the next hill"). For a wanderer's theme, a lone flute or oboe
  over a drone of open fifths.
- **Not**: a march - a march is an army; a journey strolls.

### The place's own rhythm ("Everything Is an Instrument", "Music from the Mundane", "Serendipitous Symphony")
- **Signals**: a place made of its work: the forge, the mill, the shipyard, the
  marketplace, a clockwork tower, the walking Keep's gears.
- **Write it**: turn the place's sounds into the accompaniment: the smith's hammer as
  accented hits (`timpani` or `toms` on `"x  x  xo"`), the mill wheel as a turning
  ostinato in the cellos, the market as overlapping short figures in woods, a ship's
  creak as a slow `slide` in the basses. Then put the tune over it.
- **Not**: realistic sound effects - the orchestra suggests the sound in rhythm and pitch.

### Requiem for a Landmark ("Requiem for a Landmark")
- **Signals**: a beloved place destroyed or under threat: the village burned, the
  tavern in ruins, the temple desecrated, the home fortress besieged.
- **Write it**: the place's own music, **recognisable**, but: minor (the same tune with
  `"mode": "minor"` or its chords swapped I -> i, IV -> iv), half tempo, the cheerful
  accompaniment gone (held strings or a lone instrument), a drone under it; or, for a
  place in danger, the same music faster with tremolo and a panic layer. Rebuilt, it
  returns in its old form (Triumphant Reprise).
- **Not**: new music - the loss lands only if the table knows the old tune.

### Dungeon ambience ("Dungeon Synth")
- **Signals**: the dungeon, the crypt, the dark tower, the old ruin; an endless loop
  for exploration.
- **Write it**: the genre's essence without synths: very slow (~50-60), a simple modal
  minor tune (Aeolian or Dorian, a few notes, repeated with small changes), held
  `organ` or `strings` chords at low volume as a pad, `choir` soft on long chords, a
  bass pedal; sparse harp or celesta notes like dripping water. Seamless `loop`, mild
  dynamics.
- **Not**: events in the music (hits, swells) - an ambience must sit under the table's
  talk for a long time.

### The cell ("Captivity Harmonica")
- **Signals**: prison, captivity, a slave pit, a lonely watchman, the party jailed.
- **Write it**: no harmonica - a lone reedy voice (`clarinets` in its middle register,
  or `oboe`) playing a simple, folk-like, slow tune with bends (`slide` from -1 into
  notes) and long pauses, no accompaniment or a very low held note; echo it with a
  quieter repeat (the cell's acoustics).
- **Not**: full strings - captivity is one voice.

### Musette ("French Accordion")
- **Signals**: a cosmopolitan city, a café, a canal quarter, romance in a city of
  artists; a charming, slightly melancholy rogue.
- **Write it**: a waltz (3/4, ~150-170 for the dance or ~100 for nostalgia), oom-pah-pah
  in pizzicato (`"xoo"`, bass on 1, chords on 2-3), the tune in `clarinets` in thirds
  (they stand in for the accordion's reeds) with chromatic ornaments and grace notes,
  minor with a sweet turn to the relative major.
- **Not**: slow and heavy - a musette spins.

### Highland pipes ("Everything's Louder with Bagpipes")
- **Signals**: highland clans, a mountain kingdom, a warband's march, a funeral in the
  hills; a stubborn, proud warrior.
- **Write it**: no bagpipes - a **drone** of open fifths (tonic and fifth held in
  basses, cellos and bassoons, `"-"`), the tune in `oboe` and `piccolo` in unison (the
  chanter's reedy edge) with grace-note flourishes (short notes a step above before
  main notes), Mixolydian (the flat seventh) or pentatonic, a snare pattern for a march
  in 2/4 or 6/8 or no pulse for a lament.
- **Not**: harmonised chords moving under it - the drone must not change.

### Festival trumpets ("Gratuitous Mariachi Band")
- **Signals**: a sunlit southern land, a fiesta, a lively trading port, a boisterous
  noble family's feast.
- **Write it**: two `trumpets` in parallel thirds or sixths, bright, with a slight
  `wobble` vibrato, 6/8 alternating with 3/4 (the hemiola: accents
  `"x o x o x o"` against `"x  x  "`), pizzicato strumming chords, violins doubling the
  tune, major with I - IV - V7. Fast (~180 eighths).
- **Not**: a caricature - write it as a real people's festive music, not a joke about
  them.

### Islands ("Steel Drums and Sunshine")
- **Signals**: tropical islands, beaches, a merfolk market, a carefree lagoon, a pirate
  haven at rest.
- **Write it**: no steel drums - `celesta`, `glockenspiel` and `harp` together on a
  syncopated pattern in the calypso 3+3+2 (`"x  x  x "`), bright major (I - IV - V - I),
  pizzicato bass on the offbeats, flutes on the tune; ~100-110.
- **Not**: dark harmonies - the device means sunshine.

### Deep jungle ("African Chant", "Jungle Jazz")
- **Signals**: the deep jungle, a lost temple in the green, a hunters' people, a
  beast-god's domain.
- **Write it**: polyrhythmic drums (`taiko`, `toms` and timpani in interlocking patterns,
  e.g. 3 against 2: `"x  x  "` against `"x x x "`), a `choir` in rhythmic unison chant on
  a few notes with call (one line) and response (the full choir), held notes of a beat or
  more; or, for an adventurers' jungle trek, a slinky clarinet tune with muted-brass
  stabs and swung toms. Pentatonic.
- **Not**: invented "tribal" gibberish passed off as a real people's music - make it
  this world's people, with their own motif.

### The crowd ("Crowd Song", "Big Finale Crowd Song", "Angry Mob Song")
- **Signals**: a people acting as one: an uprising, a festival, an angry mob with
  torches, the cheering arena, the finale where everyone the party saved stands with
  them.
- **Write it**: the `choir` in **unison or octaves** (one line, not chords) on a short,
  repeated, rhythmic figure (long notes on the beats; the choir cannot do quick
  rhythms), doubled by low brass and strings, `taiko` and `bd` on the beat like
  stamping. Angry mob: minor, accelerating, the figure rising each repeat. Big finale:
  major, the party's theme taken up by the choir and full orchestra.
- **Not**: soft harmonised choir chords - that is a lament or a prayer, not a crowd.

### The court dance (from knowledge)
- **Signals**: a royal court, a masked ball, diplomacy, a noble's poise; old manners.
- **Write it**: a minuet (3/4, ~110, elegant, two-bar phrases with a lift on beat 2) or
  a pavane (slow 4/4, stately), strings and woods only, plain functional harmony,
  ornaments (short grace notes, trills as alternating notes in flutes), `harp` in place
  of the harpsichord's continuo. Pairs well as the Façade's lighter cousin.
- **Not**: heavy brass and drums.

### The tavern (from knowledge)
- **Signals**: the inn, the hearth, a festival in the village, halflings, a cheerful
  bard.
- **Write it**: a jig (6/8, ~110-120 dotted quarters) or a reel (2/2, fast), the tune in
  `flutes` and `violins` together, drone or simple I - V bass in cellos, pizzicato
  strumming on the beat, `toms` or timpani lightly on 1, Dorian or Mixolydian for a folk
  colour. Loopable.
- **Not**: grand orchestration - a tavern is a few players.

### Desert (from knowledge)
- **Signals**: deserts, a sultan's city, a djinn, desert nomads, an ancient tomb under
  the sand.
- **Write it**: a scale with the augmented second (the Phrygian dominant: 1 b2 3 4 5 b6
  b7) or Hijaz-like turns, a held drone on the tonic and fifth, a melismatic solo in
  `oboe` or `english_horn` with slides and ornaments, frame-drum-like `toms` in an
  uneven rhythm (3+3+2), heat shimmer as a `wobble` on long string notes; harp for an
  oud's plucked chords.
- **Not**: a single "snake charmer" cliché for every desert people.

### The far east (from knowledge)
- **Signals**: an island empire, a temple in the mountains, a disciplined warrior
  order, a monk.
- **Write it**: pentatonic (major or minor, no semitones), `flutes` with slides into
  notes (a bamboo-flute's bend), `harp` and pizzicato in sparse plucked patterns (a
  zither's), `taiko` for the warrior, `gong` (`kit` `gong`) to mark a scene. Open
  fourths and fifths rather than full triads.
- **Not**: a gong-and-pentatonic stamp on every eastern-flavoured people; make each one's
  own motif.

### The north (from knowledge)
- **Signals**: frost lands, longships, a barbarian clan, a mead hall, giants.
- **Write it**: open fifths and power chords (`"i5"`, `"bVII5"`, `"bVI5"`), Aeolian or
  Dorian, low male `choir` on held chords ("hum" of warriors), horns in unison on a
  bold modal tune, a pounding `taiko`/`toms` heartbeat, low drones; slow and heavy
  (~70) or a fast war dance.
- **Not**: bright major brass - the north is stark.

### Sylvan and elven (from knowledge)
- **Signals**: elves, an ancient forest, a druid circle, a hidden valley.
- **Write it**: harp arpeggios, flutes and `strings` soft, modal harmony (Dorian,
  Lydian, or Mixolydian with bVII - I), long legato lines, wide intervals in the tune
  (sixths, sevenths), the `choir` soft and high for age and grace; Avian Flute for the
  wild. Slow-moving, ~60-80.
- **Not**: quick march rhythms - elves are timeless.

### Under the mountain (from knowledge)
- **Signals**: dwarven halls, mines, deep forges, a stone kingdom.
- **Write it**: low male `choir` in slow held chords (Dorian or minor), trombones and
  tuba, `cellos` and `basses` doubling a stern, stepwise tune, the anvil as the place's
  own rhythm (`timpani`/`toms` accents in a steady 4/4), an echo (the same phrase
  repeated softer). Proud and heavy, ~60-80.
- **Not**: high bright woodwinds as the lead.

### Under the sea (from knowledge)
- **Signals**: underwater realms, a drowned city, merfolk, a sea-witch, a kraken's
  lair.
- **Write it**: harp and celesta in slow, overlapping arpeggios (rising and falling like
  currents), `strings` soft and wide, whole-tone or Lydian colour, a gentle `wobble` on
  long notes, no hard attacks; for menace, a deep `slide` down in the basses and a low
  choir.
- **Not**: a strong beat - water has no downbeat.

---

## Time and nostalgia

### Nostalgic music box ("Nostalgic Music Box", "Music Box Intervals")
- **Signals**: a memory, childhood, a keepsake, home far away, a lost family. Tender,
  not creepy (compare Innocence corrupted).
- **Write it**: `celesta` or `glockenspiel` playing the tune simply, high, a little slow,
  in the clear (alone, or with soft `strings` on I and IV); used as a **passage inside
  a larger piece** (an interval: the orchestra drops away, the music box plays a phrase,
  the orchestra comes back with the same tune). End with a ritard as if the box runs
  down.
- **Not**: `wobble` and drones - those turn it ominous.

### The hour strikes ("Westminster Chimes")
- **Signals**: a city's clock tower, time running out, midnight, the deadline of a
  ritual, a clockwork city.
- **Write it**: the four-note quarter-hour chime (public domain; its four permutations of
  the notes 3, 2, 1, 5 of a major key) in `bells`, slow, then the hour struck on the low
  tonic, counted; under it a held chord or the Tick Tock pulse. For dread, strike in
  minor, or let the last stroke be a bII.
- **Not**: using it outside a city or a clock; it signals a clock tower, not any bell.

### Yearning ("'I Want' Song")
- **Signals**: a dream not yet reached: the farmhand who wants to be a hero, the exile who
  wants home, the young noble who wants freedom. The beginning of a hero's arc (stage 0).
- **Write it**: a tune that reaches up and falls back: a rising major sixth or octave
  leap, then a descent by step; phrases that end on the second or fifth, not on the
  tonic; the harmony moving to IV and vi rather than home; one instrument (flute,
  horn, violins) over a gentle pulse. Save the full cadence on the tonic for when the
  wish is fulfilled (stage 3).
- **Not**: a triumphant ending - the longing is in the lack.

---

## The sacred

### Jubilant congregation ("Gospel Choirs Are Just Better")
- **Signals**: a living, joyful faith: a god of the sun or of harvest, a temple
  festival, a healer's miracle, a celebration of a saint.
- **Write it**: call and response (a solo line - one choir voice or trumpet - answered
  by the full `choir` on a held chord), major with plagal turns (IV - I, the IV with
  its added sixth or seventh), `organ` held, a swinging pulse with hand-clap-like
  accents on 2 and 4 (`kit` `snare` light, or pizzicato), a final key change up a half
  step for the last chorus.
- **Not**: Ominous Latin Chanting (minor, unison, cold) - this is warm, many voices.

---

## Trait table: from a character's description to devices

| Their description says... | Carry the piece with | Add at their moments |
|---|---|---|
| elegant, aristocratic, refined, a lord | Façade (a dance) | Lament, Madness, Power |
| mad, obsessed, unstable, sleepless | Madness | Façade (what they were), Dread |
| grieving, guilty, tragic, lost someone | Lament | Façade, Corruption |
| conqueror, warlord, army, relentless | Power (a march) | Doom, Shock |
| cult, priest, undead, a god | Doom (organ, choir, bells) | Dread, Lament |
| childlike, trickster, uncanny | Innocence corrupted | Madness, Shock |
| hidden, scheming, spy | Dread (a drone) under a Façade | Shock at the reveal |
| hero, protector | the tune itself, growing (stages) | Fanfare, Love Theme |
| a hero darkening | Corruption of their tune | Lament, Madness |

Every villain also gets a **Power** battle piece on their tune (the table plays it in any
fight they're in).

## Trait table: from a character's description to devices (extended)

The original table stands; these rows add the rest of the RPG cast. "Carry" is the
texture that runs through; "add" enters at their moments. Devices without a section name
are in `devices.md`.

| Their description says... | Carry the piece with | Add at their moments |
|---|---|---|
| knight, paladin, sworn to a cause | The horn call, then the tune growing | National Anthem (their order), Saved by the Church Bell, Funeral hymn (for oaths at graves) |
| ranger, scout, hunter, wanderer | The road (lone flute over open fifths) | Avian Flute, Sylvan and elven, The horn call |
| barbarian, berserker, northern warrior | The north (drums, open fifths) | Rock drive in fights, The crowd, Power |
| fighter, soldier, veteran | A march (Power, but major) | Melancholy Major Key (memories), Funeral hymn |
| swashbuckler, duelist, pirate | Happy Battle Music (a 6/8) | Merry in Minor Key, Showman's bookends |
| rogue, thief, burglar | Sneaking | Creepy jazz (if dangerous), Mickey Mousing (if comic) |
| assassin, cold killer | Dread drone under a slow Sneaking | Soundtrack Dissonance (calm as they kill), Shock |
| trickster, prankster, mischief-maker | Mickey Mousing | Deflation, Stings, The circus (happy) |
| con artist, smooth crime lord | Creepy jazz | Façade, Showman's bookends |
| bard, performer, showman | Showman's bookends + their tune as a dance | The dreadful bard (if bad), Musette, The tavern |
| noble, courtier, diplomat | The court dance | Façade (if false), Wedding processional |
| king, queen, ruler, a realm | National Anthem | The horn call, Saved by the Church Bell, Requiem for a Landmark (a fallen realm) |
| scholar, sage, wizard | Spellcraft (a sage's modal tune) | Mystery and investigation, Wonder and discovery |
| tinkerer, gnome, artificer | Mickey Mousing + The place's own rhythm (gears) | Spellcraft, Happy Battle Music |
| detective, inquisitor, spymaster | Mystery and investigation | Dread, Foreshadowing and the lie |
| priest, cleric of a kind god | Jubilant congregation or Holy Pipe Organ | Cherubic Choir, Funeral hymn |
| priest of a stern or dark god, cultist | Doom (organ, chant) | Bell ostinato, The infernal |
| healer, saint, gentle soul | Cherubic Choir | Lullaby, Sentimental Music Cue |
| druid, nature spirit | Sylvan and elven | Avian Flute, The road |
| fey, fairy, a fey lord | Ethereal Choir | Dream and hallucination, The circus (creepy, for a dangerous revel) |
| elves, an ancient people | Sylvan and elven | Ethereal Choir, Melancholy Major Key |
| dwarves, miners, smiths | Under the mountain | The place's own rhythm (anvil), Merry in Minor Key (drinking songs) |
| halflings, villagers, hearth folk | The tavern | Lullaby, Requiem for a Landmark |
| merchant, trader, caravan master | The road + a bright local colour (Festival trumpets, Desert, Musette) | Showman's bookends (if a huckster) |
| sailor, captain, merfolk | Accordion to Most Sailors, Under the sea | Islands, Merry in Minor Key |
| mentor, old master, retired hero | Melancholy Major Key | The horn call (their past glory), Leitmotif upon Death |
| child, orphan, the innocent | Nostalgic music box, Lullaby | Cherubic Choir; Innocence corrupted if threatened |
| amnesiac, changeling, reborn soul | The half-remembered tune | Dream and hallucination |
| lover, beloved, a romance | Love Theme | Sentimental Music Cue, The missing answer (when lost) |
| seducer, courtesan, vampire lord | Seduction | Façade, Creepy jazz |
| dreamer, young hero at the start | Yearning | The road; their full theme at stage 3 |
| prisoner, captive, exile | The cell | Yearning, The half-remembered tune |
| monster, beast, a dragon | Power on low brass + Wonder and discovery (first sight) | Shock, The great battle |
| undead: skeletons, a lich | Dance of the bones | Doom, Backwards |
| undead: ghost, banshee, a haunted house | The haunting | Backwards, Lament (One-Woman Wail) |
| demon, devil, warlock's patron | The infernal | Creepy jazz (a devil's bargain), Doom |
| mad jester, carnival villain, puppeteer | The circus (creepy) | Madness, Soundtrack Dissonance |
| sadist, villain who enjoys cruelty | Soundtrack Dissonance | Façade, Shock |
| theatrical villain, a diva | Opera Means Drama | Mock melodrama (if a fool), Power |
| pompous fool, a comic noble | Mock melodrama | Deflation, Mickey Mousing |
| a people rising, rebels, an uprising | The crowd (angry mob into finale) | National Anthem (their new flag), The climax |
| a falling hero, a slow corruption | Descent | Corruption, Lament |
| a hero who dies | Leitmotif upon Death | Funeral hymn, Withholding and the last reprise |
| the party as a whole | The party in counterpoint | Withholding and the last reprise, The climax |

Places, quickly: dungeon -> Dungeon ambience; city -> The hour strikes, Musette;
village and inn -> The tavern; wilds -> The road, Avian Flute; temple -> Holy Pipe Organ or
Jubilant congregation; court -> The court dance; prison -> The cell; ruins of a loved
place -> Requiem for a Landmark; workshop or forge -> The place's own rhythm.

Battles, quickly: ordinary fight -> Encounter battle music; villain -> Power (Boss
Remix); war or dragons -> The great battle; brawl -> Happy Battle Music; losing or
winning -> The turning tide; a costly fight -> Sad Battle Music.

---

## The evidence behind the devices (research.md)

- **Arousal first, then valence.** Tempo and loudness set arousal and outweigh most
  cues; mode sets positive/negative; cues add up (an additive model explains most of
  listeners' ratings), so stack several pointing the same way (ch14, ch17).
- **Madness / unease**: irregular rhythm, a wide range and fast motion read as uneasy;
  minor seconds, tritones and leaps beyond the octave as unstable; fear is quiet,
  staccato, with sudden dynamic swings and a high register (ch14) - the breaking
  violin's leaps too high, its slides and its stumbles. Notes shifted a semitone and
  then repeated read as "wrong" on purpose (ch13, ch21): the strings drifting.
- **Lament**: slow, soft, low, legato, dark, minor, falling minor seconds, a solo voice
  (ch14, ch17); "sad" music gives chills about twice as often (ch21).
- **Power**: loud and bright, large intervals, unisons and octaves; majesty with
  consonance and a regular rhythm (ch14).
- **Façade / dignity**: regular rhythm, little dynamic change, consonant harmony (ch14) -
  the steady dance the madness breaks.
- **Shock and the climax**: the strongest chill trigger is a sudden forte after a quiet
  passage; others are a new voice entering, a theme returning, an unprepared harmony, a
  texture change (ch21) - why a climax grows in waves and gets one surprise.
- **Expectation**: uncertainty breeds anxiety; a delayed return or a deceptive cadence
  keeps working on listeners who know it (ch21) - the madness's breaks, the unresolved
  ending.
- **Film**: music recolours a neutral character, before or after they appear, and its
  emotion attaches to what it's synchronised with (ch31) - why a portrait plays when the
  character is on stage.
- **Density and liking** (inverted U): liking rises with complexity up to a point and
  then falls; the best point shifts with what the listeners just heard, and people busy
  with a demanding task (a table playing) want simpler music. How typical a theme is of
  its kind predicted liking far better than its complexity. Simple music wears out
  faster with repetition, complex music grows on listeners (research §7.3) - a theme
  heard all campaign can afford some depth, but a 50-second piece carries one or two
  ideas, layered rather than chained.
- **What people actually feel from music** is mostly wonder, transcendence,
  tenderness, nostalgia, peacefulness, power, joyful activation, tension and sadness
  (the GEMS model); fear is recognised far more than felt, and felt emotion is mostly
  positive even for dark music (research §7.2, §8.1). Wonder is the strongest hook;
  nostalgia comes from memory - bring back a theme from an earlier session.
- **Mechanisms** (research §8.1): a sudden loud, rough or very fast onset raises arousal
  in under a second, even in people talking over the music - keep abrupt onsets for a
  deliberate sting; a theme repeatedly heard with an event takes on its feeling
  (conditioning) - play a character's theme at their good moments, not over a boring
  stretch; listeners mirror voice-like melodies (contagion) - singable lines carry
  feeling best; imagery and expectancy need attention - place music works while the
  scene is being described.
- **Movement**: music expresses emotion by resembling how people move - gait,
  posture, gesture (research §7.5). Model a character's theme on how they walk.
- **Arc**: a foreign note or chromatic turn gradually absorbed into the piece tells an
  outsider's story; a stepwise rise over a stepwise bass reads as hope; a collapse
  right after a peak is where grief lands (research §7.1).
- **Strong experiences** come from sound that envelops (a resonant hall, felt bass, a
  remarkable timbre) and often from bittersweet mixtures; loudness, shrill timbre and
  constant dissonance turn them negative (research §7.4).
- **Across cultures** tempo, loudness, register, range, timbre and complexity read the
  same way; scales and instruments are local. A snippet of a style stands for a whole
  people or place (research §7.1, §8.3) - give each people of the world its own motif.

---

## Appendix: tropes considered and not used

Reviewed: all 211 names in `trope-names.txt`. 35 are already in `devices.md` (listed
last); 85 are used above (57 entries); these 91 were excluded:

- Tropes - site navigation link, not trope
- Media - site navigation link, not trope
- background music - inline link to Background Music
- Sound FX Tropes - sound-effects index, not score
- Music Tropes - general music index, not score
- Music and Sound Effects - works index, not a device
- Audio Diegesis - index of diegesis tropes
- Evil Music Index - index page; members reviewed individually
- Genre Motif - index page; fetch blocked, see places
- Heroic Music Index - index page; fetch blocked, see heroes
- Mood Motif - index page; fetch blocked, see moods
- Theme Tune - index of opening-theme tropes
- a mock-up thereof - inline link, not a trope
- AM/FM Characterization - diegetic car-radio characterization
- Anachronistic Soundtrack - licensed modern songs, period pieces
- Associated Composer - production trivia about collaborators
- Background Music - the general concept, not device
- Bizarre Taste in Music - in-universe character taste
- Bootstrapped Theme - opening-theme production history
- Cartoon Conductor - cartoon sight gag
- Circus Synths - electronic timbre; no synths here
- Credits Medley - end credits practice
- Cult Soundtrack - reception phenomenon, not device
- Cyber Punk Is Techno - electronic sci-fi genre marker
- Diegetic Soundtrack Usage - in-universe humming of theme
- Diegetic Switch - diegetic-to-score editing trick
- "Do It Yourself" Theme Tune - cast performs theme; production
- The Elevator from Ipanema - specific pop song gag
- Familiar Soundtrack, Foreign Lyrics - foreign-language lyrics of covers
- Follow the Bouncing Ball - on-screen sing-along lyrics
- Foreign Re-Score - localisation production practice
- Forgotten Theme Tune Lyrics - unused theme lyrics
- Future Music - sci-fi futurism; not fantasy
- Happy Birthday to You! - copyright avoidance of one song
- "The Hero Sucks" Song - insult lyrics, musical number
- Iconic Sequel Song - franchise reception of songs
- Image Song - anime character tie-in songs
- Incessant Chorus - in-universe singing habit
- Interscene Diegetic - diegetic singing across cuts
- In-Universe Soundtrack - characters hear the score
- Invisible Backup Band - diegetic performance convention
- Isn't It Ironic? - misread pop lyrics
- Left the Background Music On - diegetic reveal gag
- Local Soundtrack - real-world local bands, licensing
- Real Life - inline link, not a trope
- Mocking Music - diegetic radio irony
- Musical Episode - whole episode is a musical
- Musical Gameplay - game mechanics, sound as input
- Musicalis Interruptus - interrupting a diegetic song
- Musical Number Fumbler - stage-musical performance mishap
- Musical Trigger - in-universe tune triggers plot
- Music Video Syndrome - editing style, not music
- Nothing but Hits - diegetic radio plays hits
- One-Man Song - song titles named after men
- One-Woman Song - song titles named after women
- Orchestra Hit Techno Battle - electronic rave genre
- Orchestral Version - soundtrack release practice
- Playlist Soundtrack - game playback shuffling
- Pop-Star Composer - composer celebrity, production
- Public Domain Soundtrack - sourcing practice; quotes used inside entries
- Recycled Soundtrack - reuse across works, production
- Recycled Trailer Music - trailer production practice
- Re-Release Soundtrack - home-release licensing changes
- Sidekick Song - musical-number type, lyrics
- Silent Credits - end credits practice
- Soap Within a Show - inline link, show-within-show
- melodramatic - inline link, not a trope
- Sound-Coded for Your Convenience - game interface sound cues
- Sound Test - game menu feature
- Source Music - diegetic music by definition
- Standard Snippet - stock quotations; specific ones used
- Stock Trailer Music - trailer licensing practice
- Sung-Through Musical - stage-musical form, lyrics
- Suspiciously Apropos Music - diegetic coincidence gag
- Suspiciously Similar Song - copyright sound-alikes
- Theme Music Abandonment - opening theme dropped by show
- Theme Song Reveal - opening credits spoil plot
- This Is a Song - self-referential lyrics
- Title Theme Drop - game title-screen practice
- "The Villain Sucks" Song - insult lyrics, musical number
- With Lyrics - lyrics added to instrumentals
- Music Video Tropes - index link, music videos
- Media Tropes - index link, media
- Manga Effects - index link, comics visuals
- Narrative Tropes - index link, narrative
- Rule of Glamorous - index link, not music
- Spectacle - index link, not music
- Sensory Index - index link, senses
- New Media Tropes - index link, internet media
- Comedy Tropes - index link, comedy
- About TVTropes - site link, not trope

Already covered in `devices.md` (not repeated): Accordion to Most Sailors, Avian Flute,
Boléro Effect, Boss Remix, Corrupted Leitmotif, Creepy Children Singing, Dark Reprise,
Drone of Dread, Drumbeat of Chaos, Fanfare, Haunting Harpsichord, Heartbeat Soundtrack,
High-Class Harpsichord, Holy Pipe Organ, Ironic Nursery Tune, Location Song, Lonely Piano
Piece, Love Theme, Musical Pastiche (Corruption's darker colour), Ominous Latin Chanting,
Ominous Music Box Tune, Ominous Pipe Organ, One-Woman Wail, Playing the Heart Strings,
"Psycho" Strings, Regional Riff, Sad Battle Music, Simple Score of Sadness, Sinister
Tango Music, Tense Tremolo, Theme Music Power-Up, Tick Tock Tune, Triumphant Reprise,
Victorious Chorus, Villain Song (the villain portraits; its lyrics are not used).

The *Evil Music Index*'s members were reviewed separately: the ones not already above or in the villain sections are Ghost Song, Theremin / Freaky Electronic Music and Conducting the Carnage (added under Villains); the rest are songs with lyrics (villain songs, duets, rock, Halloween songs), not orchestral devices.

From the *Heroic Music Index*: the songs that are lyrics rather than devices ("Bragging Theme Tune", "Bravado Song", "Christmas Songs", "'I Am Great!' Song", "'I Am' Song", "'The Villain Sucks' Song") are not used; its other members are covered above.
