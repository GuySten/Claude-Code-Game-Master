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

## The rest of the orchestra

| What it plays | Recordings | Creator | Licence |
|---|---|---|---|
| the General MIDI orchestra (every other part, and the stand-in when a download fails) | MuseScore_General SoundFont | MuseScore (S. Christian Collins and contributors) | MIT |
| `men_choir`, `chorus` | Sonatina Symphonic Orchestra chorus (<https://github.com/peastman/sso>) | Mattias Westlund | Creative Commons Sampling Plus 1.0 |
| `choir_oo`, `choir_oh` | Vowel Ensemble | Mihai Sorohan | free to render music with; the recordings not to be passed on |
| `gong`, `bass_drum`, `anvil`, `brake_drum` | VSCO 2 Community Edition, Versilian Community Sample Library | Versilian Studios | CC0 1.0 |
| `guitar`, `guitar_mute` | Standard Guitar | Unreal Instruments | licence free, no credit required |
