# Harmony: devices and when to use them

Chords are roman numerals in the tune's key (see lib/arrangement.py): upper case
major, lower case minor, b/# before, ° or + after, then 7, maj7, add9, sus4, sus2,
6, 5, and a slash bass ("I/E#"). The numerals are relative to the tonic, so the
same device is written the same way in any key.

## Fitting chords to the tune

- A held note (a beat or more) or a note on a strong beat should be a chord tone,
  or a deliberate colour: the 9th (add9), the 6th, the major 7th over a major
  chord. A note a half step *above* a chord tone, held, is either a sigh
  (appoggiatura - expressive, resolves down) or a clash; the critic flags these
  as notes for you to confirm.
- Quick passing notes between chord tones don't need their own chord.
- One chord per half bar to a bar is the default pace; slower for calm, faster
  approaching a cadence or climax. A chord held 4+ bars is static unless it's a
  pedal or a vamp on purpose.

## The modes' own chords (relative to the tonic)

| mode (tune kind) | its colour | chords to reach for |
|---|---|---|
| ionian (paladin, cleric, fighter) | classic, noble | I IV V vi, ii, V7-I, IV-I (amen) |
| mixolydian (barbarian, ranger, bard) | rugged, epic, folk | I bVII IV v, bVII-I (the epic cadence), I-bVII-IV-I |
| dorian (warlock, druid, monk, rogue) | brooding but hopeful | i IV (major!) bVII v, i-IV (the dorian lift) |
| lydian (wizard, sorcerer) | wonder, magic, floating | I II (major) vii, I-II-I, #iv° avoided |
| aeolian (villains) | tragic, grave | i iv v bVI bVII bIII, V (borrowed) for drama |
| phrygian (villains, dark twins) | menace, dread | i bII bVII biii, bII-i (the Phrygian cadence) |
| harmonic minor | gothic, exotic | i iv V bVI, V7-i, vii°7 |

## Devices by effect

- **The lift (wonder, a hero's top note):** a chromatic mediant under a held
  note - bIII or bVI major where the tonic was expected (I -> bIII, keeping the
  common tone). The film-score "goosebumps" chord. Use once, at the climax.
- **Triumph (endings):** bVI - bVII - I. In Mixolydian the bVII is native; in
  major it's borrowed and sounds heroic.
- **Epic plain:** I - bVII - IV - I, or i - bVI - bVII - i in minor.
- **Yearning:** IV - iv - I (the minor iv borrowed), or vi7 before IV.
- **Dread:** bII (Neapolitan) under a menacing phrase; bII - i at the end. A
  tritone in the tune (the villain generator writes one before its climax) over
  i° or bVI7.
- **Tragic grandeur (a villain's climax):** bVI7 (= augmented sixth) resolving to
  i64 (i/5) then V - one of the strongest dark cadences.
- **Suspense:** a pedal (the bass holding the tonic) under changing chords; sus4
  chords; tremolo.
- **Lament:** i - iv - i, iv6 (iv/b6), the descending bass (i, i/b7, bVI, V) -
  the "lament bass". Slow harmonic rhythm.
- **Warmth (a bond):** add9 and maj7 colours, IV-I, vi-IV-I-V; thirds in the
  inner voices.
- **Darkening (a hero's slide):** borrow from the parallel minor one chord at a
  time - iv for IV, bVI for vi, bVII for V - matching how the tune itself
  borrows dark notes (lib/music_compose.py DARKENING).
- **Vamps for battle:** two chords alternating per bar - i | bII (Phrygian,
  relentless), i | bVI (heroic-dark), i | bVII (driving).
