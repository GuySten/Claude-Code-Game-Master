# Table music

**Quick start:** `bash tools/gm-music-library.sh fetch` downloads a starter library (25
tracks by Kevin MacLeod, CC BY 4.0, listed in `library.json`) already sorted by mood.

**Automatic music.** The GM tags narration with a mood (`say --mood combat`) and the table
plays a file whose name contains one of that mood's keywords (`battle-drums.mp3` → combat,
`tavern-night.ogg` → tavern; `gm-table.sh music list` shows the keywords), or a built-in
generated sound if none matches. To choose exactly, add `moods.json` here:
`{"combat": ["my-fight.mp3"], "calm": ["harp.ogg"]}`.

**Enemy themes.** `say --theme "Grimaldi"` plays that enemy's theme: a file assigned with
`gm-table.sh music theme "Grimaldi" clown-waltz.mp3`, else a file named after them
(`grimaldi.mp3`; `grimaldi-boss.mp3` for the boss fight), else a tune generated from the name.

Drop audio files here (`.mp3`, `.ogg`, `.m4a`, `.wav`, `.flac`, `.webm`, `.opus`) and the
GM can play them for every player at the online table:

```bash
bash tools/gm-table.sh music list                 # what's available, per mood
bash tools/gm-table.sh music --mood dread         # play whatever fits a mood
bash tools/gm-table.sh music tavern-night.mp3     # play a file for everyone (loops)
bash tools/gm-table.sh music ambient:storm        # built-in generated ambience, no files needed
bash tools/gm-table.sh music https://example.com/battle.ogg --volume 0.4
bash tools/gm-table.sh music stop
```

Files here are shared by every campaign; a campaign can also keep its own in
`world-state/campaigns/<name>/music/`. Name files after their mood (`battle-drums.mp3`,
`elven-forest.ogg`) so the GM can pick the right one at a glance.

Your audio files are not committed to git (see `.gitignore`). Use music you are allowed to
play for your group, for example CC0 or royalty-free tracks from Pixabay Music or the Free
Music Archive.
