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

Makes the Python virtual environment in `.venv` and installs llamatron into
it, then builds the backend, which plays the built-in synths and FluidSynth and sends MIDI, offering to install Rust first
([Building the Backend](BUILDING_THE_BACKEND.md)). Run it once after
cloning the repository, and again if the environment is ever deleted.
[Installing](INSTALLING.md) describes the installation.

```
sh user_scripts/setup.sh
```

Parameters: none.

### `build.sh`

Builds llamatron2, the tracker in Rust, which `./llamatron.sh` opens, with
the backend, offering to install Rust first. Run it once after cloning the
repository, and again after updating it.

```
sh user_scripts/build.sh
```

Parameters: none.

### `install_fluidsynth.sh`

Installs FluidSynth, a free software synthesizer, and the sounds it plays,
using Homebrew and offering to install Homebrew first. Run it once if you want
to hear the demos with no synthesizer or DAW, or to export WAV files. It
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

Serves the documentation website, as committed in `web_docs/`, on this
computer and opens it in the browser. Use it to read the documentation
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

### `play_demo.sh`

Plays a demo's WAV file in the terminal, by its number in the list or its
name, after saying its number and what the demo is: the set, its title, genre
and description. Use it after `demos_to_wavs.sh` to listen without opening the
tracker.

```
sh user_scripts/play_demo.sh
sh user_scripts/play_demo.sh --list
sh user_scripts/play_demo.sh 12
sh user_scripts/play_demo.sh pachelbel
```

Parameters:

- `DEMO`: the demo to play, by its number in the list, by its name, such as
  `pachelbel`, or by the path of a WAV file; a numbered list to pick from
  unless given.
- `--list`: print the numbered list and play nothing.
- `--folder FOLDER`: where the WAV files are, `output/previews/` unless given.

### `demos_to_live_sets.sh`

Exports every example as an Ableton Live set beside it, replacing earlier
exports. Use it to open the demos in Live with every scene and clip in place.

```
sh user_scripts/demos_to_live_sets.sh
```

Parameters: none.

## Demo Information

### `demo_report.sh`

Prints a report of the demos as comma-separated values, for a spreadsheet: one
row per demo with its genre, what it plays, its length, scenes, tracks and the
features it uses, or with `--features` one row per feature and a column per
demo. Use it to find a demo that shows a feature, or to sort and filter the
demos.

```
sh user_scripts/demo_report.sh > demos.csv
sh user_scripts/demo_report.sh --features > features.csv
sh user_scripts/demo_report.sh examples/by_genre/electronic/*.yml
```

Parameters:

- `--features`: one row per feature and a column per demo, rather than one row
  per demo. Given first.
- `SET ...`: the sets to report on, every example unless given.

## Printing a Song

### `export_pdf.sh`

Makes a song of a set into its learning packet, a PDF beside the set named
`<set>_<song>__packet.pdf`: its piano roll, chord changes, chord chart and
chord sequence ([Sheet Music and Learning Packets](EXPORTING_PDF.md)). Use it
to print a song to learn or teach at the piano.

```
sh user_scripts/export_pdf.sh examples/by_genre/ragtime/entertainer.yml
sh user_scripts/export_pdf.sh my_song.yml --song chorus_idea --pages piano_roll,chord_chart --chords-level triads
sh user_scripts/export_pdf.sh my_song.yml --tracks lead,piano --output-dir ~/printouts
sh user_scripts/export_pdf.sh --help
```

Parameters:

- `SET`: the set file. Required.
- `--song NAME`: the song, the set's first if not given.
- `--output-dir FOLDER`: where the PDF goes, the set's folder if not given.
- `--pages PAGES`: the packet's pages, comma-separated, from `piano_roll`,
  `chord_changes`, `chord_chart` and `chord_sequence`; all of them if not given.
- `--tracks TRACKS`: the tracks merged and read as a lead sheet,
  comma-separated; every track with pitched notes if not given.
- `--chords-level LEVEL`: `sevenths` (the default), `triads` or `as_played`.

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
