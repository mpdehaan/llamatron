# Exporting

Besides playing a song in real time, llamatron writes a song out: as a Live set to finish in a DAW, as MIDI
files for any other DAW or player, or as a WAV file to listen to anywhere. This page covers every kind of
export, where the files go, and exporting from the command line; [Opening and Saving](GETTING_STARTED.md#opening-and-saving)
covers saving the set itself.

## Tracker Export

`Ctrl+X`, on any page, exports the current song and asks which kind first. A set that hasn't been saved
yet is saved first, since an export is named after the set's file and written beside it. When the export
is written, the status line says where it went.

Every export is named `<set>_<song>`, so `songs/foo.yml` with a song called `bar` exports as:

| Kind | File | What it's for |
| --- | --- | --- |
| Ableton Live set | `songs/foo_bar.als` | The main one: each track a MIDI track, its clips in Session View and the scenes laid end to end in Arrangement View, ready for instruments, effects and mixing. |
| MIDI (Stems) | `songs/foo_bar_stem_001-lead.mid` and so on | A file per track, each the full length of the song with the tempo changes, for hardware and samplers that take one file at a time. |
| MIDI (Single File) | `songs/foo_bar.mid` | One file with a track per track and the tempo changes, which most DAWs import as aligned tracks in one drop. |
| MIDI (Clips) | `songs/foo_bar_clip_s_002-chorus-t_001-lead.mid` and so on | A file per clip, named by scene and track, to drag into a project one by one. |
| MIDI (General MIDI) | `songs/foo_bar_gm.mid` | One file for any General MIDI player, GarageBand or a phone: drums on channel 10, every other track on a channel of its own, each with its instrument's GM sound. |
| WAV (FluidSynth) | `songs/foo_bar.wav` | The song as audio, for anyone with no DAW: the tracks whose instrument's Device is `*FluidSynth`, played by FluidSynth faster than real time and normalized to a peak 1 dB below full scale. Choosing it says first that only those tracks are in it, and it needs FluidSynth installed. |

## Export Contents

An export plays the song as written, every scene once through from the top, as Live's Arrangement View
lays it out, with every generator, groove, register and random choice played into the notes. A song with
no seed exports a new take each time; set a seed on the Song page to export the same take every time.

Some things belong to real-time playback alone and no export reads them: instruments' devices, a clip's
follow action and a scene's Launch together, the Live response, and anything you did by hand while the
song played. Muted tracks are left out of the MIDI and WAV exports, and in the Live set they are switched
off. The MIDI files lay the scenes end to end as Live's Arrangement View does, so a track that plays
nothing in the first scenes starts with silence and every file lines up. Every MIDI file carries the song's time signature, and so does the Live set, so a DAW draws its bar
lines on the song's beats.

## File Locations

Exports sit beside the set's file, so a set and its exports stay together wherever you run llamatron
from, and every file of a song starts with `<set>_<song>`, so exporting one song never touches another's.

Writing a Live set over an earlier one asks first, once in a session for each set, because replacing it
loses anything you saved over that set in Live; to keep work you've done in Live, save it there under
another name. The MIDI kinds and the WAV just write over their earlier files. The exports of the sets in
`examples/` are ignored by git.

In Live, each llamatron track is a MIDI track with no instrument, so drop one onto each track to hear
it. Scenes keep their names, and each clip is named after the pattern it plays. The project was made with
Ableton Live 12.3, and later versions should open it.

## Command-Line Export

`--to` exports a set without opening the tracker, writing every song in it beside the set's file, the
same as `Ctrl+X`. On its own it writes Live sets, and it can name another kind: `ableton`, `midi`
(MIDI (Single File)), `stems`, `cliptree` (MIDI (Clips)), `gm` (MIDI (General MIDI)) or `wav`
(WAV (FluidSynth)). Put it after the set's name:

```
llamatron examples/by_genre/electronic/minimal_techno.yml --to
llamatron examples/by_genre/electronic/minimal_techno.yml --to midi
llamatron examples/by_genre/electronic/minimal_techno.yml --to wav --out exports
llamatron examples/by_genre/electronic/minimal_techno.yml --to ableton --replace
llamatron examples/learning/04_scale.yml --to --song "Scale demo"
```

| Option | What it does |
| --- | --- |
| `--song` | Exports only the song with that name. |
| `--out` | Writes into that folder, with the same file names, in place of the set's own folder. |
| `--replace` | Removes each song's earlier export first, so you can export again and listen. |
| `--template` | Builds the Live set from another Live set. |
| `--seed` | Exports with that seed in place of the song's, so an export can be repeated exactly. |
| `--force` | Exports a set file that holds values llamatron can't use, each changed the way the tracker's dialog would change it, listing what it changed. Without it such a file isn't exported. The file itself is never changed. |

These only work with `--to`.

## Batch Export Scripts

| Script | What it does |
| --- | --- |
| `sh user_scripts/demos_to_live_sets.sh` | Every example as a Live set beside it, replacing earlier exports. |
| `sh user_scripts/demos_to_midi.sh` | Every example as one General MIDI file in `previews/`, for any MIDI player. |
| `sh user_scripts/demos_to_wavs.sh` | Those previews as WAV files through FluidSynth, installing it the first time. |
| `sh user_scripts/play_demo.sh` | Pick one of those WAV files from a list and hear it. |
