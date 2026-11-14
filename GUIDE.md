# llamatron

llamatron is a tracker for the terminal: a composing environment where songs are built from shared patterns, scales and generators, arranged in scenes, and played. It plays in real time through MIDI hardware, software synthesizers or a DAW, or through FluidSynth with no setup at all, and exports to Ableton Live sets, MIDI files and WAV audio, so that a song can be finished in any DAW.

A file holds a set of songs, like the songs of one concert. The patterns, scales, generators, chains, grooves and instruments belong to the set, and every song shares them; each song has its own tempo, scale, seed, groove, tracks, registers and scenes.

## Intro

### Why llamatron

| Page | What it covers |
| --- | --- |
| [Why llamatron](docs/WHY_LLAMATRON.md) | What llamatron takes from Ableton Live, the Cirklon and the Monomachine, and where it goes its own way. |

### Installing

| Page | What it covers |
| --- | --- |
| [Installing](docs/INSTALLING.md) | Installing llamatron, and why and when to install FluidSynth. |
| [FluidSynth](docs/FLUIDSYNTH.md) | The software synthesizer that plays every demo with no setup: installing it, and how the tracker uses it. |
| [Recording](docs/INSTALLING_RECORDING.md) | What recording videos needs installed and set up: BlackHole, a Multi-Output Device, permissions and Xcode's tools. |

### Getting Started

| Page | What it covers |
| --- | --- |
| [Getting Started](docs/GETTING_STARTED.md) | Starting llamatron, the layout of every screen, keyboard control, opening and saving, and a first song. |

### Concepts

| Page | What it covers |
| --- | --- |
| [Concepts](docs/CONCEPTS.md) | The ideas that join the pages: audio, chord progressions, shaping sections, randomness, hockets, performing, recording and exporting. |

## Demo Songs

**[▶ See every demo song](docs/DEMOS.md)**: each example set, what it plays, how long it lasts and which features it shows, with videos to watch. Every demo plays as it comes through FluidSynth: open one, press `A` for Arrange, move to the top left corner and press `Space`.

[![The Density demo, edm_density.yml, on YouTube](https://img.youtube.com/vi/68vSj5sSW3c/hqdefault.jpg)](https://www.youtube.com/watch?v=68vSj5sSW3c)

| Page | What it covers |
| --- | --- |
| [About Demos](docs/DEMOS.md) | Opening and playing the example sets, and the pages that describe them. |
| [Listening to the Demos](docs/LISTENING_TO_DEMOS.md) | Every demo as a WAV file, made and played with no synthesizer. |
| [Tutorial Demos](docs/demos/TUTORIAL.md) | The learning demos, in the order to learn them. |
| [Blues](docs/demos/BLUES.md) | The blues demo songs. |
| [Children's](docs/demos/CHILDRENS.md) | The children's demo songs. |
| [Classical](docs/demos/CLASSICAL.md) | The classical demo songs. |
| [Electronic](docs/demos/ELECTRONIC.md) | The electronic demo songs. |
| [Exercise](docs/demos/EXERCISE.md) | The exercise demo songs. |
| [Folk](docs/demos/FOLK.md) | The folk demo songs. |
| [Gospel](docs/demos/GOSPEL.md) | The gospel demo songs. |
| [Pop](docs/demos/POP.md) | The pop demo songs. |
| [Ragtime](docs/demos/RAGTIME.md) | The ragtime demo songs. |
| [Rock](docs/demos/ROCK.md) | The rock demo songs. |
| [Soundtrack](docs/demos/SOUNDTRACK.md) | The soundtrack demo songs. |
| [TV Theme](docs/demos/TV_THEME.md) | The TV theme demo songs. |
| [Video Game](docs/demos/VIDEO_GAME.md) | The video game demo songs. |
| [World](docs/demos/WORLD.md) | The world demo songs. |
| [Other](docs/demos/OTHER.md) | The demos in `examples/other/`, which fit no other folder. |

## Objects

Each object of a set has a page in the tracker and a page here, with its settings and keys; `F1` on any page of the tracker lists its keys too.

| Object | Key on the main screen | Page |
| --- | --- | --- |
| Sets and songs | `F`, `S` | [Object Model](docs/OBJECT_MODEL.md) |
| Patterns | `P` | [Patterns](docs/PATTERNS.md) |
| Scenes | `A`, then a scene's name | [Scenes](docs/SCENES.md) |
| Tracks | `A`, then a track's name | [Tracks](docs/TRACKS.md) |
| Instruments | `I` | [Instruments](docs/INSTRUMENTS.md) |
| The arrangement | `A` | [Arrange](docs/ARRANGE.md) |
| Clips | `A`, then a clip | [Clips](docs/CLIPS.md) |
| Scales | `Z` | [Scales](docs/SCALES.md) |
| Registers | `R` | [Registers](docs/REGISTERS.md) |
| Chains | `C` | [Chains](docs/CHAINS.md) |
| Grooves | `V` | [Grooves](docs/GROOVES.md) |

## Generators

A generator changes how a clip's notes are played, without changing its pattern. The overview describes what every generator shares, and each generator has a page of its own, grouped by what it changes.

| What it covers | Page |
| --- | --- |
| What generators are, and what they share | [Generators](docs/GENERATORS.md) |

### Arrangement

| What it does | Page |
| --- | --- |
| A melody dealt out among tracks | [Hocket](docs/generators/HOCKET.md) |

### Articulation

| What it does | Page |
| --- | --- |
| Notes sliding into the next | [Glide](docs/generators/GLIDE.md) |
| Notes played short on chosen steps | [Shorten](docs/generators/SHORTEN.md) |

### Chords

| What it does | Page |
| --- | --- |
| A chord played one note at a time | [Arpeggiator](docs/generators/ARPEGGIATOR.md) |
| A figure moved through chords | [Progression](docs/generators/PROGRESSION.md) |
| Chords spread in time like a pick | [Strum](docs/generators/STRUM.md) |
| Chords voiced nearest the chord before | [Voice Leading](docs/generators/VOICE_LEADING.md) |

### Rhythm

| What it does | Page |
| --- | --- |
| Notes chopped into quick repeats | [AutoRatchet](docs/generators/AUTORATCHET.md) |
| Only the notes on a Euclidean rhythm | [Euclid](docs/generators/EUCLID.md) |

### Timing

| What it does | Page |
| --- | --- |
| Notes pushed late | [Drag](docs/generators/DRAG.md) |
| Notes pushed early | [Rush](docs/generators/RUSH.md) |

### Transitions

| What it does | Page |
| --- | --- |
| How long notes sound, ramping over a section | [Articulate](docs/generators/ARTICULATE.md) |
| How many notes play, ramping over a section | [Density](docs/generators/DENSITY.md) |
| One slow change over the whole song | [Drift](docs/generators/DRIFT.md) |
| How loud notes play, ramping over a section | [Swell](docs/generators/SWELL.md) |

## File Operations

| Page | What it covers |
| --- | --- |
| [Exporting](docs/EXPORTING.md) | Every kind of export: Ableton Live sets, MIDI files and WAV audio, from the tracker and the command line. |
| [Importing](docs/IMPORTING.md) | A MIDI file made into a new song of the set. |

## MIDI & Performance

| Page | What it covers |
| --- | --- |
| [MIDI Setup](docs/MIDI_SETUP.md) | Playing into a synthesizer or Ableton Live on a Mac, and what to do when nothing sounds. |
| [Playing Live](docs/PLAYING_LIVE.md) | Real-time playback, launching scenes and clips, and live editing. |
| [Visualizers](docs/VISUALIZERS.md) | Moving pictures drawn from the notes as a song plays. |

## Advanced

| Page | What it covers |
| --- | --- |
| [User Scripts](docs/USER_SCRIPTS.md) | Every script in `user_scripts/`, by category, with an example of running each and its parameters. |
| [Recording](docs/RECORDING.md) | Videos of a set playing, by itself or performed, one at a time or every demo in a batch. |
| [Architecture](docs/ARCHITECTURE.md) | How the code is put together, for anyone reading it, with a link to it on GitHub. |

[![llamatron's visualizers, on YouTube](https://img.youtube.com/vi/yt9NffJ1HF4/hqdefault.jpg)](https://www.youtube.com/watch?v=yt9NffJ1HF4)

## Trademarks

Ableton and Ableton Live are trademarks of Ableton AG. Elektron and Monomachine are trademarks of Elektron Music Machines MAV AB. Sequentix and Cirklon are trademarks of Sequentix Music Systems Ltd. Apple and macOS are trademarks of Apple Inc., registered in the U.S. and other countries. YouTube is a trademark of Google LLC. GitHub is a trademark of GitHub, Inc. Linux is the registered trademark of Linus Torvalds in the U.S. and other countries. All other trademarks are the property of their respective owners. llamatron is an independent project, not affiliated with, sponsored by or endorsed by any of these companies; their names are used only to describe compatibility and inspiration.
