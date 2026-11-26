# User Scripts

The scripts in `user_scripts/` are for anyone using llamatron, as opposed to
the development tools in `internal_tools/`. Each is plain `sh`, so it needs
nothing installed first, and each runs from the project folder wherever it is
started, passing on any options it is given. Run one from the project folder
as `sh user_scripts/NAME.sh`.

Each script below has an example of running it and a list of its parameters,
in the order they are given: first what the script is given in place, such as
the set to record, and then its options, which may come in any order.

## Installation

### `setup.sh`

Installs what llamatron needs and builds it: it makes `.venv`, a small Python
environment the development tools use, then runs `build.sh`, which offers to
install Rust first. Run it once after cloning the repository.
[Installing](INSTALLING.md) describes the installation.

```
sh setup.sh
```

Parameters: none.

### `build.sh`

Builds llamatron, which `./llamatron.sh` opens, offering to install Rust
first ([Building llamatron](BUILDING_THE_BACKEND.md)). Run it once after cloning the
repository, and again after updating it.

```
sh build.sh
```

Parameters: none.

### `install_fluidsynth.sh`

Installs FluidSynth, a free software synthesizer, and the sounds it plays,
using Homebrew and offering to install Homebrew first. Run it once if you want
to hear the demos with no synthesizer of your own or DAW, or to export WAV files. It
installs nothing without asking, and does nothing that is already done. See
[FluidSynth](FLUIDSYNTH.md).

```
sh user_scripts/install_fluidsynth.sh
```

Parameters: none.

Environment:

- `SOUNDFONT_DIR`: the folder to download the SoundFont into, `~/soundfonts`
  unless given. llamatron looks for the SoundFont in `~/soundfonts`.

### `install_blackhole.sh`

Installs BlackHole 2ch, the loopback audio device the demo recorder records
sound from, using Homebrew and asking before installing. Run it once before
recording your first video. See [Recording](INSTALLING_RECORDING.md), which
also says why the Mac's output is best left on your speakers while you
compose, since the Multi-Output Device made for recording can make the sound
substantially quieter.

```
sh user_scripts/install_blackhole.sh
```

Parameters: none.

## Documentation

### `launch_docs.sh`

Serves the documentation website on this computer and opens it in the
browser, building it first into `output/web_docs/` where it isn't built yet
or a document has changed since it was built. Use it to read the documentation
offline, or to check the website after rebuilding it, before publishing.
`Ctrl+C` stops it.

```
sh user_scripts/launch_docs.sh
sh user_scripts/launch_docs.sh --port 8080 --no-browser
```

Parameters:

- `--port PORT`: the port to serve on, 4173 unless given.
- `--no-browser`: serve without opening the browser.

## Listening to the Demos

### `demos_to_midi.sh`

Exports every example as one General MIDI file in `output/previews/`, playable in any
MIDI player, such as GarageBand. Use it to hear the demos on a computer
without llamatron, or to share them.

```
sh user_scripts/demos_to_midi.sh
sh user_scripts/demos_to_midi.sh examples/learning/02_pachelbel.yml
```

Parameters:

- `SET ...`: the sets to export, every example unless given.

### `demos_to_wavs.sh`

Turns every demo into a WAV file in `output/previews/` in one go: it makes the
previews first, plays each through FluidSynth, which it installs the first
time, and evens out their loudness. Use it to have every demo as audio to play
or share.

```
sh user_scripts/demos_to_wavs.sh
sh user_scripts/demos_to_wavs.sh output/previews/pachelbel.mid
```

Parameters:

- `PREVIEW ...`: the preview MIDI files to turn into WAV files; every demo,
  its preview made afresh, unless given.

### `demos_to_live_sets.sh`

Exports every example as an Ableton Live set beside it, replacing earlier
exports. Use it to open the demos in Live with every scene and clip in place.

```
sh user_scripts/demos_to_live_sets.sh
```

Parameters: none.

## The Corpus

### `fetch_corpus.sh`

Downloads the public domain music corpus, scores and traditional tunes, into
`output/corpus/`, which git ignores, asking before each collection and saying
its size and terms. The song wizard's music theory was measured from it, and
the song wizard is to import songs from it where it is downloaded.
[Credits](CREDITS.md) lists each collection, its link, its terms and its
folder.

```
sh user_scripts/fetch_corpus.sh
sh user_scripts/fetch_corpus.sh joplin thesession
sh user_scripts/fetch_corpus.sh --all
```

Parameters:

- `COLLECTION ...`: the collections to download, by their folders, such as
  `joplin`; asked one by one unless given.
- `--all`: every collection, without asking.

## Recording Videos

Recording is coming back to llamatron, which is now written in Rust; until it
does, these scripts are not part of it.

Every recording script needs the setup that
[Recording](INSTALLING_RECORDING.md), under Installing, describes: BlackHole,
Screen Recording permission for your terminal, and Xcode's command line tools.
[Recording](RECORDING.md) describes the takes themselves.

The visualizer modes a recording can show are `lava_lamp`, `piano_roll`,
`spectrum`, `milkdrop`, `llamas`, `hypercube`, `fireworks`, `warpzone`,
`pipes`, `plasma`, `maze`, `mystify`, `laser_llama`, `mandelbrot`, `life`,
`digital_rain` and `cycle`.

### `record.sh`

Records a video of the tracker playing a set on Arrange. `--sound` says where
the sound comes from: `daw`, the default, plays the set's tracks over MIDI
into your DAW, so the song sounds as your own instruments play it, and
`fluidsynth` plays the set's own FluidSynth instruments, so no DAW is needed,
the simplest recording. With `--interactive` you perform the take: nothing
plays until you press `Space` on Arrange's corner, and stopping there, or
`ESC`, ends it, so that you can launch scenes and edit as the song plays. A
take of a visualizer opens on the title and READY and fills the screen with
the visualizer in its frame, unless `--plain` is given.

```
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --visualizer plasma --go
sh user_scripts/record.sh examples/learning/01_hello_world.yml --sound fluidsynth --interactive
sh user_scripts/record.sh my_set.yml --use-driver "My Synth" --track-assign 1,1,2 --max-seconds 60
sh user_scripts/record.sh my_set.yml --interactive --use-driver "IAC"
```

Parameters:

- `SET`: the set to record, such as `examples/learning/01_hello_world.yml`.
- `--sound SOUND`: `daw`, the default, or `fluidsynth`.
- `--interactive`: perform the take yourself.
- `--visualizer MODE`: record this visualizer mode rather than the clips.
- `--clips`: record the clips on Arrange, without asking.
- `--detail`: record the clips on Arrange with the Details View open, as `D`
  shows it, without asking; it cannot be combined with `--visualizer`.
- `--plain`: with `--visualizer`, show the visualizer over Arrange's clip
  area, the older style, rather than the title, READY and the framed
  visualizer.
- `--no-alternate`: show the visualizer alone in the frame, rather than the
  clips and the visualizer by turns every ten seconds.
- `--batch`: record the take as one of a batch video's, from the window's
  cells alone.
- `--scroll-text WORDS`: the words that cross the screen after the opening
  splash, in place of `DEMO:` and the set's name from its file.
- `--no-scroll`: show no words crossing the screen after the opening splash.
- `--announce`: show each scene's name as the scene starts, such as `SCENE:
  verse`, near the bottom of the screen, in place of the visualizer modes'
  names.
- `--audio-device DEVICE`: the audio input device to record the sound from,
  the first whose name holds this text.
- `--max-seconds SECONDS`: the longest the take may run.
- `--window-id ID`: the id of the window to record, when the terminal program
  cannot be asked.
- `--go`: start the take at once, without waiting for ENTER after the setup is
  explained.

With `--sound daw`:

- `--use-driver PORT`: the MIDI output port to play through, the first whose
  name holds this text.
- `--track-assign-auto`: the first track on channel 1, the second on 2 and so
  on, the default.
- `--track-assign CHANNELS`: a channel for each track in the song's order,
  such as `1,1,2`, with `-` to keep a track's own instrument.

With `--sound fluidsynth`:

- `--fluidsynth-output DEVICE`: the audio output FluidSynth plays to, such as
  a Multi-Output Device that reaches the recorded one too; the recorded device
  unless given.

### `record_all.sh`

Records a video of every example through FluidSynth, shortest first, each
showing the visualizer mode its pairing gives it, and leaves out any example
whose video is already recorded. Use it to make videos of every demo for
uploading.

```
sh user_scripts/record_all.sh
LLAMATRON_BATCH_RECORD_MAX=2 sh user_scripts/record_all.sh
```

Parameters:

- `--audio-device DEVICE`: the audio input device to record the sound from,
  the first whose name holds this text.
- `--fluidsynth-output DEVICE`: the audio output FluidSynth plays to, such as
  a Multi-Output Device that reaches the recorded one too.
- `--window-id ID`: the id of the window to record, when the terminal program
  cannot be asked.
- `--go`: start at once, without waiting for ENTER after the list of takes.
- `--no-scroll`: show no words crossing the screen after each take's title.
- `--announce`: show each scene's name as the scene starts, such as `SCENE:
  verse`, near the bottom of each video.

Environment:

- `LLAMATRON_BATCH_RECORD_MAX`: record only this many examples, the shortest,
  such as `2` to try it first.
