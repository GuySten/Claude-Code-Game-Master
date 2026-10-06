---
name: orchestrate
description: Compose and orchestrate the game's music as written notes for the sampled orchestra (JSON scores played by lib/arrangement.py) - a character's theme or anthem at any point of their story (seed, theme, heroic, legendary, wounded, bonded, darkened), a dark twin, a villain's theme, a boss-fight loop, or any piece the table needs. Use it whenever music is to be written, arranged, revised or judged - including when the host says a piece sounds wrong ("I can't hear the choir", "too quiet", "boring", "doesn't sound like him"), asks for a new version of someone's music, or a story moment calls for a theme to change - even if they don't say "arrangement" or "orchestra".
---

# Orchestrate

You write the music the way a film composer does: the character's tune comes from
the leitmotif generator (it is theirs, always exact), and you decide everything
around it - who plays it when, the harmony under it, the countermelodies, the
build, the climax, the ending. The orchestra (real instrument recordings) plays
what you write.

**You can't hear.** Everything you know about how a piece sounds comes from two
places: the score critic (`arrangement.py check`, which renders the piece and
measures what a listener would notice) and the host's ears. Your past mistakes
were all things a listener heard at once - a choir 20 dB too quiet to exist, a
tune buried under its own accompaniment, violins too slow to speak quick notes.
So the loop below is not optional ceremony; it's how you hear.

## The loop

0. **Important characters: write the tune yourself** (the host clearly preferred
   hand-written tunes to the generator's): `references/tunes.md`. Write three
   candidates from the character's **distinctive concepts** (the brief's, below:
   the mode, the hook's interval and rhythm come from who they are), different in
   hook and rhythm, each passing the memorability floor; let the **host judge** pick
   (below). Who counts:
   - **the party** - the host's own characters: a close call in the finals goes to
     the host;
   - **important NPCs** - bosses, main villains, main allies, unique summons: the
     same workflow, decided automatically (`host_judge.py finals decide --no-host`);
     the host isn't asked to choose (host: "a workflow that is similar to the players
     but without me picking from two").
   Do it when they're introduced, in prep - never compose a boss's fight before its
   tune exists. A boss's finals are arranged as **their theme** - the piece the table
   hears when they appear, before any fight - so the players know the tune before the
   fight varies it (stage 1 is where they learn a boss; a leitmotif is recognised in
   a reprise, not a variation); the stages are built from the winner after. A boss's fight states that tune whole in every stage (`"statements"`):
   the host couldn't tell whether the Ashen Saint's second stage had the first
   stage's tune, because her improvised one (scored 4.0-5.0) was unmemorable.
   Everyone else gets the generator's (gen 2).

**Then compose by `references/composing.md`** - the rulebook: the host's verdicts, what the
research adds, a recipe for each kind of piece, the format's shortcuts, and the loop
(plan, write, `arrangement.py make`, report). Read it whole; nothing else is required
reading for a composer. Run the scripts with a Python that has numpy, soundfile and
tinysoundfont (the host's `.compose-venv`, set up by `gm-music-compose.sh setup --orchestra`).
Listen-tool note: `lib/music_rate.py` (Audiobox) hears the sound, not the music - use it to
compare two mixes of one piece, never to choose a tune or judge the music.

## The host judge: the host's taste, so they only listen when it matters

The host can't audition everything, and can't tell a 9 from a 10 - nobody can;
people judge pairs, not scores. `lib/host_judge.py` approximates their taste with
the judges that matched their verdicts (the audio models, Audiobox and SongEval,
did no better than a coin flip on our music):

- **Tunes are chosen by their finished music, not alone.** The host put it
  plainly: which tune they like bare isn't which makes the best piece once the
  orchestra is added (in the 2x2, the simpler tune richly set matched the bold
  one plainly set). So bare-tune judging only narrows the field:
  `host_judge.py tunes prepare a.json b.json c.json --out DIR` drops red-flagged
  candidates and writes blind pairs; a **fresh agent** (it must not know which is
  which, or that one is yours) reads `DIR/README.txt` and writes
  `DIR/verdicts.json`; `host_judge.py tunes decide DIR` names two **finalists** -
  candidates that also hold up as a leitmotif in every form (seed, heroic,
  legendary, darkened, the villain's: `versatility`).
- **Then the finals:** arrange each finalist for the same role with the same care,
  budget-matched (a bold tune plainly set, a simple tune richly set), check both
  clean, and `host_judge.py finals prepare a-score.json b-score.json --out DIR`;
  a fresh agent reads the scores blind; `host_judge.py finals decide DIR` picks
  the piece - and with it the tune.
- **Arrangements:** the critic clean, and the surprise budget balanced.
- **Close calls only go to the host:** when `finals decide` says `ask_host`, send
  the two finished pieces (`host_judge.py clips a-score.json b-score.json --out
  DIR`) and ask which they prefer - "can't tell" is a fine answer. Never ask the
  host to choose between bare tunes for the final pick.
- **Record every preference the host states** - an A/B answer, or "this one's
  better" about anything - with `host_judge.py record WINNER.json LOSER.json
  [--tie] [--note "their words"]`. Their verdicts live in the campaigns folder
  (`taste/verdicts.json`); `host_judge.py validate` re-checks the automatic
  judges against all of them - run it after changing a rule, and if agreement
  drops, the rule is wrong, not the host.

## The brief: the GM writes it, by `references/briefs.md`

Most of the host's verdicts were lost in the brief, not the score: each line a faithful
translation of a word, and nobody checking what the whole would make the table feel. So every
brief follows `references/briefs.md`: read the host's verdicts on this kind of piece, write the
**Job** (what the table must feel by the last bar, and why music plays here), fill the template
with a reason on every instruction, read it as the table will hear it, have a **fresh agent
review it** (`references/brief-review.md`) before any composing, and store it in the campaign
(`music/briefs/`). Its principles (P1-P8) are the only brief rules; they replace the ones that
used to live here and in `concepts.md`.

The GM writes every brief, not a separate translator: the GM knows the character - the
scenes, the players, what the story made of them - and a translator working from a few
files squeezed them into concept labels and lost the picture (the host, Kestrel's theme in
three blind rounds: both translator briefs lost, the second "clearly"; the GM's came "closer").
The means come from the references: `references/concepts.md` translates what a subject stands
for (holiness, cunning, the sea, a farewell...) into music - find the entries in
`references/concepts-index.md` and read only those, with its section 1 (how concepts combine) -
and `references/devices.md` gives character devices. A lexicon entry has several readings;
the Job picks one (P7).

A verdict on character goes into `table-feedback.md`, one line under its kind in `briefs.md`,
and, if it shows an entry is wrong, into that entry - never as a patch for one character.

## Characters: a portrait in devices

A character's music is a portrait, not a mood: read who they are in the campaign
(npcs.json, the world bible, their deeds) and build their piece from the **character
devices** in `references/devices.md` - the façade, the madness, the lament, the power,
the corruption... - each with how to write it, the convention and evidence behind it,
and the host's verdicts; its trait table maps a description to devices. Some are code
(`lib/devices.py`: `madness()`). Ask the host for a brief in their own words when you
can (their reference pieces taught more than any measurement), and for one listen at
the end: no model judges a piece's character for them (`table-feedback.md`).

## Pieces and versions

Every kind of piece has its recipe in `references/composing.md`; a named boss's fight in
stages - the stage plan, transitions, endings, playing them at the table - in
`references/boss-music.md`. Full scores from play live in the campaign's
`music/arrangements/` folder, their briefs (with the review and the host's verdict) in
`music/briefs/`.

## When the host says something sounds wrong

Believe them over any measurement, then find out why with the critic (render the part they
mention alone against the rest). Fix the cause, not just that piece: record the verdict in
`references/table-feedback.md`, and change `references/composing.md` - one rule, stated once,
with its source - and the critic where it can check it. Never add a patch rule beside an old
one: replace the old one.
