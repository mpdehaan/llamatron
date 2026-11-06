# llamatron

llamatron is the sixth iteration of Michael DeHaan's project to enable faster complex compositions 
and random music through science

It is heavily inspired by Ableton Live itself and old school trackers and the brilliant Sequentix Cirklon.
It constructs songs using complex patterns, scales, and other magic and then outputs MIDI and Ableton Live
projects. Ableton is not required for use.

Against my better judgement Claude is involved in much of this current version and it's been doing a fantastic job.

The project is at an early stage, so expect things to change.

## Setup

From the top folder checkout of this project, create a virtual environment and install llamatron, which also installs [mido](https://github.com/mido/mido), PyYAML and [Textual](https://textual.textualize.io/):

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

`./llamatron.sh` does the same from the project folder.

[GUIDE.md](GUIDE.md) explains how to use llamatron, from installing to every feature of each page. Every key you can press is shown on the screen you're on. From the main screen, `S` jumps to the song's settings, along with load, save and render. `P` is patterns, `T` is tracks, `C` is chains, `G` is generators, which holds arpeggiators and AutoRatchets for now, `Z` is scales, and `A` is Arrange, where you add scenes and clips. `H` explains the page you're on, Tab goes back, and `Q` quits from the main screen. Nothing is saved or rendered until you ask. What these objects mean and how they inter-relate to one another is well
explained in the GUIDE.

Rendered files go to `output/<song name>`. Rendering asks before replacing an earlier render, including anything saved over it in Live, so save (Save As) your own work under another name.  The goal of llamatron
is to the starting point for a Live set, so you would then go into live, make instrument choices, add effects, automation, and make any further changes you want.  Projects are then usable in both
Session and Arrangement view.

If you are using another DAW (such a BitWig, Logic, or Reaper), tree based output will provide a sea of clips that you can drag into your project.

## Song files

Songs are saved as YAML, which is mainly for the program to read, but stays readable so that songs can be compared in version control. They can also be rendered from the command line, where `--to` writes the song instead of opening the tracker:

```
llamatron examples/minimal_techno.yml --to ableton --replace
llamatron examples/minimal_techno.yml --to cliptree --out output/my_song
```

It is very much the goal of llamatron to enable human produced intentional music with random elements, but our examples (for expediciency) are for right now AI generated and don't sound all that
great. We'll evolve these over time.

`examples/` has `minimal_techno.yml`, `retro_chill.yml` and `acid_techno.yml`, which run about three minutes each, and demos named `*_demo.yml` that each show one feature a scene at a time, described in `examples/DEMOS.md`. Output goes to `output/<song name>` unless you set `--out`. `--replace` removes that song's earlier output first, and `--template` picks the Live set to build from. These three only work with `--to`.

To write a Live set for every song in `examples/` at once, use `./run_examples.sh`. It replaces each song's earlier set, including anything saved over it in Live, so save your own work under another name.

## Tests

Tests are mostly written by AI so they may not really be that illustrative of the program's API.  They seem to help Claude out which is enough.  Usability is tested manually.


```
.venv/bin/python -m unittest discover -s test
```

## License

llamatron is licensed under the GNU General Public License, version 3 or any later version. See [LICENSE](LICENSE) for details.

## Contribution / Roadmap / Ideas / Conversation

I enjoy conversation!

At the same time, this is a personal project and it's going to be opinionated at times. I am not interested in collaborative development, code preferences, tech preferences, or criticism, 
but if you have ideas  or want to share anything I'm always interested in conversation and maybe I can ask Claude to implement them in a way that others can share. 
Please do not use GitHub for conversation, bugs, or requests. If you have a cool idea we can see what makes sense, but I also do want to keep things relatively focused.

There are some other ideas in the pipe around generation and arps and so on and this will continue to evolve.

If there are ways we can output MIDI trees better for other DAWs that would make sense.  I have a lot of experience trying to get realtime MIDI working and I don't want to do that.
It is a mess in Python and starts to make the connectivity problematic if we change this to be a live performance tool. This tool is strictly trying to be a entry point to jumpstart
Live (and other DAW) sets.

## Author

Michael DeHaan <michael @ michaeldehaan.net> 
home.laserllama.net
laserllama.substack.com


