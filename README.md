# noose6

noose6 is the sixth iteration of Noose, a project to enable faster complex compositions and random music through science

against my better judgement Claude is involved in much of this current version.

The project is at an early stage, so expect things to change.

## Setup

From the top folder of the project, create a virtual environment and install the dependencies, [mido](https://github.com/mido/mido), PyYAML and [Textual](https://textual.textualize.io/):

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## The text UI

```
./run_tui.sh
./run_tui.sh examples/retro_chill.yml
```

Every key you can press is shown on the screen you're on. From the main screen, `S` is the song's settings, along with load, save and render. `P` is patterns, `T` is tracks, `C` is chains, `G` is generators, which holds arpeggiators and AutoRatchets for now, `Z` is scales, and `A` is Arrange, where you add scenes and clips. `H` explains the page you're on, Tab goes back, and `Q` quits from the main screen. Nothing is saved or rendered until you ask.

Renders go to `output/<song name>`. Rendering asks before replacing an earlier render, including anything saved over it in Live, so save your own work under another name.

## Song files

Songs are saved as YAML, which is mainly for the program to read, but stays readable so that songs can be compared in version control. They can also be rendered from the command line:

```
.venv/bin/python -m src.cli examples/minimal_techno.yml --to ableton --replace
.venv/bin/python -m src.cli examples/minimal_techno.yml --to cliptree --out output/my_song
```

`examples/` has `minimal_techno.yml`, `retro_chill.yml` and `acid_techno.yml`, which run about three minutes each. Output goes to `output/<song name>` unless you set `--out`. `--replace` removes that song's earlier output first, and `--template` picks the Live set to build from.

To write a Live set for every song in `examples/` at once, use `./run_examples.sh`. It replaces each song's earlier set, including anything saved over it in Live, so save your own work under another name.

## Running the examples

To run all of them in order, use `./run_demo.sh`. To run one at a time, use these commands from the top folder of the project:

| Command | What it does | Output |
|---|---|---|
| `.venv/bin/python -m demo.mary` | Mary Had a Little Lamb, with the melody on one track and the chords on another | `./output/mary` |
| `.venv/bin/python -m demo.mary_repeat` | The same song, with each chord played twice using `Repeater` | `./output/mary2` |
| `.venv/bin/python -m demo.mary_arp` | The same song, with the chords played one note at a time using `Arp` | `./output/mary3` |
| `.venv/bin/python -m demo.mary_degrees` | The melody written as scale degrees, so it can change key | `./output/mary4` |
| `.venv/bin/python -m demo.mary_transpose` | Loads the `demo.mary_arp` files back in and moves them down into B flat minor, so run that demo first | `./output/mary5` |
| `.venv/bin/python -m demo.mary_duration` | The same song, with a choppier melody using `DurationChange` | `./output/mary6` |
| `.venv/bin/python -m demo.mary_stutter` | The same song, with bursts of repeated melody notes using `AutoRatchet` | `./output/mary7` |
| `.venv/bin/python -m demo.mary_mix_up` | The same song, with a shuffled melody using `MixUp` and `MixUp2` | `./output/mary8` |
| `.venv/bin/python -m demo.mary_jazz` | A 22-scene jazz song built from Mary, using every generator, written as an Ableton Live 12 set in Session and Arrangement View, or as MIDI files if you set `USE_ABLETON` to `False` | `./output/mary_jazz` |
| `.venv/bin/python -m demo.gifts_to_sun` | Simple Gifts slowly turns into The House of the Rising Sun, written as an Ableton Live 12 set in Session and Arrangement View | `./output/gifts_to_sun` |
| `.venv/bin/python -m demo.backfill` | A sparse pattern that fills in a little more with each scene, using `Backfill` | `./output/backfill` |
| `.venv/bin/python -m demo.scales` | Every supported scale, with each one in its own scene | `./output/scales` |

The examples have to be run with `-m` as shown, because `python demo/mary.py` can't find the project's code.

Each example writes one MIDI file per clip, named `<scene>-<track>-<clip name>.mid`, or `<scene>-<track>.mid` if the clip has no name, with the numbers zero-padded to three digits, such as `002-001-My_Riff.mid`. Rendering never deletes anything. If a file it needs to write already exists, it prints a warning and stops without writing anything, so delete the output folder before running an example again.

## A short example

```python
from src.note import Note
from src.renderers.clip_tree import ClipTree
from src.scale import Scale, ScaleType
from src.song import Clip, Scene, Song, Track

song = Song(tempo=120)
scene = song.add_scene(Scene('Intro'))
track = song.add_track(Track('Lead'))

# One octave of C major in quarter notes. A note's length is a fraction of a
# whole note, so 0.25 is a quarter note and 0.5 is a half note.
notes = Scale(Note('C', 4, 0.25), ScaleType.MAJOR).octaves(1)
song.set_clip(scene, track, Clip('C Major', notes=notes))

ClipTree('./output/my_song', song).render()
```

This writes `./output/my_song/000-000-C_Major.mid`.

## Tests

```
.venv/bin/python -m unittest discover -s test
```

## License

noose6 is licensed under the GNU General Public License, version 3 or any later version. See [LICENSE](LICENSE) for details.
