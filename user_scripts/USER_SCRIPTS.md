# User Scripts

Every script in this folder, what it is for, and how to run it. Run them from the project's top folder with `sh`, as shown.
Each script also says what it does in its own `# What it does:` line. The scripts for developing llamatron are in
`internal_tools/`.

| To | Run |
| --- | --- |
| Set up llamatron | `setup.sh`, `install_fluidsynth.sh`, `install_blackhole.sh` |
| Read the documentation | `launch_docs.sh` |
| Hear the demos | `demos_to_wavs.sh`, then `play_demo.sh` |
| Take the demos elsewhere | `demos_to_midi.sh`, `demos_to_live_sets.sh` |
| See what the demos hold | `demo_report.sh` |
| Record a video | `record.sh`, `record_all.sh` |
| Ask the genre library | `describe_style.sh` |

## Setting Up

### `setup.sh`

Makes the virtual environment `.venv` and installs llamatron into it. Run it once, before anything else.

```
sh user_scripts/setup.sh
```

### `install_fluidsynth.sh`

Installs FluidSynth and the free GeneralUser GS SoundFont on a Mac, offering Homebrew first, so that every example plays with
no synthesizer of your own. It installs nothing without a yes.

```
sh user_scripts/install_fluidsynth.sh
```

### `install_blackhole.sh`

Installs BlackHole 2ch, the loopback audio device the recorder records the sound from. Needed only for recording videos.

```
sh user_scripts/install_blackhole.sh
```

## Documentation

### `launch_docs.sh`

Serves the documentation website, already built, on this computer and opens it in the browser. Ctrl+C stops it.

```
sh user_scripts/launch_docs.sh
sh user_scripts/launch_docs.sh --port 5000 --no-browser
```

## Hearing the Demos

### `demos_to_wavs.sh`

Turns every demo into a WAV file in `previews/`, in one go: it makes the General MIDI previews first, plays each through
FluidSynth (installing it the first time), and evens out the loudness. Run it once, and again after the demos change.

```
sh user_scripts/demos_to_wavs.sh
sh user_scripts/demos_to_wavs.sh previews/entertainer.mid      # only the previews named, not made afresh
```

### `play_demo.sh`

Plays a demo's WAV file in the terminal. Before it plays, it prints the demo's number in the list and what the demo is: the
set it came from, its title, genre and description. Ctrl+C stops it.

```
sh user_scripts/play_demo.sh --list            # the numbered list, playing nothing
sh user_scripts/play_demo.sh 12                # the twelfth of the list
sh user_scripts/play_demo.sh entertainer       # by name
sh user_scripts/play_demo.sh                   # the list, then type a number
```

## Taking the Demos Elsewhere

### `demos_to_midi.sh`

Exports every demo as one General MIDI file in `previews/`, for any MIDI player. `demos_to_wavs.sh` runs it for you.

```
sh user_scripts/demos_to_midi.sh
sh user_scripts/demos_to_midi.sh examples/by_genre/ragtime/entertainer.yml
```

### `demos_to_live_sets.sh`

Exports every demo as an Ableton Live set beside it, replacing earlier exports.

```
sh user_scripts/demos_to_live_sets.sh
```

## What the Demos Hold

### `demo_report.sh`

Prints a report of the demos as comma-separated values, for a spreadsheet: one row a demo, with its genre, what it plays, its
length, scenes, tracks and features; or with `--features`, given first, one row a feature and a column a demo.

```
sh user_scripts/demo_report.sh > demos.csv
sh user_scripts/demo_report.sh --features > features.csv
sh user_scripts/demo_report.sh examples/by_genre/rock/*.yml
```

## Recording Videos

These need the setup `docs/INSTALLING_RECORDING.md` describes; `docs/RECORDING.md` describes the takes.

### `record.sh`

Records a video of the tracker playing a set on Arrange. `--sound daw`, the default, takes the sound from your DAW over MIDI;
`--sound fluidsynth` uses the set's own instruments and needs no DAW. With `--interactive` nothing plays until you press Space
on Arrange's corner, and stopping there, or Esc, ends the take.

```
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --visualizer plasma --go
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --interactive
sh user_scripts/record.sh my_set.yml --use-driver "My Synth" --track-assign 1,1,2
```

### `record_all.sh`

Records a video of every demo through FluidSynth, shortest first, each with its visualizer mode, leaving out any already
recorded.

```
sh user_scripts/record_all.sh
LLAMATRON_BATCH_RECORD_MAX=2 sh user_scripts/record_all.sh     # only the two shortest, to try it
```

## Asking the Genre Library

These read the genre library as it ships. They need no corpus and no training run.

### `describe_style.sh`

Prints the style of a song as JSON: its tempo, meter, feel, bass, harmony, melody's shape, texture, energy and the rest, each
a trait with its fields. Everything in it is measured from the song's notes by the Python code; no genre, artist or composer is
consulted, and no note of the song is written, so it says what kind of music the song is, not which music. Unstable: the fields change as the analyzer does.

```
sh user_scripts/describe_style.sh some_song.mid
sh user_scripts/describe_style.sh my_set.yml --song "second song" > style.json
```
