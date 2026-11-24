# User Scripts

Every script in this folder, what it is for, and how to run it. Run them from
the project's top folder with `sh`, as shown. Each script also says what it
does in its own `# What it does:` line. The scripts for developing llamatron
are in `internal_tools/`.

| To | Run |
| --- | --- |
| Set up llamatron | `setup.sh`, `install_fluidsynth.sh`, `install_blackhole.sh` |
| Read the documentation | `launch_docs.sh` |
| Hear the demos | `demos_to_wavs.sh`, then `play_demo.sh` |
| Take the demos elsewhere | `demos_to_midi.sh`, `demos_to_live_sets.sh` |
| See what the demos hold | `demo_report.sh` |
| Print a song to learn at the piano | `export_pdf.sh` |
| Import many MIDI files at once | `batch_importer.sh` |
| Record a video | `record.sh`, `record_all.sh` |

## Setting Up

### `setup.sh`

Makes the virtual environment `.venv` and installs llamatron into it. Run it
once, before anything else.

```
sh user_scripts/setup.sh
```

### `install_fluidsynth.sh`

Installs FluidSynth and the free GeneralUser GS SoundFont on a Mac, offering
Homebrew first, so that every example plays with no synthesizer of your own.
It installs nothing without a yes.

```
sh user_scripts/install_fluidsynth.sh
```

### `install_blackhole.sh`

Installs BlackHole 2ch, the loopback audio device the recorder records the
sound from. Needed only for recording videos.

```
sh user_scripts/install_blackhole.sh
```

## Documentation

### `launch_docs.sh`

Serves the documentation website, already built, on this computer and opens it
in the browser. Ctrl+C stops it.

```
sh user_scripts/launch_docs.sh
sh user_scripts/launch_docs.sh --port 5000 --no-browser
```

## Hearing the Demos

### `demos_to_wavs.sh`

Turns every demo into a WAV file in `previews/`, in one go: it makes the
General MIDI previews first, plays each through FluidSynth (installing it the
first time), and evens out the loudness. Run it once, and again after the
demos change.

```
sh user_scripts/demos_to_wavs.sh
sh user_scripts/demos_to_wavs.sh previews/entertainer.mid      # only the previews named, not made afresh
```

### `play_demo.sh`

Plays a demo's WAV file in the terminal. Before it plays, it prints the demo's
number in the list and what the demo is: the set it came from, its title,
genre and description. Ctrl+C stops it.

```
sh user_scripts/play_demo.sh --list            # the numbered list, playing nothing
sh user_scripts/play_demo.sh 12                # the twelfth of the list
sh user_scripts/play_demo.sh entertainer       # by name
sh user_scripts/play_demo.sh                   # the list, then type a number
```

## Taking the Demos Elsewhere

### `demos_to_midi.sh`

Exports every demo as one General MIDI file in `previews/`, for any MIDI
player. `demos_to_wavs.sh` runs it for you.

```
sh user_scripts/demos_to_midi.sh
sh user_scripts/demos_to_midi.sh examples/by_genre/ragtime/entertainer.yml
```

### `demos_to_live_sets.sh`

Exports every demo as an Ableton Live set beside it, replacing earlier
exports.

```
sh user_scripts/demos_to_live_sets.sh
```

## What the Demos Hold

### `demo_report.sh`

Prints a report of the demos as comma-separated values, for a spreadsheet: one
row a demo, with its genre, what it plays, its length, scenes, tracks and
features; or with `--features`, given first, one row a feature and a column a
demo.

```
sh user_scripts/demo_report.sh > demos.csv
sh user_scripts/demo_report.sh --features > features.csv
sh user_scripts/demo_report.sh examples/by_genre/rock/*.yml
```

## Printing a Song

### `export_pdf.sh`

Makes a song of a set into its learning packet, a PDF beside the set: its
piano roll, chord changes, chord chart and chord sequence. `--song`,
`--output-dir`, `--pages`, `--tracks` and `--chords-level` choose
what goes in; `--help` lists them.

```
sh user_scripts/export_pdf.sh examples/by_genre/ragtime/entertainer.yml
sh user_scripts/export_pdf.sh my_song.yml --pages piano_roll,chord_chart --chords-level triads
```

## Importing MIDI Files

### `batch_importer.sh`

Imports every MIDI file under a folder, at any depth, as the Import Wizard
cuts it, each into a set file of its own in another folder, or every file a
song of one set. The output folder stays flat: a file's set is named after its
path under the input folder, its folders joined by `__`, and its song after
the file. A file that can't be imported is named and passed over, and the
report at the end says how long the imports took: the shortest, the longest
and the average. Use it to bring a whole collection of MIDI files into
llamatron at once.

```
sh user_scripts/batch_importer.sh --input-dir ~/midi --output-dir ~/llamatron_sets
sh user_scripts/batch_importer.sh --input-dir ~/midi --output-dir ~/llamatron_sets --bars-per-pattern 4 --quantize 1/16
sh user_scripts/batch_importer.sh --help
```

Parameters:

- `--input-dir FOLDER`: the folder of `.mid` and `.midi` files. Required.
- `--output-dir FOLDER`: where the set files go, made if missing. Required.
- `--bars-per-pattern N`: the longest a pattern may be, in bars, 8 unless
  given.
- `--quantize GRID`: the finest grid a file played by hand is put on, from
  `1/4` to `1/64`, `1/64` unless given.
- `--format direct`: one song for each file, playing it as the file does, the
  only format so far.
- `--multiple-songs-per-set`: every file a song of one set, named after the
  input folder.

## Recording Videos

These need the setup `docs/INSTALLING_RECORDING.md` describes;
`docs/RECORDING.md` describes the takes.

### `record.sh`

Records a video of the tracker playing a set on Arrange. `--sound daw`, the
default, takes the sound from your DAW over MIDI; `--sound fluidsynth` uses
the set's own instruments and needs no DAW. With `--interactive` nothing plays
until you press Space on Arrange's corner, and stopping there, or ESC, ends
the take.

```
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --visualizer plasma --go
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --interactive
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --announce   # each scene named as it starts
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --detail     # the clips with Arrange's details view open
sh user_scripts/record.sh my_set.yml --use-driver "My Synth" --track-assign 1,1,2
```

### `record_all.sh`

Records a video of every demo through FluidSynth, shortest first, each with
its visualizer mode, leaving out any already recorded.

```
sh user_scripts/record_all.sh
LLAMATRON_BATCH_RECORD_MAX=2 sh user_scripts/record_all.sh     # only the two shortest, to try it
```
