# User Scripts

Every script in this folder, what it is for, and how to run it. Run them from
the project's top folder with `sh`, as shown. Each script also says what it
does in its own `# What it does:` line. The scripts for developing llamatron
are in `internal_tools/`.

| To | Run |
| --- | --- |
| Set up llamatron | `setup.sh`, `build.sh`, `install_fluidsynth.sh`, `install_blackhole.sh` |
| Read the documentation | `launch_docs.sh` |
| Hear the demos | `demos_to_wavs.sh` |
| Take the demos elsewhere | `demos_to_midi.sh`, `demos_to_live_sets.sh` |
| Record a video | `record.sh`, `record_all.sh` |

## Setting Up

### `setup.sh`

Installs what llamatron needs, a small Python environment for the development
tools in `.venv`, then builds llamatron with `build.sh`. Run it once, before
anything else.

```
sh setup.sh
```

### `build.sh`

Builds llamatron, which `./llamatron.sh` opens, offering to install Rust
first. Run it once after cloning, and again
after updating.

```
sh build.sh
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

Turns every demo into a WAV file in `output/previews/`, in one go: it makes the
General MIDI previews first, plays each through FluidSynth (installing it the
first time), and evens out the loudness. Run it once, and again after the
demos change.

```
sh user_scripts/demos_to_wavs.sh
sh user_scripts/demos_to_wavs.sh output/previews/entertainer.mid      # only the previews named, not made afresh
```

## Taking the Demos Elsewhere

### `demos_to_midi.sh`

Exports every demo as one General MIDI file in `output/previews/`, for any MIDI
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

## Recording Videos

Recording is coming back to llamatron, which is now written in Rust; until it
does, these scripts are not part of it.

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
