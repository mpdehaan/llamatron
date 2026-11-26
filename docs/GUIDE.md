# llamatron

llamatron is a tracker for the terminal: a composing environment where songs
are built from shared patterns, scales and generators, arranged in scenes, and
played. It plays in real time through MIDI hardware, software synthesizers or
a DAW, or through FluidSynth with no setup at all, and exports to Ableton Live
sets, MIDI files and WAV audio, so that a song can be finished in any DAW.

A file holds a set of songs, like the songs of one concert. The patterns,
scales, generators, chains, grooves and instruments belong to the set, and
every song shares them; each song has its own tempo, scale, groove, tracks,
draws and scenes.

## Intro

### Why llamatron

| Page | What it covers |
| --- | --- |
| [Why llamatron](WHY_LLAMATRON.md) | What llamatron takes from Ableton Live, the Cirklon and the Monomachine, and where it goes its own way. |

### Installing

| Page | What it covers |
| --- | --- |
| [Installing](INSTALLING.md) | Installing llamatron, and why and when to install FluidSynth. |
| [FluidSynth](FLUIDSYNTH.md) | The software synthesizer that plays every demo with no setup: installing it, and how the tracker uses it. |
| [Recording](INSTALLING_RECORDING.md) | What recording videos needs installed and set up: BlackHole, a Multi-Output Device, permissions and Xcode's tools. |
| [Building llamatron](BUILDING_THE_BACKEND.md) | Building the program that plays the built-in synths and FluidSynth and sends MIDI, with one script that offers to install what it needs. |

### Getting Started

| Page | What it covers |
| --- | --- |
| [Getting Started](GETTING_STARTED.md) | Starting llamatron, the layout of every screen, keyboard control, opening and saving, and a first song. |

### Concepts

| Page | What it covers |
| --- | --- |
| [Concepts](CONCEPTS.md) | The ideas that join the pages: audio, chord progressions, shaping sections, randomness, hockets, performing, recording and exporting. |

## Demo Songs

**[▶ See every demo song](DEMOS.md)**: each example set, what it plays,
how long it lasts and which features it shows, with videos to watch. Every
demo plays as it comes through FluidSynth: open one, press `A` for Arrange,
move to the top left corner and press `Space`.

[![The Density demo, edm_density.yml, on
YouTube](https://img.youtube.com/vi/68vSj5sSW3c/hqdefault.jpg)](https://www.youtube.com/watch?v=68vSj5sSW3c)

| Page | What it covers |
| --- | --- |
| [About Demos](DEMOS.md) | Opening and playing the example sets, and the pages that describe them. |
| [Tutorial Demos](demos/TUTORIAL.md) | The learning demos, in the order to learn them. |
| [Blues](demos/BLUES.md) | The blues demo songs. |
| [Children's](demos/CHILDRENS.md) | The children's demo songs. |
| [Classical](demos/CLASSICAL.md) | The classical demo songs. |
| [Country](demos/COUNTRY.md) | The country demo songs. |
| [Electronic](demos/ELECTRONIC.md) | The electronic demo songs. |
| [Exercise](demos/EXERCISE.md) | The exercise demo songs. |
| [Folk](demos/FOLK.md) | The folk demo songs. |
| [Gospel](demos/GOSPEL.md) | The gospel demo songs. |
| [Metal](demos/METAL.md) | The metal demo songs. |
| [Pop](demos/POP.md) | The pop demo songs. |
| [Ragtime](demos/RAGTIME.md) | The ragtime demo songs. |
| [Rock](demos/ROCK.md) | The rock demo songs. |
| [Soundtrack](demos/SOUNDTRACK.md) | The soundtrack demo songs. |
| [TV Theme](demos/TV_THEME.md) | The TV theme demo songs. |
| [Video Game](demos/VIDEO_GAME.md) | The video game demo songs. |

## Demos (Synth)

The demo songs played wholly on llamatron's built-in synths.

| Page | What it covers |
| --- | --- |
| [Synth](demos/SYNTH.md) | The demo songs on the built-in synths. |

## Mashup Demos

| Page | What it covers |
| --- | --- |
| [Blues Mashup](demos/BLUES_MASHUP.md) | Another work's notes set on a blues band. |
| [Electronic Mashup](demos/ELECTRONIC_MASHUP.md) | Another work's notes set on an electronic band. |
| [Funk Mashup](demos/FUNK_MASHUP.md) | Another work's notes set on a funk band. |
| [Jazz Mashup](demos/JAZZ_MASHUP.md) | Another work's notes set on a jazz band. |
| [Metal Mashup](demos/METAL_MASHUP.md) | Another work's notes set on a metal band. |
| [Rock Mashup](demos/ROCK_MASHUP.md) | Another work's notes set on a rock band. |
| [World Mashup](demos/WORLD_MASHUP.md) | Another work's notes set on a world band. |

## Objects

Each object of a set has a page in the tracker and a page here, with its
settings and keys; `F1` on any page of the tracker lists its keys too.

| Object | Key on the main screen | Page |
| --- | --- | --- |
| Sets and songs | `F`, `S` | [Object Model](OBJECT_MODEL.md) |
| Patterns | `P` | [Patterns](PATTERNS.md) |
| Scenes | `A`, then a scene's name | [Scenes](SCENES.md) |
| Tracks | `A`, then a track's name | [Tracks](TRACKS.md) |
| Instruments | `I` | [Instruments](INSTRUMENTS.md) |
| The arrangement | `A` | [Arrange](ARRANGE.md) |
| Clips | `A`, then a clip | [Clips](CLIPS.md) |
| Scales | `Z` | [Scales](SCALES.md) |
| Draws | `D` | [Draws](DRAWS.md) |
| Grooves | `V` | [Grooves](GROOVES.md) |

## Generators

A generator changes how a clip's notes are played, without changing its
pattern. The overview describes what every generator shares, and each
generator has a page of its own.

| What it covers | Page |
| --- | --- |
| What generators are, and what they share | [Generators](GENERATORS.md) |
| A chord played one note at a time | [Arpeggiator](generators/ARPEGGIATOR.md) |
| Several generators shared as one list | [Chain](generators/CHAIN.md) |
| A figure moved through chords, or to the chords another track plays, and its chords voiced | [Chords](generators/CHORDS.md) |
| One slow change over the whole song | [Drift](generators/DRIFT.md) |
| Chords and notes played as a guitar plays them | [Guitarify](generators/GUITARIFY.md) |
| A melody dealt out among tracks | [Hocket](generators/HOCKET.md) |
| A part played as a player of the band would play it | [Musician](generators/MUSICIAN.md) |
| A tune delivered in lines, with a breath, a rise and fall | [Phrasing](generators/PHRASING.md) |
| How many notes play, how loud and how long, ramping over a section | [Shapes](generators/SHAPES.md) |
| Notes pushed early or late, played short or sliding into the next, on chosen steps | [Timing](generators/TIMING.md) |

## Song Wizard

| Page | What it covers |
| --- | --- |
| [Song Wizard](WIZARD.md) | A whole song made from a few choices: each panel of the wizard and what it holds. |

## File Operations

### Import

| Page | What it covers |
| --- | --- |
| [Importing](IMPORTING.md) | A MIDI file made into a new song of the set. |

### Export

| Page | What it covers |
| --- | --- |
| [Exporting](EXPORTING.md) | Ableton Live sets, MIDI files and WAV audio, from the tracker and the command line. |

## MIDI & Performance

| Page | What it covers |
| --- | --- |
| [MIDI Setup](MIDI_SETUP.md) | Playing into a synthesizer or Ableton Live on a Mac, and what to do when nothing sounds. |
| [Playing Live](PLAYING_LIVE.md) | Real-time playback, launching scenes and clips, and live editing. |
| [Visualizers](VISUALIZERS.md) | Moving pictures drawn from the notes as a song plays. |

## Synths

llamatron's own synthesizers: how an instrument's sound is built, each engine,
and each of its parts.

| Page | What it covers |
| --- | --- |
| [Synths](SYNTHS.md) | The built-in synths' design, their engines and how the sound is made. |
| [Oscillators](synths/OSCILLATORS.md) | Each engine's oscillators and the Voice column. |
| [Envelopes](synths/ENVELOPES.md) | Every envelope type, and how each moves. |
| [LFOs](synths/LFOS.md) | The four LFOs. |
| [Filters](synths/FILTERS.md) | Every filter type and the low-pass gate. |
| [Effects](synths/EFFECTS.md) | Drive, Bitcrush and the effects planned. |
| [Mod Matrix](synths/MOD_MATRIX.md) | What moves what. |

### Standard Engines

#### Basic

| Page | What it covers |
| --- | --- |
| [Basic](synths/engines/BASIC.md) | Up to three band-limited oscillators of classic waveforms. |

#### Analog Mono

| Page | What it covers |
| --- | --- |
| [Fishline](synths/engines/FISHLINE.md) | The acid bass. |
| [Asheville](synths/engines/ASHEVILLE.md) | Planned. |
| [Monorail](synths/engines/MONORAIL.md) | Planned. |

#### Analog Poly

| Page | What it covers |
| --- | --- |
| [Choir](synths/engines/CHOIR.md) | Planned. |
| [MozaicClassic](synths/engines/MOZAICCLASSIC.md) | Planned. |
| [MozaicHypersaw](synths/engines/MOZAICHYPERSAW.md) | Planned. |
| [Syrup](synths/engines/SYRUP.md) | Planned. |

#### Chip

| Page | What it covers |
| --- | --- |
| [SID](synths/engines/SID.md) | An 8-bit sound chip's voice. |
| [Pocket](synths/engines/POCKET.md) | A 4-bit chip's pulse, drawn wave and noise. |
| [DustCart](synths/engines/DUSTCART.md) | Planned. |
| [BitArcade](synths/engines/BITARCADE.md) | Planned. |
| [Bytecrunch](synths/engines/BYTECRUNCH.md) | Planned. |

#### Classic Keys

| Page | What it covers |
| --- | --- |
| [Piano](synths/engines/PIANO.md) | Planned. |
| [Tonewheel](synths/engines/TONEWHEEL.md) | Planned. |
| [Combo Organ](synths/engines/COMBO_ORGAN.md) | Planned. |
| [Stringy](synths/engines/STRINGY.md) | Planned. |

#### Digital

| Page | What it covers |
| --- | --- |
| [FM](synths/engines/FM.md) | Planned. |

#### Noise and Glitch

| Page | What it covers |
| --- | --- |
| [Bit Saw](synths/engines/BIT_SAW.md) | Planned. |
| [PhoneHome](synths/engines/PHONEHOME.md) | Planned. |
| [Dialup](synths/engines/DIALUP.md) | Planned. |

#### Other Modelling

| Page | What it covers |
| --- | --- |
| [Pluck](synths/engines/PLUCK.md) | Planned. |
| [Strings](synths/engines/STRINGS.md) | Planned. |
| [Pipe](synths/engines/PIPE.md) | Planned. |

#### Wavetable

| Page | What it covers |
| --- | --- |
| [Wavetable](synths/engines/WAVETABLE.md) | Planned. |

#### West Coast

| Page | What it covers |
| --- | --- |
| [ComplexOsc](synths/engines/COMPLEXOSC.md) | Planned. |
| [Harm](synths/engines/HARM.md) | Planned. |

### Drum Engines

#### Classic

| Page | What it covers |
| --- | --- |
| [MechaDrum](synths/engines/MECHADRUM.md) | A drum machine of ten drums. |
| [Oh8](synths/engines/OH8.md) | Planned. |
| [Oh9](synths/engines/OH9.md) | Planned. |
| [SynTom](synths/engines/SYNTOM.md) | Planned. |

#### FM Drums

| Page | What it covers |
| --- | --- |
| [FM](synths/engines/FM_DRUMS.md) | The FM Kick, Snare, Tom, Metal and Bell, planned. |

#### Noise

| Page | What it covers |
| --- | --- |
| [Glitch Drum](synths/engines/GLITCH_DRUM.md) | Planned. |
| [Chirpy](synths/engines/CHIRPY.md) | Planned. |
| [Pocket Drum](synths/engines/POCKET_DRUM.md) | Planned. |

#### Modelling

| Page | What it covers |
| --- | --- |
| [Struck](synths/engines/STRUCK.md) | Planned. |

## Advanced

| Page | What it covers |
| --- | --- |
| [User Scripts](USER_SCRIPTS.md) | Every script in `user_scripts/`, by category, with an example of running each and its parameters. |
| [Recording](RECORDING.md) | Videos of a set playing, by itself or performed, one at a time or every demo in a batch. |
| [Architecture](../developer_docs/ARCHITECTURE.md) | How the code is put together, for anyone reading it, with a link to it on GitHub. |
| [Backend](BACKEND.md) | How the backend works inside, its messages, threads, synths, sender and safety, for anyone changing it. |

[![llamatron's visualizers, on
YouTube](https://img.youtube.com/vi/yt9NffJ1HF4/hqdefault.jpg)](https://www.youtube.com/watch?v=yt9NffJ1HF4)

## Trademarks

Ableton and Ableton Live are trademarks of Ableton AG. Elektron and
Monomachine are trademarks of Elektron Music Machines MAV AB. Sequentix and
Cirklon are trademarks of Sequentix Music Systems Ltd. Apple and macOS are
trademarks of Apple Inc., registered in the U.S. and other countries. YouTube
is a trademark of Google LLC. GitHub is a trademark of GitHub, Inc. Linux is
the registered trademark of Linus Torvalds in the U.S. and other countries.
All other trademarks are the property of their respective owners. llamatron is
an independent project, not affiliated with, sponsored by or endorsed by any
of these companies; their names are used only to describe compatibility and
inspiration.
