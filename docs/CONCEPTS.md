# Concepts

Each of the other pages covers one part of the tracker in full. This page covers the ideas that join them, in the order a song grows: hearing it as you work, moving one figure through chords, shaping sections, introducing randomness, passing a melody between voices, performing, and recording and exporting. Each section explains the idea, then gives the pages and keys, and links the page with every detail. This page follows on from [Getting Started](GETTING_STARTED.md), whose first song, a melody, a kick drum and a scene that plays them, is the starting point.

## Enabling Audio

A song is easiest to write when every change is heard as it is made. llamatron plays a set in real time through its instruments: each instrument names a device, either a MIDI port connected to a synthesizer or DAW, or `*FluidSynth`, the software synthesizer the tracker starts by itself. A track chooses the instrument it plays through. While a song plays, every edit on any page is heard, at the moment the song's Live Response setting says.

1. On the main screen, press `I` for Instruments and `A` to add one. On its Device field, press `Enter` and choose `*FluidSynth`, or one of your MIDI ports, and give it a General MIDI sound if it plays through FluidSynth. Adding the first instrument turns the set's Real Time switch on. See [Instruments](INSTRUMENTS.md).
2. On Arrange, move to a track's name and press `Enter` for the track editor, and choose the instrument on its Instrument field. A drum track wants Drum on, and plays on channel 10 through FluidSynth. See [Tracks](TRACKS.md).
3. On Arrange, move to the top left corner, where `▶ song` shows, and press `Space`. The song plays on while you move to any page. See [Playing Live](PLAYING_LIVE.md).

## Chord Progressions

A pattern is written once and played in many places, and a generator changes how it plays without changing what it says. The most useful case is a chord progression: write a one-bar figure over chord I, an arpeggio, a bass line or a chord, and a Progression generator moves the figure through the chords, so that one bar becomes a whole section, and changing the progression rewrites the section without touching the pattern.

1. On Patterns, `P`, write a one-bar figure on degree 1. See [Patterns](PATTERNS.md).
2. On Generators, `G`, open Progressions and press `A`. In the progression's editor, press `Enter` on Chords, then `H` to pick a named progression, such as pop or twelve-bar blues, matched to the song's scale. See [Progression](generators/PROGRESSION.md).
3. On Chains, `C`, add a chain and put the progression in it. See [Chains](CHAINS.md).
4. Put the chain on the clips that play the figure, on the clip page's Chains field, or on the Scene page to move a whole section, or in the track editor to move every clip of a track. See [Clips](CLIPS.md) and [Scenes](SCENES.md).
5. For chords that move smoothly rather than jumping, add a Voice Leading generator after the progression in the same chain. See [Voice Leading](generators/VOICE_LEADING.md).

`examples/learning/06_chord_progression_generator.yml` is this recipe, finished.

## Shaping Sections

A section of a song often changes over its length: a build grows denser, a crescendo grows louder, a breakdown thins out. Three shapes do this, each a percentage that ramps from a start to an end: Density, how many notes play; Swell, how loud they are; and Articulate, how long they sound.

1. On Arrange, copy a scene with `C` to make the next section, and change its clips. See [Arrange](ARRANGE.md).
2. On the scene's Scene page, open `+ Density` and set Density start to 25 and Density end to 100: the section starts sparse and fills in to a build. `+ Swell` does the same for loudness, and `+ Articulate` for length. See [Scenes](SCENES.md).
3. To give many sections the same shape and change it in one place, make a Density, Swell or Articulate generator instead, and put it in a chain on those scenes. See [Density](generators/DENSITY.md), [Swell](generators/SWELL.md) and [Articulate](generators/ARTICULATE.md).

`examples/by_genre/electronic/edm_density.yml` and `examples/learning/16_bolero_swell.yml` show both ways.

## Introducing Randomness

A part that plays exactly the same every time can sound mechanical. llamatron can vary a song by chance, while keeping that chance under control: every random choice draws from the song's seed, so a song with no seed plays a new take each time, and a song with a seed plays the same take every time.

1. On a pattern's rows, set Probability on a few steps, so that their notes come and go. See [Patterns](PATTERNS.md).
2. Through the pattern editor's `R` (Reconfigure), choose a play direction, such as pendulum or brownian.
3. In a drum track's track editor, open `+ Euclid` to keep only the hits of a Euclidean rhythm; `H` on Hits picks a named one. See [Euclid](generators/EUCLID.md).
4. On the Song page, choose a groove for swing. See [Grooves](GROOVES.md).
5. For a part that wanders slowly over the whole song, add a Drift generator to the clips' chains. See [Drift](generators/DRIFT.md).
6. To keep a take you like, set a seed on the Song page. See [Object Model](OBJECT_MODEL.md).

## Hocketing

A hocket passes a melody between voices, one note each, as singers did in early music. In llamatron one track plays the melody as a source, and a Hocket generator deals its notes out among other tracks, so that no single sound plays every note.

1. Make a track that plays the melody, and turn its Mute on in the track editor, so that it is only a source.
2. Make three or four tracks, each with an instrument and a pattern of rests.
3. On Generators, add a Hocket, and choose the melody's track on its Source Track field.
4. Put the Hocket's chain on the voices' clips. The voices take turns at the melody, a note each.

See [Hocket](generators/HOCKET.md). `examples/learning/19_hocket_shanty.yml` does this with four voices.

## Performing

A song can be performed rather than only played from the top: scenes and clips are launched by hand, held, and changed as they play, with every launch landing on the next bar.

1. On the Song page, set Live Response to "next bar", so that edits land on the beat, or "ASAP" for at once. See [Object Model](OBJECT_MODEL.md).
2. Play from Arrange, and launch scenes by hand with `Space` on their names, or a single clip with `Space` on it; each launch waits for the next bar. See [Playing Live](PLAYING_LIVE.md).
3. To hold a section while you work, turn on its clips' Loop on the clip page: the scene plays on. Then change anything, a scale, a pattern or a generator, and hear it come in.
4. On Arrange, `Z` shows a visualizer over the clips while the song plays. See [Visualizers](VISUALIZERS.md).

## Recording and Exporting

A finished song leaves the tracker in three ways: as a video, as audio, or as a project to finish in a DAW.

- **A video:** `sh user_scripts/record.sh --sound fluidsynth --interactive examples/learning/01_hello_world.yml` records you performing a set, ending when you stop it on the corner; the other recording scripts play a set by itself or through a DAW. See [Recording](RECORDING.md).
- **Audio:** `Ctrl+X` and WAV (FluidSynth) writes the song as a WAV file. See [Exporting](EXPORTING.md).
- **A DAW project:** `Ctrl+X` and Ableton Live set, or one of the MIDI kinds for another DAW, then add instruments, effects and mixing there. See [Exporting](EXPORTING.md).
