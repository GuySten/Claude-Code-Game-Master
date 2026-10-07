# Credits: the recordings the orchestra plays

The engine (`lib/music/orchestra.py`) plays recordings of real instruments. None of them are
kept in this repository: each is downloaded once, from a fixed URL (pinned to a commit where
the host allows it), into `~/.cache/gm-orchestra/` and built there into a SoundFont. Building
changes them (a part of a recording kept, one microphone of two, an envelope or a loop added,
levels set); the changed recordings stay on the machine that built them. The music rendered
from them is credited here as their licences ask.

## Short string notes, brass sections, solo horn

Gathered, trimmed and looped by **Virtual Playing Orchestra 3** (Paul Battersby,
<https://virtualplaying.com/virtual-playing-orchestra/>), whose SFZ files describe how they
play; fetched from the mirror
<https://github.com/studiorack/virtual-playing-orchestra> at commit
`9ab3329bb136834d33dcabb734b76053d5606b83`. VPO's terms: free to use for music, and to copy,
modify and pass on with credit to the creators of its content (this file).

| What it plays | Recordings | Creator | Licence |
|---|---|---|---|
| `violins` short notes (staccato 1st violins), `basses` short notes (staccato basses) | Sonatina Symphonic Orchestra, <http://sso.mattiaswestlund.net/> | Mattias Westlund | [Creative Commons Sampling Plus 1.0](https://creativecommons.org/licenses/sampling+/1.0/) |
| `violins2` short notes (spiccato violas), `cellos` short notes (spiccato cellos) | VSCO 2 Community Edition, <https://github.com/sgossner/VSCO-2-CE> | Versilian Studios (Sam Gossner) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) |
| `horns` (the horn section) | "Brass 2011-11-07 Horns Sustain", <http://mattiaswestlund.net/samples/> | Mattias Westlund | [CC BY-SA 3.0 Unported](https://creativecommons.org/licenses/by-sa/3.0/) |
| `trombones` (the trombone section) | No Budget Orchestra, <https://github.com/ssj71/No-Budget-Orchestra> | ssj71 (Spencer Jackson) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `horn_solo` (a solo F horn) | VSCO 2 Community Edition (its SFZ branch, commit `6dd651d55dde97fd4028699be9d4481f26917891`) | Versilian Studios (Sam Gossner) | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) |

Changes made when they are built (`fetch_strings_short`, `fetch_brass`, `fetch_horn_solo`):
each recording played as its SFZ describes it (volume, pan, envelope) and baked into a
SoundFont; the brass sections and the solo horn reduced to one microphone; the solo horn's
recordings given crossfaded loops; levels set to match the rest of the orchestra.

## The solo voice

`solo_voice` sings from three recordings of **VocalSet: A Singing Voice Dataset** (Julia
Wilkins, Prem Seetharaman, Alison Wahl, Bryan Pardo; ISMIR 2018), version 1.1, Zenodo,
[doi:10.5281/zenodo.1442513](https://doi.org/10.5281/zenodo.1442513): its singer "f4" (a
soprano) holding long tones on "ah" - forte, pianissimo, messa di voce
(`FULL/female4/long_tones/*/f4_long_{forte,pp,messa}_a.wav`). Licence:
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

Changes made when she sings (`fetch_voice`, `_voice_stem`): the recordings' held notes found,
analysed (pitch, pitch marks) and moved to the score's notes by pitch-synchronous overlap-add,
held notes drawn back and forth over their recordings, notes joined legato, levels set, a
small room added; the recordings themselves are kept unchanged on the machine that fetched them.

## The rest of the orchestra

| What it plays | Recordings | Creator | Licence |
|---|---|---|---|
| the General MIDI orchestra (every other part, and the stand-in when a download fails) | MuseScore_General SoundFont | MuseScore (S. Christian Collins and contributors) | MIT |
| `men_choir`, `chorus` | Sonatina Symphonic Orchestra chorus (<https://github.com/peastman/sso>) | Mattias Westlund | Creative Commons Sampling Plus 1.0 |
| `choir_oo`, `choir_oh` | Vowel Ensemble | Mihai Sorohan | free to render music with; the recordings not to be passed on |
| `gong`, `bass_drum`, `anvil`, `brake_drum` | VSCO 2 Community Edition, Versilian Community Sample Library | Versilian Studios | CC0 1.0 |
| `guitar`, `guitar_mute` | Standard Guitar | Unreal Instruments | licence free, no credit required |

## The rock organ

`rock_organ` is played by **setBfree** (Fredrik Kilander, Robin Gareus and Will Panther,
<https://github.com/pantherb/setBfree>): a model of a Hammond B3 tonewheel organ, its preamp
and its Leslie rotating speaker - code, not recordings. Version 0.8.12, its source fetched
from Ubuntu's copy of the release,
<https://archive.ubuntu.com/ubuntu/pool/universe/s/setbfree/setbfree_0.8.12+ds.orig.tar.xz>
(SHA-256 `7a414b7ce8654fcc935c52465cac9a68d102811acb39d552c44daf5cbec4e087`, the checksum
Ubuntu's `setbfree_0.8.12+ds-2build2.dsc` gives). Licence: the
[GNU General Public License, version 2 or later](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).

`fetch_setbfree` compiles setBfree's tone generator, overdrive and rotating speaker (its
reverb, JACK and LV2 parts left out) with `lib/music/setbfree_render.c` - a small program that
plays the score's notes, bass pedals and speaker switches through them offline - into one
program in `~/.cache/gm-orchestra/`, which the engine runs as a separate process. That file is licensed
under the GPL, version 2 or later, like the code it is built with (not under this
repository's licence); nothing else here links to setBfree. The synthesized organ in
`orchestra.py` (`_organ_synth_stem`) is this repository's own, and plays when setBfree
can't be built.
