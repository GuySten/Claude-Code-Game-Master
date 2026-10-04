# The orchestra: what each part can do

All figures are measured from the sound set (MuseScore_General) the table plays.
Pitches: C4 = 60 (middle C).

## Parts

| part | range | speaks in | good for |
|---|---|---|---|
| violins | G3-E7 | 0.50 s (slow) | soaring tune an octave up; lush long lines. Quick notes need a doubling |
| violins2 | G3-C7 | 0.26 s | a second line: countermelody, ostinato (double quick ones) |
| strings | C2-C7 | 0.48 s (slow) | sustained chords (pads) under everything |
| tremolo | C2-C7 | 0.16 s | tension, suspense, intros, under a climax |
| pizzicato | E1-C7 | instant | ticking, walking bass, light rhythm, clockwork |
| cellos | C2-E5 | 0.24 s | warm tune an octave below; sustained bass. Too slow for a quick ostinato alone |
| basses | E1-C4 | quick | the bottom: hold the bass, or a low pulse |
| flutes | C4-C7 | instant | doubling the tune up an octave (sparkle), quick notes |
| piccolo | D5-C8 | instant | a glint at the very top of a tutti |
| oboe | A#3-G6 | 0.12 s | plaintive solo, a memory, a lament |
| english_horn | E3-A5 | 0.42 s | tired, elegant, melancholy solo (double its quick notes) |
| clarinets | D3-G6 | instant | warm, quick doubling of a slow voice; mysterious low register |
| bassoons | A#1-C5 | instant | dark tune in the low octave; the bite on a cello ostinato |
| horns | F2-F5 | 0.06 s | noble/heroic tune (the hero's instrument), warm pads, low fifths |
| trumpets | F#3-A#5 | instant | triumph, fanfare, the climax, the final statement |
| trombones | E2-C5 | instant | menace, weight, chords under a climax, the villain's tune low |
| tuba | E1-A#3 | instant | the lowest brass bottom |
| brass | C2-C6 | 0.08 s | one big blended brass chord: stabs in battle music |
| choir | E2-A5 | blooms in 1.2 s | fate, the sacred, the epic: held chords, the tune's long notes |
| harp | C1-G7 | instant | arpeggios, magic, tenderness |
| celesta | C4-C8 | instant | wonder, childhood, fairy-tale magic |
| glockenspiel | G5-C8 | instant | sparkle on top |
| bells | C4-F5 | instant | tolling: a clock, a church, a doom |
| organ | C1-C7 | 0.10 s | grandeur, the sacred, the aristocratic villain |
| timpani | D2-G3 | instant | strong beats on root/fifth; rolls into big moments; the final stroke |
| taiko | - | instant | war drums: barbarians, armies, savage battles |
| toms | - | instant | driving fills in a fight |
| reverse_cymbal | - | swell | a whoosh into a hit |
| kit (orchestral) | - | instant | bd (bass drum), snare (marches, builds), crash/cymbal (the climax), gong, triangle |

## Rules that come from those numbers

- **Slow speakers + quick notes = smear.** A note shorter than ~1.5x the
  "speaks in" time sounds at under half its level. Give such passages a quick
  doubling at the same moment and pitch (the critic recognizes it), or write held
  notes. Typical pairs: violins+flutes (an octave up), violins+clarinets,
  cellos+bassoons (an ostinato), english_horn+clarinets (quietly, "mix" -8).
- **The choir needs time and space.** Notes of a beat or more (ideally a bar),
  held chords, the tune's long notes. In the vamp of a battle it holds an "AAAH"
  per bar while brass stabs carry the rhythm. Two octaves (low voices around
  A#2-A#3, high around F4-F5) is the epic sound.
- **Same part, same pitch, overlapping = cut.** Two notes of one pitch on one
  part cut each other off. Put a held note and a moving line on different parts
  (or octaves).
- **Bass registers.** Basses hold the bass around E1-D#2; cellos an octave up
  (C2-B2) for warmth or the pulse; tuba under brass from the build onward.
- **Timpani** sit D2-G3: tonic and dominant mostly ("note": "root" picks the
  chord's root in range). Rolls ("rolls") lead into the climax and under the last
  chord, then a final stroke ("hits").
- **Register spacing.** Chord pads between about G2 and A#4 under a tune in the
  4th-5th octave; keep pads below the tune when the tune is soft (a solo), and
  don't stack every part in the same octave.

## Balance

Every part is evened out already (the same velocity = the same loudness), plus a
small orchestral balance (brass and choir a little forward, pads back). The
tune's notes are their own layer, `"lead"` dB over the rest (default 4). Order of
fixes when something is too quiet or loud:

1. Write it: fewer or softer accompanying parts in that section (a velocity
   offset of -15 to -25 for pads), the tune in a stronger carrier or octave.
2. `"gain"` on that melody entry (the critic suggests the number).
3. `"mix": {"part": dB}` for the whole piece - last, because it changes the part
   everywhere.
