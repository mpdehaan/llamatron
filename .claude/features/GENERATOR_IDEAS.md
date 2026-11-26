# Generator Ideas

Wanted work on the generators (the chains a clip, a track or a scene runs, and the built-in generators): what each idea is,
never its status or order (those are in `.claude/planning/QUEUE.md`). An agreed design moves to
`.claude/planning/DESIGNS.md`; an idea leaves this file once built. How the generators are built is in
`.claude/format/GENERATORS.md`.

## How Generators Work

- **Built-in generators** (DESIGNS.md, "Built-in generators and the tab box"): the plugins self-contained with the shared view
  page; combined into nine generators (Chords from Progression and Follow Chords, 1226 A; Timing from Rush and Drag, Shorten
  perhaps too; whether AutoRatchet joins the Arpeggiator; Strum into Guitarify; Density, Swell and Articulate); the tab box and
  built-ins on clips, tracks and scenes; whether tempo ramps could be a generator.
- **A generator as a self-contained plugin**: Its strings, key bindings, editor page, help, limits, file names, tools,
  screenshots and tests in its own folder; a design from what removing Euclid touched.
- **Chains as a kind of generator**: A clip, a scene and a track list generators, not chains, and a chain becomes a meta
  generator whose settings are a list of generators already defined; chains and plain generators mix in one list; a file that
  lists chains is read as before and written byte for byte the same; Chains is no longer a button of the main screen nor an
  object in the documents; a generator is made and assigned straight from the clip page's list. A discussion first, on how to
  do it safely.
- **A generator's preview**; the MIDI import on classical music (a discussion).
- **Pattern generators on the Patterns page**: Tools on the Patterns page that write a new pattern, or fill one in, from a
  few choices: a melody, a bassline, a chord progression, a drum beat and so on. They'd be different from today's
  generators, which change a clip at render time in a chain: these would write ordinary steps into a pattern once, which can
  then be edited by hand like any other. They'd live beside the clip generators in `src/llamatron/generators`, or in a
  package of their own for pattern mutators. Making them intuitive will take some thought, so nothing is decided yet.
  Questions to settle first: - **Where they live.** A key on the Patterns page that makes a new pattern, a key in the
  pattern editor that fills in or rewrites the rows under the cursor, or both. - **How few choices are enough.** Something
  like "bassline, 16 steps, follows these chords" is easy to pick, but every extra setting makes the dialog harder to use. -
  **Trying again.** A generated pattern is rarely right the first time, so generating again with another seed, and undoing,
  should each be one key. - **Following the song.** Writing degrees rather than notes keeps a generated pattern following
  the scale, as everything else does. A bassline or melody could also take its chords from another pattern, the way a grab
  takes notes from a track.
- **Gauges for a stutter and the groove editor**: steps that go up and down by so many points read better as gauges than
  numbers, as the offsets editor's signed gauge does; the groove editor's cells, signed percentages, drawn with the same
  gauge, and a stutter, which llamatron does not have yet, as the same kind of row. Sketches first, drawn the way the pattern
  editor's were.

## New Generators

- **Math**: a generator for the last place in a track's chain on the Track page, perhaps a column of its own, that
  works out rules on what has played: a comparison (a modulator or a draw rising above, or falling below, a level)
  firing a trigger, such as striking the last note played again, restarting a filter's or an envelope's sweep, or
  restarting a modulator, and the pattern's draws firing the same triggers. How it is modelled is a discussion.
- **ChordToNote**, bass lines from a track's chords (`choose_note`: lowest, highest, random); with it a **Transpose** generator
  (octaves, semitones, scale degrees).
- **The Harmonizer**: each harmonizer is one voice, in the scale, exact half steps, voice-led, or later chord tones; Delay, one
  of the time settings with "(none)" as its default, makes a canon or a round (Canon, once a generator of its own, is this
  Delay: the clip repeated a number of steps later, moved along the scale and quieter); "Follow the melody's rhythm" (the
  default) or "Keep this track's rhythm"; its lead track named on the generator, as the Hocket does, to be asked when built.
- **Drop 2 and drop 2 and 4 chord voicings**: Asked for by a user: drop 2 and drop 2 and 4 voicings, where the second note
  from the top of a close chord, or the second and the fourth, is dropped an octave. Details are not settled and need a
  discussion: whether they are a choice in the Chord Selector that the pattern editor's chord key opens, beside the
  inversions; whether they are a setting of the Chords generator's voicing; or both, and how they meet inversions and voice
  leading.
- **Bassify: a generator that plays a clip's chords as a bass player would**: The user asks whether, beside Guitarify, a
  Bassify is needed and what it would do. To discuss before anything is built. Claude's first thoughts, to bring as
  proposals: a bass has no chord to strum, so its two halves would be which note of the chord is played and how the bar is
  filled. Notes: root, fifth, octave, third, an approach note a step or a half step before the next chord, a walk through
  the scale, all kept in a bass's range on four or five strings. A bar of cells as Guitarify's, with its own strokes: root,
  fifth, octave, approach, a ghost (dead) note, a slide in, a rest, and a note held or cut short. Ready-made bars by style:
  roots in eighths, root and fifth on one and three, a walking four, octaves on the off-beats, a reggae bar that leaves beat
  one empty, a funk sixteenth bar with ghosts, a gallop, an acid bar. It would let a row of chords become a bass line with
  no bass pattern written, and give the wizard's bass player a generator to set rather than notes to write. What it
  overlaps: the Progression generator already moves a figure through chords, and the wizard's bass player already writes
  lines, so the questions are whether Bassify replaces either or sits beside them, and whether a bar of strokes is the right
  picture for a bass.
- **A humanize generator**: At the top priority. A generator, beside the arpeggiators,
  AutoRatchets and the coming Drift, that makes a part sound played by a person rather than a machine: small random changes
  to each note's velocity, its timing a little early or late, and perhaps its gate a little longer or shorter, each within a
  range the composer sets, with a seed like an arp's so that a take can be repeated. Drift's Vel+= with a small range does
  the velocity part slowly, trigger by trigger; humanize works note by note, which is what a player's hands do. What it
  needs: a settings class and an editor like the others, and a place in the render. Velocity can change on a finished clip's
  sounds in a chain, as generators work today, but timing can't: the groove moves notes in `engine/timing/timing.py` after
  the render, so humanized timing would either be applied there, as a per-note random groove, or the chain would need to
  move a note's start, which no generator does yet. Undecided: the ranges and their defaults, whether timing is in ticks,
  milliseconds or a share of a step, whether it stays inside a groove's cell so that notes keep their order, and whether a
  drum track wants different defaults from a melody. `mainstreet_hoedown.yml` is the first song it would suit.
- **Isorhythm: a rhythm and a series of pitches that repeat at different lengths**: A repeating rhythm and a repeating
  series of pitches, each of its own length, played together so that the two drift out of phase and meet again only after
  many bars, as in medieval isorhythm. To look at first: how much already works, since a pattern's rows can each have a step
  of their own and a list generator steps through its values note by note, so a row of pitches of one length under a rhythm
  of another may need only a demo; and what is missing, such as a pattern's pitch row and rhythm row having lengths of their
  own, or a generator that deals a series of degrees to whatever notes arrive.
- **Canon and imitation: a track replaying another's pattern after a delay**: A generator that replays a pattern on another
  track after a delay, moved up or down within the scale: rounds, stretto where the entries crowd closer, and phasing where
  the delay keeps growing a little each time round. What exists already: the Harmonizer's Delay repeats a clip some steps
  later, moved along the scale and quieter, on the same track. What would be new: taking the notes from another track, as
  the Hocket does, and a delay that changes over time. To settle: whether this is a new source for the Harmonizer or a
  generator of its own, and how Restart treats the growing delay.
- **Serial transforms as playback generators: inversion, retrograde, augmentation**: Generators that turn a clip's line
  upside down around a note of the scale, play the line backwards, or stretch or squeeze the line's lengths, at playback,
  leaving the pattern as written, so that they chain with Voice leading and Progression. What exists already: Munge reverses
  and pivots a pattern for good in the pattern editor, and the serial melody style of the song wizard makes the forms of a
  row. To settle: where in a chain each belongs, what retrograde means for a clip that loops or is cut short by its scene,
  and whether inversion is by scale step or by half step.
- **Velocity and CC offsets on the Arpeggiator's steps**: The Arpeggiator's grid of steps gets two more rows beside its
  offsets: a velocity row adding to or taking from each step's velocity, so an arpeggio fades or swells across its steps,
  and a CC row adding to or taking from one CC, chosen on the Arpeggiator's page (only one CC, the user's limit), so a
  filter can open across the figure. At least in the pattern grid, the user's words: the arpeggiator's own grid of steps
  first. To decide: the ranges, what a CC row sends where the clip sends no value of that CC (a value to add to), and
  whether an AutoRatchet's repeats should take the same rows.
- **Inversions for AutoChord**: AutoChord, the Chords generator's mode that turns single notes into chords, choosing an
  inversion for the chords it builds, beyond the root position and Note on top it has.
- **Transforms that enrich a melody**: Ways to make a basic melody or part richer, each one a choice the user makes, and
  repeatable with a seed: - passing tones and neighbor tones between melody notes; - chord extensions, turning triads into
  sevenths, ninths and more; - syncopation, swing, and moving notes ahead of the beat; - ornaments such as trills, turns and
  grace notes; - octave doubling, and a harmony line in thirds or sixths; - reharmonizing a chord progression with
  substitute chords. Some of these could be generators that run in a chain at render time, so that the plain pattern stays
  as written and the transform can be turned off. Others could be pattern mutators, which rewrite a pattern's steps once, so
  they can be edited afterwards. Either way, nothing is generated unless the user asks, and what comes out is ordinary
  patterns and settings.
- **A Munge generator, which takes Serialism's place in the wizard**: A generator that works on a pattern before it plays, a
  preprocessor of the pattern rather than running with the timing as the other generators do. The first idea, RandomizePitch
  (broader than serialism, maybe with no settings at first), rearranges the pitches of a pattern's steps that hold notes, at
  random by default, every note keeping its place in time, as the pattern editor's randomize pitches munge does. The later
  idea: look at which of the pattern editor's Munges work as a generator, and make one generator, Munge, that runs one of
  them on a range of steps. It would take Serialism's place in the song wizard's Experimental genre, whose serial subgenres
  are to be removed. Wanted: opinions on settings that carry Serialist ideas further. A talk of its own before anything is
  built.
- **Chordify**: While settling how generators keep their state: a generator, or a setting of
  the arpeggiator, that turns single notes into chords on chosen steps of the bar, the opposite of what the arpeggiator
  does. Painted on a whole scene, every track's copy works on the same steps, so that tracks whose patterns are the same
  length line up. Undecided: whether it is a kind of its own or part of the arpeggiator, how the steps and the chord are
  chosen (a chord symbol, as the Chord row's, or the scale's triad), and whether a note already a chord is left alone. An
  earlier ask of the same kind,: as a setting of the arpeggiator, a row like the offsets row but holding
  chord symbols, which puts a chord type on a step of the arp's cycle, so that an arp over a line can play, say, the third
  note of each cycle as a triad and the rest as single notes.
- **Melodic figures for melody generators**: Short melodic figures, a few notes each, counted across many works: which turns
  of phrase a style favours, how a figure is elaborated and ornamented. An experiment to recognize styles by them was
  started and deleted, the user's choice, since figures may only be collected from sources clearly in the public domain
  (classical scores, folk tunes, ragtime), where styles are already recognized best. The idea kept is the other use: a
  melody generator that builds a line from a style's favoured figures and its ways of varying one. What it touches in the
  code: a table of figures per style measured from the public-domain corpus alone, a new module in
  `internal_tools/analysis_and_generation/measuring/hearing/` to cut a lead into figures, and a generator in
  `src/llamatron/generators/` that reads the table. No melody of a copyrighted work is ever read
  (`.claude/features/GENRES.md`, "Only What Can Be Acted On").
- **A controller ramp over time, the sibling of Swell, Density and Articulate**: From the music expert's review of the
  electronic template. A generator, or a shape on a clip, a scene and a generator as Swell is, that writes one MIDI
  controller from a first value to a last over a span of time: a filter opening over 16 bars (controller 74, with 71 for
  resonance), a pad swelling on held notes (11), a reverb wash over the last bar (91). It is the dependency of the song
  wizard's "filter opens", "pad swell" and "wash" rises in the electronic genres; the other rises (hats filling in, a snare
  roll, a kick or bass dropping out, a gap) need only what exists. Open: whether it is a fourth shape beside Swell, Density
  and Articulate, sharing their time settings, or a generator of its own; how it meets a pattern's own CC lane of the same
  controller; and what the wizard says when the preview synth does not answer to the controller, since General MIDI sounds
  often ignore 74.
- **Guitarify presets**: Whole settings taken from the Guitarify demo, beside the ready-made bars `R` reaches.
