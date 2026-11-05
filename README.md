# llamatron

llamatron is the sixth iteration of a project to enable faster complex compositions and random music through science

against my better judgement Claude is involved in much of this current version.

The project is at an early stage, so expect things to change.

## Setup

From the top folder of the project, create a virtual environment and install llamatron, which also installs [mido](https://github.com/mido/mido), PyYAML and [Textual](https://textual.textualize.io/):

```
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

This adds the `llamatron` command to `.venv/bin`, along with the Live set it builds from, so it works from any folder. `-e` makes it use the code in this folder, so changes take effect without installing again.

## The text UI

```
llamatron
llamatron examples/retro_chill.yml
```

`./run_tui.sh` does the same from the project folder.

Every key you can press is shown on the screen you're on. From the main screen, `S` is the song's settings, along with load, save and render. `P` is patterns, `T` is tracks, `C` is chains, `G` is generators, which holds arpeggiators and AutoRatchets for now, `Z` is scales, and `A` is Arrange, where you add scenes and clips. `H` explains the page you're on, Tab goes back, and `Q` quits from the main screen. Nothing is saved or rendered until you ask.

Renders go to `output/<song name>`. Rendering asks before replacing an earlier render, including anything saved over it in Live, so save your own work under another name.

## Song files

Songs are saved as YAML, which is mainly for the program to read, but stays readable so that songs can be compared in version control. They can also be rendered from the command line, where `--to` writes the song instead of opening the tracker:

```
llamatron examples/minimal_techno.yml --to ableton --replace
llamatron examples/minimal_techno.yml --to cliptree --out output/my_song
```

`examples/` has `minimal_techno.yml`, `retro_chill.yml` and `acid_techno.yml`, which run about three minutes each. Output goes to `output/<song name>` unless you set `--out`. `--replace` removes that song's earlier output first, and `--template` picks the Live set to build from. These three only work with `--to`.

To write a Live set for every song in `examples/` at once, use `./run_examples.sh`. It replaces each song's earlier set, including anything saved over it in Live, so save your own work under another name.

`backup/` holds older code the tracker doesn't use, including the Python API examples.

## Tests

```
.venv/bin/python -m unittest discover -s test
```

## License

llamatron is licensed under the GNU General Public License, version 3 or any later version. See [LICENSE](LICENSE) for details.
