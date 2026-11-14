# Why llamatron

llamatron is a tool for composing music before it reaches the DAW, and it can also play music fully on its own, through MIDI devices or through FluidSynth.

llamatron borrows from three places: Ableton Live, whose Session View shapes how a song is laid out; the Sequentix Cirklon, whose step sequencing shapes how patterns are written; and the Elektron Monomachine, whose arpeggiator and parameter locks shape how a few notes become a line. This page says what was taken from each, where llamatron does things differently, and why. From those starting points llamatron soon goes its own way, above all in its generators and in how chains of generators reshape a song.

## Composing Before the DAW

In llamatron's view, a DAW is where a piece of music is finished: instruments, effects, automation, mixing. A DAW is not the cheapest place to try a structural idea. Changing the key of a song, swapping a bass line under every section, or trying a different play order for a riff means editing many clips by hand.  

llamatron, by contrast, is a tool for composing at the scale of a whole song, precise enough to change one note and broad enough to recast whole sections at once. Its notes aren't tied to a particular clip: patterns are shared between clips, and that sharing is where the rest of its design begins.

llamatron keeps the structure saved in a YAML file: the patterns, the scales, the tracks, the scenes and the settings that tie them together. The file holds a set of songs, much as a band plays a set at a concert: the set shares the patterns, scales, generators, chains and grooves, and each song in it has its own tracks and scenes.

llamatron can play a Live set in real time over MIDI, and exporting turns a song into a Live set or a set of MIDI files in seconds.

The intent is that a song's shape is worked out here, quickly and with room to try things, and then finished in Live, where the work of sound design and automation belongs. A song can also stay here to the end: played live, recorded as a video, or exported as a WAV file.

## Shared Patterns

In Live, a clip owns its notes. A riff that plays on three tracks, or in five scenes, is three or five copies of the same notes, and a change to the riff has to be made in each.

In llamatron a pattern is written once and clips refer to it by name. Change the pattern and every clip that plays it follows. The same rule holds throughout: clips name patterns, chains and tracks; chains name generators; the song, its scenes and its clips name scales; tracks name instruments. Renaming anything updates everything that refers to it, so names are safe to choose and change.

## Degrees and Scales

A pattern holds scale degrees rather than pitches, and a degree is bound to a note as late as possible, when the clip that plays it knows its scale. A scale is chosen by the song, and any scene, or any single clip, can choose another. A key change is one edit, and a modulation for one section is one edit to that scene.

Chords follow the same idea. A chord written as a number, like `7`, stacks scale notes above the degree, so it stays in the scale and changes with it: a seventh on the second degree of a major scale is minor, and on the fifth it is dominant. Named chord symbols, like `dom7` or `m7b5`, are exact intervals for the times a chord should leave the scale. The two are kept apart on purpose, so that a bare number always means a chord of the scale.

Scales are named objects of the set, and a name can be anything. A song whose scenes all use a scale called `main` can be moved to a new key by changing what `main` is.

The cost of this is that writing in llamatron means thinking in scales. Drum patterns, which use note letters, and fixed chord symbols are the ways around it.

## Generators and Chains

A pattern says what a part is; a generator says how it is played. A generator takes the notes a clip has made and changes them, and because it works on the finished clip rather than on the pattern, it changes nothing that is written: the pattern stays as it was, other clips that play it are untouched, and the generator follows whatever scale, chord or tempo the clip is in when it plays.

Generators are kept in chains, lists of generators that run one after another, each working on what the last one made. A clip names the chains it runs, and so can a scene and a track: a clip runs its own, then its scene's, then its track's, so one chain on a track can shape every clip the track plays, and one on a scene can shape a whole section.

The way to think of a generator is as paint. A chain applies it to exactly the clips that should have it, and editing the generator afterwards changes everything painted with it, at once, across every song of the set. Where a setting can also be made on a single clip, scene or track, like a strum or a density, the generator is still worth having for the clips across a song that should share one shape.

There are many kinds, all listed together on the Generators page:

- **Arpeggiators and AutoRatchets**, which turn chords into lines and notes into repeats (see the Monomachine, below).
- **Progressions**, which move a figure written over one chord through a chord progression, and **Voice leading**, which plays each chord in the inversion nearest the one before.
- **Strums**, which spread a chord's notes in time like a guitarist's hand, and **Euclids**, which keep only the notes that land on a Euclidean rhythm.
- **Densities, Swells and Articulates**, which shape how many notes play, how loud and how long, ramping across a clip or a section, for builds, crescendos and fades.
- **Glides, Shortens, Rushes and Drags**, rows of steps that slide notes into the next, shorten them, or push them early and late, each on its own cycle against the pattern.
- **Drifts**, one slow process for the whole song that moves velocity, probability, degrees, the scale or the root from one version to another as the song goes on.
- **Hockets**, which deal one track's notes out among other tracks in turn, one note each, so a melody passes between voices.

Each generator says when it starts over: with every clip, the first time each scene plays, or never, carrying on along the song from its top, so that a progression or an arpeggio can run across scenes rather than restarting at every clip. Every generator that draws anything at random draws it from the song's seed.

## Cirklon Influences

The pattern editor is a Cirklon-style step grid: one row per property, one column per step, with rows for the degree, gate, velocity, probability, ratchet, glide, tie and the rest, grouped into sections that open and close so that a long list of rows stays readable. It also has a piano roll view of the same pattern, which Tab switches to. From the Cirklon also come:

- Play directions, by the Cirklon's names: forward, reverse, alternate, pendulum, random, brownian and the others, with a pattern's length unchanged whichever order its steps play in.
- Note grab, where a step takes the note another track most recently played.
- Ratchets, which split a step into equal repeats, and ratchet offsets, which move each repeat along the scale.
- CC rows, like the Cirklon's aux rows, each assigned a CC number per track, so that one pattern can move different controls on different tracks.
- Ties, which hold a note across the steps that follow it.
- A text interface that is quick to move around in. The Cirklon's screens put a lot of information in a small space and reach any of it in a few presses, and llamatron's pages are built the same way.

The Cirklon's accumulators are the model for llamatron's registers, four numbers the whole song shares, which any step can set, add to or subtract from, and use to move a note along the scale or change a velocity. They work a little differently from accumulators, being song-wide rather than per pattern and kept from scene to scene unless a scene resets them, but they are very much inspired by them. llamatron takes them further: a step can sound only when a condition between two registers holds, a register can say what happens past its limits (stop, start over, wrap around or land somewhere at random), an arpeggiator and a drift can add to them too, and a register can drive a track's velocity or one of its CC lanes directly.

Where the Cirklon's patterns are arranged by a song mode, llamatron's are arranged on the Arrange page's grid of scenes and tracks, which comes from Live (see the text interface, below).

## Monomachine Influences

The arpeggiator takes its design from the Monomachine's. Besides playing a chord's notes in order, it has an octave range, a choice of when to jump octaves, and its own row of up to sixteen offset steps, each moving the note it plays along the scale, with silent steps allowed. With offsets, a single held note or chord becomes a line of its own, which is how lead parts can be written from very little.

Slide on a CC row ramps a value to the next one, as the Monomachine's parameter slide does. The CC rows themselves can be used the way Elektron parameter locks are: a value set on a step changes a parameter as that step plays. The difference is that a value in llamatron holds until the next one is set, where a parameter lock applies to its step alone. The CC rows are also the Cirklon's aux rows, and the two influences meet there.

## Controlled Chance

llamatron has many more ways to introduce randomness than a DAW's clip editor: probability per step, random and brownian play directions, random arpeggiator orders, drifts that wander between two versions of a part, registers that can land on a random value, and chains of generators that stack all of these on a clip. Every one of them is seeded. A song with no seed renders a new take each time. A song with a seed renders the same take every time, and changing the seed gives a different one that can be kept. While a song plays in real time, one take is kept for the whole play, so that an edit changes only what was edited.

Randomness never changes a length. A note that probability drops becomes a rest of the same length, and a random direction plays the same number of steps, so the arrangement stays as written while the notes vary.

## Live Play

A song can be played in real time while it is being written, through MIDI to hardware or software synths, or through FluidSynth, a software synthesizer llamatron starts by itself, so that someone with no synthesizer and no DAW hears every example the moment they press play. Each track chooses an instrument, a MIDI device and channel or FluidSynth, and every example plays through FluidSynth as it comes.

Playing follows Live's Session View. Space on a scene launches it, and when it is done each clip's follow action starts the clip below, so a song plays from top to bottom as the export lays it out; a clip can also be launched on its own, and every launch made by hand waits for the next bar, as Live's quantization does. Looping clips play on until the scene below starts on their track.

The song keeps playing while you edit it, on any page, and every edit is heard on what plays: a note in a pattern, a scale, a tempo, a clip made to loop, a track muted. Each song says when an edit is heard: at the next bar, at each clip's next pass, or at once. So a set can be performed: loop a scene, go make a new scale, assign it, and hear the music change under you.

While a song plays, Arrange can show a visualizer over its clips, and a take can be recorded as a video, either played from the top by itself or performed by hand, ending when you stop it. None of this changes an export: the exports always play the song as written, once through.

## Text Interface

The interface is a tracker's in spirit, a grid of steps edited from the keyboard, but it is meant to be found by looking rather than learned. Every key that works on a screen is shown on that screen or in its F1 help, so there are no shortcuts to remember, and the same few keys do the same things everywhere: Esc goes back, F1 explains the page, Enter chooses, and Space plays, stops and toggles.

The Arrange page is where Live's influence is clearest. Scenes are rows and tracks are columns, as in Session View, so the whole song is visible as one grid rather than as a list of pattern changes. Hardware sequencers tend to arrange a song as a sequence of steps that change patterns; the grid was chosen because it shows the structure at a glance.

## Other DAWs

Live is the main output, and the only one where an export produces a complete project. Other DAWs are supported to a limited degree, by exporting MIDI: one file for the whole song, a file per track, or a file per clip, with the scenes laid end to end so that every file lines up when it is dragged in, and a General MIDI file that any General MIDI player plays with a sound chosen for each track. With no DAW at all, a song can be heard through FluidSynth as it plays, or exported as a WAV file.

## Non-Goals

It is not a synthesizer or an editor of sound, though it plays songs in real time, through your synths or FluidSynth. The Live set it produces is deliberately bare: notes, tempo and CC envelopes, with no instruments, effects, panning or automation beyond that. A song meant for a release is finished in Live, where those things are easier to add and better done.
