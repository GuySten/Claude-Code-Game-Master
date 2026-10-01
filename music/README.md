# Table music

Drop audio files here (`.mp3`, `.ogg`, `.m4a`, `.wav`, `.flac`, `.webm`, `.opus`) and the
GM can play them for every player at the online table:

```bash
bash tools/gm-table.sh music list                 # what's available
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
