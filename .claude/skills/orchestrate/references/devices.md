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
  (Juslin & Sloboda (eds.), *Handbook of Music and Emotion*, 2010; esp. Gabrielsson &
  Lindström, ch. 14);
- **Practice** - how one film composer's themes are built and transformed (Lehman,
  *Complete Catalogue of the Musical Themes of Star Wars*);
- **This table's ears** - `table-feedback.md` (the host's verdicts win over all of these).

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
