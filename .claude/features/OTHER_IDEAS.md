# Other Ideas

Wanted work that is not the synths, the generators, the song wizard, a demo or the UX: what each idea is, never its status or order (those
are in `.claude/planning/QUEUE.md`). An agreed design moves to `.claude/planning/DESIGNS.md`; an idea leaves this file once
built.

## The Model

- **CC ramps** on a scene (954, 955 open).
- **A clip's list of patterns** (DESIGNS.md); a Repeat Behavior idea may change what Repeat counts; a clip's other pattern by a
  table, thought over on top of it.
- **Shifts** on an instrument, a track and a scene: octave, then scale step, then semitone; then **velocity adjust**
  (DESIGNS.md).
- **Enabled** on a generator and a chain, and on a track and an instrument; **Skip over** on a scene; the song wizard's button
  on the main screen: each a discussion.
- **Drum-kit sequencing**, each its own discussion: a kit-wide accent lane, hit-restarted modulation across tracks, a
  kit grid, rolls with rate and swell, a control track, clip start and length, layering and choke on any instrument.
- **Draws as decks** (questions 54 to 58).

## Export, Import and Playback

- **An offline export of a whole song** through FluidSynth and the built-in synths, mixed together, where no outside MIDI
  device is used; asked whether in stems, a WAV a track, or one mix.
- **An offline video export** through the visualizer, extra-tight timing without the recorder, a visualizer chosen, an accurate
  progress bar.
- **The corpus browser** (a tree by source, genre, composer and work, importing a piece into a song) and a Download / Reinstall
  of the collection, as a later source for the Import Wizard.
- **The remaining visualizer modes**, all but Piano Roll, Spectrum and Cycle, each from the Python's intent.
- **CoreMIDI's -304** (MIDIClientCreate refused): watch whether it returns.
- **The Hue Bridge Pro lighting**: A subject to discuss.

## The Code

- **The song wizard's screens comparison in Rust**, inside llamatron-compare, timed before and after, holding the wizard's
  screens to the Python's frozen ones until its port is done, the one whole-screen comparison left.
- **The Rust's shape**, discussions: ratatui for the UI (a crate needs the user's yes); directory depth and smaller files, the
  UI's implementation split from its presentation; testing (cargo-nextest, snapshots, properties, fakes behind traits, no
  allocation on the audio thread, benchmarks, cargo-deny); style (newtypes for units, enums over strings, invalid states
  unrepresentable, checked conversions, the API naming guidelines, workspace lints); UI organization (one-way data flow,
  domain, UI and derived state apart, overlays on a stack); a thin main.rs; duplication (lookups by name, change_set closures,
  per-plugin matches, near-identical field lists); whether the frontend's design is ideal; too many primitive types or not;
  the Python's outputs kept as compressed data and the comparison moved into cargo test, or not stored at all; the functional
  tests ported; the rules for the Rust and the Python split cleanly; more named `let`s in place of deep nesting.
- **The Rust made more Rust-like** once the Python is gone: no code that only mimics Python (its number mixing, str.format
  templates, PyYAML rules), the generated/ folders made ordinary source, tests that only held the port pruned.
- **Code a person can work on without Claude** (below, under More Ideas), opening with the code maintainability expert's findings
  (DESIGNS.md, "After the song wizard: what the code maintainability expert found"); every test and tool brought over to the
  program's constants.
- **Steps that must go together** made one function: rename and follow, copy and show it, delete and keep the cursor in range,
  add and go to it, swept across the pages.
- **Hand-written caches** audited against the memoization rule.
- **The import order rule** applied to every module with a rule test (asked first); the rule tests' wording in TESTING.md, a new
  rule getting a test only when a break would be silent and harmful.
- **The suite back toward 30 seconds**, the slowest parts split, timings before and after.
- **A row of ifs against constants**: Whether a lookup table would avoid the repeated checks; measured first.
- **FluidSynth vendored** and statically linked by cargo: a discussion.
- **The style plans**: The checkable "reads like a book" rules as tests, the longest function body down to 25 lines.

## The Documents and the Tools

- **Page tests that read the page**: one screen reader in a shared test-support module, which draws the tracker's screen
  at 80x24 and answers as a person reading it (the cursor's line, where a label is drawn, the value beside it, the legend,
  the status line, a dialog's title and choices, the tabs, Arrange's headings and boxed cell), with verbs that act as a
  person does (go to a label by the arrows, open a tab, choose a listed choice, press a key through the tracker); every
  page test converted onto it, none calling a page's `press` or setting its fields; the screen tour's whole-screen
  comparison and its baselines removed, its crash sweep and the key map's walk kept, the song wizard alone still held to
  the Python's frozen screens; the renders' and exports' answers committed in git and changed with
  `--record-approved-export-change`, every example changed since the freeze given llamatron's own (`.claude/rules/TESTING.md`).
  With it, the tests the review found thin: the engine's, the exporters' and the importers' behaviour tested at their own
  layer, the command line's tests through constants and a working folder of their own, and `synth_controls` made faster.
- **The development tools in a crate of their own**: `src/compare/` becomes `src/internal_tools/`, the one crate of
  every tool not for users, building its own program, never the shipped `llamatron`: the comparisons, the screenshots,
  the key map's walk, with the screen tour (`tour.rs`) and the screenshots' drawing (`svg.rs`) moved out of the tracker
  into it as its modules. The scripts in `internal_tools/` build and run it under its new name. With it, the port's
  leftovers go from the shipped program: `W` refuses with a status message until the wizard is back, no page shows a
  Python class's name, and the stray Python folders in `src/` are deleted.
- **The tracker's tables named for what they are**: `src/tracker/src/generated/` becomes `src/tracker/src/tables/`, the
  program's own tables of keys, generator pages, synth defaults and the new set, edited by hand, its documentation
  saying so; the false "generated" banners go, the key bindings are split by page group, each key a `Key::` constant
  and each shown text a strings-crate constant, with a test that no class binds a key twice or shadows an everywhere key.
- **No YAML in strings**: every set a test starts from held as a string becomes a data file in its crate's
  `tests/data/`, named for what it holds; the synth control trials become data structures; the new-set template is
  built in code from the model's types, the tools sharing the one function (`.claude/rules/STYLE.md`).

- **The documents divided by feature** rather than by screen; a documentation expert perhaps.
- **An overhaul of all the documentation** to match the new architecture.
- **At the video tutorial**: Changes to the documents for people proposed first as an exact before and after (1206), and
  DOCS.md's "Who edits them" updated.
- **Skills**: Whether the reply format or the macros should become skills or slash commands.

- **One source for each rule of the code**: one stepping helper for moving through a list, safe on an empty one; the
  constants redeclared locally imported from the schema or the strings crate; whether a track is heard worked out once,
  `Song::is_heard`, real-time playback minding solo as the render does; the lists of sections and settings built from
  the schema rather than kept by hand.
- **Undo recorded only when the set changed**: a cursor move copies nothing, a failed undo says so, timed before and
  after.
- **Checked writes and a lock-free sender**: `set_written` checks a value against its object's settings, at least in
  the tests; a misnamed `{placeholder}` fails a test; the sender thread takes no lock the daemon holds while drum hits
  render.
- **Dead code and comments**: unused text and schema constants removed, the wizard's kept until its port; modules
  `pub(crate)` and the file-wide `allow(dead_code)` dropped, and every function given its comment, crate by crate with
  the lints turned on as each is clean (`.claude/rules/RUST.md`).
- **The command line's `--force`**: exporting a file with values out of range refused unless `--force` is given, as the
  documents describe.
- **Settings pages by field**: each settings page's fields an enumeration rather than numbered ids, and the instrument
  editor split into a module a tab; functions over a hundred lines divided where a reader would name the parts.

## More Ideas

In the order of their priority, the highest first.

- **General MIDI previews in git**: `sh user_scripts/demos_to_midi.sh`'s files, with `output/previews/DEMOS.md` describing
  every demo, checked into git, so that people without a synth can hear the demos.
- **Seeds and track names**: probability rolls and random directions are seeded from the song's seed, the scene and the
  track's name, so renaming a track changes what a song with probability plays; seeding from the track's place would make
  renames safe and reordering unsafe, and either change alters existing renders once. To decide.
- **music_theory: llamatron's musicianship**: A refactor that grows, with later features stacked on it: the musical
  knowledge now spread through the song wizard, the model's values, the munges, the Chords generator and the measuring tools
  gathered into one package, extremely well organized, plain enough that reading it shows what llamatron understands about
  music. The wizard becomes thin: it holds the panels, the person's choices and the plan that turns those choices into
  calls, and writes the result into the set; every musical decision, judging and making alike (writing a melody, a hook, a
  riff, a bass line, a drum part, choosing a voicing or a progression), is the package's. A maker in the package takes the
  random source it is handed, so the wizard's seeds still decide a take, and takes no wizard object, so that the MIDI
  import, generators and later features call the same makers. No explanations or book in the code for now (46): reasons,
  certainty and worked examples stay in Claude's notes (.claude/notes/music_theory/, MUSICIANSHIP_MAP.md), and Claude reads
  the package's chapter on a subject before answering from its own knowledge (53). Two tiers in one package (51 A):
  music_theory/fundamentals, just above math and below the model (pitch classes, intervals, scale shapes and keys, chord
  shapes and Roman numerals, meter and beat strength: pure values that model/values and the render use); the rest above the
  model and below engine, understanding patterns, clips, scenes and songs, a rendered song reaching it as a neutral score so
  that analysis never imports the render; generators may call it, wizards and pages sit above it, and the layer test treats
  the tiers as two layers. The chapters, in reading order (44): harmony, voice_leading, transformations (today's munges as
  named operations, with motif development), melody, hooks, rhythm_and_drums, comping, accompaniment, counterpoint (later
  canon and fugue from a pattern), form (including how patterns evolve between scenes), arrangement, styles, analysis,
  critique. A chapter is made only when real code moves into it or a feature needs it; no utils module; no shape exceptions;
  new class names avoid those taken (ScaleShape, ChordShape, MusicalKey, TheoryScore and the like). What a musician does to
  a pattern moves off Pattern, which keeps storage and editing (52, STYLE.md). Preferences are costs, never refusals, and a
  style can turn any to nothing. The move, each step a commit with every export byte for byte identical, deleting its old
  copy in the same commit (48 A): (1) fundamentals: the octave constant (now in about ten places), scale shapes, chord
  shapes, Roman numerals, with the layer rule; (2) voice leading, timed on the render path; (3) the munges into
  transformations; (4) the wizard's theory, one module per commit (hooks, chord-tone fitting, phrasing, feels, joins), then,
  in a separate commit the user approves, chord_notes fixed to use the real chord quality instead of treating any chord with
  a sharp or flat as major (50 A); (5) the neutral score and the wizard's note dictionaries, one melody engine per commit,
  the riskiest step, since any change in the order of random draws changes every song; (6) the measuring tools' key finding
  and chord matching into analysis; (7) the style templates into music_theory/styles with a schema the package owns,
  separated into what is universal, what is style data and what is the wizard's own choices, the wizard keeping its choices
  and reading the YAML (47 A). It comes before the MIDI import's refinement (the user's order): the import is to divide a
  song into scenes smartly, sort its accompaniment into tracks, and offer to remove drums, add drums or add accompaniment,
  all of which ask this package. To discuss later, each likely its own idea (49 A): a critique report finding problems with
  a suggested repair for each; an accompaniment wizard (a lead in, a bass, pad or drums out); a counterpoint and fugue
  generator from a pattern; comping and vamping generators; an analyze-and-recompose round trip; the tension curve driving a
  controller ramp.
- **Music videos from a Live set's audio, a helper script apart from the tracker**: A spin-off
  mode of the project, a helper script that works differently from the tracker and turns a finished song into a music video
  for YouTube, a `.mov` of a visualizer playing to the song's own audio. It takes two things: the audio that Ableton Live
  renders from the song's Live set, probably AIFF, where the set may have been given any synths and effects in Live, and the
  song's MIDI files, which the script reads so that the visualizer follows the real notes and everything lines up with the
  audio. The Live set has to keep the song's playing time, so that the audio and the MIDI last the same. - **What the video
  shows.** The visualizer alone, full screen, with no scene bar, no clips and no tracker around it. It doesn't open with the
  splash's sine-wave letters; instead something like a "produced by llamatron" that flies in from the left and then fades
  away, its look to be designed. - **Where it lives.** Not in the GUI: a script run from the command line, given the audio
  file and the MIDI files. - **What it would mean for the code.** The visualizer modes (`interface/visualizers/`) already
  draw from what they hear (`interface/visualizers/heard.py`), which the script would feed from the MIDI files by time
  rather than from real-time playback; each frame drawn at a fixed rate, rendered to images rather than to a terminal, and
  joined with the audio into a `.mov` (`ffmpeg`, if installed, or AVFoundation on a Mac). How the visualizer's characters
  and big pixels become video frames, at what resolution, is the main thing to design. - **Undecided.** The audio formats
  taken; how the MIDI files are given (the MIDI (Stems) export, the single file, or the set itself); which visualizer mode,
  or Cycle; the intro's look and length; the video's size and frame rate; and what is done when the audio and the MIDI
  disagree in length.
- **Accents on beats: velocity in grooves**: We should use the time signature information of the arrangement demo to add
  velocity on beats. We should research whether we can automatically use, in a per track setting, some knowledge of time
  signature to maybe auto fill in the velocity numbers, but this can be explored seperately. Claude's note:
  this and "velocity shaping in grooves" are the same feature seen from two sides. A groove already repeats a row of cells
  from the start of the scene, so a second row on a groove, a velocity amount per cell, gives accents on the beats per track
  with no new concept, chosen the way grooves are now. Swing on the classic samplers, drum machines, grooveboxes and step
  sequencers is timing only, and a velocity-only pattern is an accent row rather than a groove, which is why timing came
  first.
- **More ways to munge a pattern**: The user has tried the pattern editor's munge dialog (`M`: reverse after the cursor,
  reverse before it, reverse all, pivot around it, randomize) by hand, so the next step is to think about which other munges
  earn a place in it. Each is a `Pattern` method that rearranges or rewrites the steps in place, like the five there now,
  and the cursor stays on its step. Candidates to weigh, not decisions: rotate the steps left or right by one (the step
  sequencers' and grooveboxes' nudge), invert the degrees around the step under the cursor or around the scale's root,
  transpose every degree by a number of scale steps, double the pattern by repeating it at twice the steps or halve it, thin
  it by dropping every other note or by a probability, swap two halves, and copy one row's values from another pattern.
  Which of them belong in the munge dialog, which are really pattern generators (see "Pattern generators on the Patterns
  page", which already has notes for pattern builders, and "Transforms that enrich a melody") and which want a key of their
  own is the thing to decide.
- **A step that plays only when no other track plays a note then (working title Interleave)**: A new on-or-off row of a
  pattern, working title Interleave, which needs a better name: a step marked in it plays only if no other track plays a
  note at the same moment, drum tracks not counting, so that a bassline fills the gaps of a melody and never clobbers it.
  First evaluate what it costs: the Realizer would have to know every other track's note times before playing the marked
  track, which breaks the habit of playing each clip on its own and may mean a second pass over a scene, or playing the
  marked tracks last against the others' notes; measure the render before and after. Undecided: what "the same moment" means
  (the note's start alone, or any overlap while another note sounds, and a window around it), whether a held note of another
  track blocks a later step, which tracks count (every melodic track, or chosen ones), how it meets generators that move
  notes later in the chain, and its name. A mechanism already exists to build on: a grab step already plays from what
  another track plays. The Realizer plays clips when they are first asked for, so a clip that grabs from a track asks for
  that track's clip, which is played first, and a GrabSource (engine/realizer/grab_source.py) keeps the finished clip's
  notes by when they start; SongRealizer catches grabs that go round in a circle (_grab_circle). The new row could ask the
  same way: before playing a marked track's clip, ask for every other melodic track's clip in the scene, and keep their
  notes by start, and with their ends, for "is a note sounding at this time". Differences to weigh: a grab names one track,
  while this would ask for every other track, so two tracks that both use the row would wait on each other, a circle the
  rule must settle (such as: the row ignores other tracks that also use it); and the cost is every melodic clip of the scene
  played before the marked one, which the render mostly does anyway, so the extra cost may be small. A side discussion at
  the same time: other ways to make counterpoint easier for a bassline, such as moving toward the melody's gaps, contrary
  motion against the melody, or avoiding the melody's note or its octave on a strong beat. Some may not make complete
  musical sense, but they are the same idea of a bass that listens to the melody, and are to be discussed then.
- **The JazzStandards collection in the corpus and the Public Domain Library**: The fetch script for the library gains
  https://github.com/mikeoliphant/JazzStandards, and the Import Wizard's library browser can import from it. Undecided: the
  collection's license and what it holds (chord charts of standards, many of them copyrighted songs, so that the chords may
  be measured and imported while no melody is), checked before it is fetched; how its charts become a song, chords alone or
  with a bass and drums the import writes; and how the browser files it, by composer or by title.
- **A visualizer called Chords**: A visualizer mode named Chords, placed right after Piano Roll and before Spectrum in the
  order the modes step through. Each chord heard while the song plays gets a block with its chord's name written on it, the
  blocks gathering in the order first played from the upper right. When a chord sounds, its block lights up around its edge
  and the light fades out. When the screen is full, the block played longest ago gives its place to the new chord. It helps
  people hear chords while playing tunes. Until the first chord is played it shows "(no chords yet)", centred, so that a
  song without chords never leaves a blank screen. Silent tracks count too; where several instruments play different chords
  at once, each chord shows, lit together. Undecided: whether the blocks name the chord (Am7) or its type (minor seventh),
  whether the numeral shows, and where the chords come from: the heard chords Scene View and the PDF export use, read from
  the clips playing.
- **Live export with audio tracks, and the WAV export's kinds**: The Ableton Live export asks, for each track whose
  instrument plays through FluidSynth or a built-in synth, whether that track goes into the Live set as MIDI or as WAV
  audio, to discuss when it comes up. The WAV export offers what the MIDI export does: a single WAV of the song, stems, a
  WAV for each track, and the clip tree, a WAV for each clip.
- **Pitch bend, and CC smoothing between a pattern's steps**: The user asks for an investigation: whether FluidSynth plays
  pitch bend (it does take MIDI pitch bend, two semitones either way by default, to be confirmed for the sounds llamatron
  uses), what CC smoothing llamatron has, and whether a CC could glide between a pattern's steps, set per instrument
  perhaps, with pitch bend done the same way and switched on or off per instrument. Today llamatron sends no pitch bend at
  all, and the only CC smoothing is Munge's Smooth CCs (`Pattern.smooth_ccs`), which fills a row's blank steps from a
  straight line between two values: a value a step, never between steps. A glide between steps would add events between a
  step's moment and the next, at a rate to be chosen, in the render or in the real-time timeline and every export; questions
  are where the setting lives (the instrument, the track, the row), the curve, how dense the events are, what a DAW does
  with them, and what it costs the render, measured. The ideas "Pitch bend" (a fifth kind of lane, `PB`, sent as pitch bend,
  and the import that leaves it out today) and "Pitch bend as the electronic genres' riser and bass slide" below hold the
  earlier thoughts, and are taken up with this one.
- **A fill pattern for a clip, played over the scene's last bar**: A clip names a second pattern as its fill, and the fill
  plays in place of the clip's pattern at the end of the scene: a fill as long as a bar plays over the last bar, a shorter
  one over the last steps, so a drum fill is written once as its own pattern rather than worked out with draws and
  registers, which stay for anyone who wants them. To decide: whether the fill replaces the pattern's notes where the two
  overlap or plays over them; whether it plays on every pass, on the last pass of the scene only, or on a chance; whether a
  scene can name a fill for every clip; how real-time playback knows the scene is about to end when a scene loops until a
  person moves on; and how Arrange shows that a clip has a fill.
- **Chord types of your own**: A list page, reached like Scales and Grooves, where a person adds a chord type: a name of
  their choosing and its notes as half steps above the root, such as 0 4 12. The chord types are kept in the set, like
  scales, and the Chord dialog lists them after the built-in qualities, so a pattern's Chord row can play them. The MIDI
  import would use one where a shape struck together is named by no built-in quality, interval chord or doubling, rather
  than splitting its notes into tracks, and two songs imported into one set would share a type rather than each bring a
  copy. To decide: how an imported type is named so its sound is plain; whether a type can be renamed or deleted while a
  pattern plays it; how the Chord dialog marks the set's own types; and how an export names the chord. For the code: a
  section of the set like scales, the chord symbols the Chord row accepts read from the built-ins and the set, the Chord
  dialog's quality list, and voices.chord_named in the import.
- **A track's phrase pattern: each note plays a short pattern from that note**: A track names a pattern as its Phrase
  pattern (a setting of the track, not of the instrument, the user's design), and every note the track's clips play starts
  that pattern in the note's place, the phrase's degree 1 landing on the note played: a pattern of 1 3 5 3 played from a
  written D in C major sounds D F A F. One note becomes a figure, so a line of long notes turns into an arpeggiated or
  riffing part, and the figure is written once. To decide: how long the phrase plays (the note's length, cutting the phrase
  short or looping it; or the phrase's own length, running past the note); what a chord does (the phrase from each of its
  notes, from its root, or the phrase's own chord moved); whether a rest in the phrase leaves a gap; how velocity combines
  (the phrase's own velocities scaled by the note's); whether a drum track may have one; how it sits among the track's
  generators (before the chain, as a pattern is played, or as a step of it); and how the pattern editor and the piano roll
  show a clip whose track has a phrase pattern. The Arpeggiator does a part of this with offsets on a grid; a phrase pattern
  is a whole pattern, with its rows, rhythm and gates.
- **MIDI clock sent to a track's device**: The real-time sender sends MIDI clock, 24 pulses to the quarter note, with Start
  and Stop, so that a hardware sequencer or synth can follow llamatron's tempo. Off by default and switched on for each
  track, a setting of the track, since clock confuses some synths, such as an Analog Four. It needs the
  sender to schedule notes with CoreMIDI timestamps, the real-time redesign's stage 3, so that the pulses are steady; the
  clock follows tempo changes and ramps, starts on a launch from silence and stops with Ctrl+T and the corner's stop.
- **Pitch rows and rhythm rows of different lengths**: A pattern's pitch rows (Degree, Octave, Chord and the like) and its
  rhythm rows (the steps that play, Velocity, Gate, Tie) each loop at a length of their own, so that a figure of five
  pitches over a rhythm of eight steps comes round in a new order every pass, as the hardware sequencers' separate track
  lengths do. Each group of rows shows a loop mark where its loop starts again, and the piano roll draws the notes as heard,
  the pitches laid over the rhythm, rather than as written. To decide: which rows go in which group, how a length is set (a
  field on the pattern, or a mark placed on a row), what a clip's repeat and the pattern's length mean when the two loops
  differ, and how Munge and Reconfigure treat the groups.
- **Step input from a MIDI keyboard**: Playing notes on a MIDI keyboard into the pattern editor, one step at a time: each
  key pressed writes its note into the step under the cursor, as a degree of the pattern's scale where it fits, and the
  cursor may move on to the next step by itself, so a line is typed by playing it. A chord held writes a chord. To decide:
  how a note outside the scale is written, whether the step moves on by itself (a setting, the user's thought), which key or
  pedal writes a rest or a tie, and how the keyboard is chosen. It needs MIDI input, which llamatron does not have today: a
  port opened for listening, as the real-time playback opens one for sending, and the CC knob idea would share it.
- **Chords**: ### Grabbing whole chords Today a grab step takes a single note, the chord's root, even when the track it
  grabs from plays a chord. A chord grab feature could let a step take the whole chord. If it comes, it should probably be a
  choice rather than a change, because single-note grabs are what basslines and hocketing need. ### Custom chord types and
  scale types Let a song define its own chord types and scale types, each a new kind of named object kept in the song, like
  scales and arps already are, and then usable anywhere the built-in ones are. A custom chord wouldn't need to be musically
  "right". It's just a shape of notes built from the step's note, such as three power chords stacked in octaves, an octave
  doubling with a note in between, or a cluster. It would be written as half steps above the note, like the named chords
  (`M`, `dom7`) are, or as scale steps, like the numbered ones (`3`, `7`), so that it follows the scale. It would also fix
  most of the problem with The Entertainer described above: Joplin's right hand is mostly a melody note doubled an octave
  down with a note between, a shape no built-in symbol has, so each hand had to be split across three tracks. A custom scale
  type would be one octave of half steps, as `ScaleType` values are, and a named scale could then use it as its type. The
  user noted that a user's scale type is independent of any root, so it's entered as half steps from the root
  rather than as note names, for instance by toggling keys on the Scale page's keyboard drawn from C
  (`interface/tracker/components/keyboard.py`). Things to settle: names have to fit the pattern editor's 5-character chord
  cell and be told apart from the built-in symbols, the chord and scale pickers would need a page for the song's own, and
  renaming or deleting one has to update or refuse its uses, as with everything else. When custom chord types come, the
  Import Wizard (.claude/planning/DESIGNS.md, its step 4) uses them, the user's wish: notes that start and end
  together in a shape no built-in symbol has become a chord of the set's own on the Chord row rather than extra tracks. ###
  African scales Consider adding scale types from African traditions to the built-in list.
  Many of them don't sit on twelve equal half steps: the equiheptatonic scales of the Chopi timbila and of Ugandan and
  Mozambican xylophone music divide the octave into seven roughly equal steps, and the equipentatonic scales of the Gogo and
  much of East Africa into five, so a `ScaleType` built from half steps can only approximate them, and the approximation may
  not sound right without microtuning, which llamatron doesn't do and MIDI only manages with pitch bend or a tuning table in
  the synth. Worth including anyway where a twelve-note approximation is in use already, such as the anhemitonic pentatonic
  shapes common across West Africa and the Ethiopian kiñit (tezeta, bati, ambassel and anchihoye), which are pentatonic
  modes that fit twelve notes. Each would be one octave of half steps, like every `ScaleType`, so adding them is a list
  change plus a page in the scale picker, and the picker's names would need to fit. A microtuning note in the guide would
  say what's approximate.
- **Looping a whole scene, to tweak patterns live**: A way to loop one whole scene in real-time playback, for changing
  patterns by ear as they play. While the loop is set, no clip's follow action runs, so the scene plays round until the loop
  is taken off. A scene set to loop blocks export, which needs a song that ends, and never blocks real-time playback. To
  work out: whether the loop is a setting kept in the set's file or a state of the tracker only; what sets it and takes it
  off, and how Arrange shows it; and how export says which scene blocks it. Asked before,, as a scene that
  loops until another is launched, where a scene's Repeat is a fixed count. To decide with it: whether an export ignores the
  loop and plays the scene's Repeat as it does now, or warns in the export dialog and on the command line, where this idea
  says the loop blocks export. For the code it would be read only by real-time playback and never by `SongRealizer` or the
  exporters. How it sits with a looping clip needs settling first, since a scene whose every clip loops already plays until
  the human starts something else, which stops an export today.
- **Recording in Rust**: Porting the recording tools to Rust. For now llamatron2 records through the shell wrapper script,
  whatever gets it working first, which the user accepts for the time being.
- **Porting the helper scripts to Rust**: Porting the other helper scripts in user_scripts/ and internal_tools/ to Rust,
  which needs a discussion with the user first about which and why.
- **A Delay row: a step's note played early or late**: A row in the pattern editor's Timing section that moves one step's
  note off the grid, earlier or later, by a share of the step, so a single snare can lag behind the beat or a single note
  can push ahead. It differs from Rush and Drag, which are on or off, and from a groove, which moves every step in a place
  of the bar alike. To decide: the unit (a share of the step, ticks, or milliseconds), the range, whether a note moved later
  than the next step is allowed, how the piano roll draws a moved note, and whether the humanize idea shares the render
  work. Every exporter and real-time playback read the moved times; the render already places notes by exact lengths, so a
  step's offset would be one more term there.
- **Pitch bend**: With the MIDI import's CCs. Pitch bend isn't a CC: it's a MIDI message of its
  own, with values from -8192 to 8191, and llamatron has no way to send it, in a pattern, an export or real time, so the
  import leaves it out and counts it. The user doesn't care for pitch bend much in electronic music, so it waits. Before
  it's built, find a good public domain MIDI song that uses pitch bend, for `examples/midi/`, to prove it works by the round
  trip (`py_legacy/internal_tools/test_all_sample_midi_against_import.sh`). Claude offered a fifth kind of lane that a track's CC
  setting names, `PB` say, whose 0 to 127 are sent as pitch bend with 64 as no bend, about 3 cents a level over a bend of
  two semitones; the Live set already has a pitch bend target on every MIDI track (`exporters/ableton_project.py`).
  Once built, the electronic genres use it as a riser and a bass slide.
- **The program built by GitHub Actions**: llamatron and llamatron-backend built for each supported platform on each release
  and attached to it; setup.sh downloads the right ones and checks their checksums, so that no one needs Rust installed.
- **Draws as decks: the professor's review of draws and ideas for them**: The professor's review, kept whole, set aside by
  the user to discuss later. Nothing is decided; the questions at the end (54 to 58) are open. What works: few parts give
  many results (a count-in, accents that turn over, melodies that change each pass, gates made by counting); a draw is
  shared by the whole song, so two tracks drawing from AD pass one sequence between them, randomness the band holds in
  common rather than kept inside each lane, the most original thing here; a step draws once and its Note+=, Vel+= and
  conditions all see that one value, so one value can mean several things at once; resetting on a scene's first play makes
  chance repeatable, so it can make a form; Serial reads as a shuffled deck and Any as a die. What is weak or confusing: (1)
  tracks to the left draw first, so moving a track column changes the music, unseen; (2) "Conditions redraw" is a flag on
  the draw, not the statement, so one statement cannot look while another draws; (3) a silenced step still draws, right but
  hidden, a rest that moves the melody on; (4) a value reaches only pitch, loudness and on or off, never gate, octave,
  probability, ratchet, CC, step size or which pattern plays; (5) the names collide: "draw" is the thing and the act, the
  code says registers, the user says accumulators, Value Min and Max squeeze the slots but do not limit a running result,
  and Note+= does not add up across passes despite its name; (6) the twelve-tone example leads the page; (7) only a scene or
  a step's Reset row can reset, and nothing shuffles, reverses, rotates or changes a deck mid-song. Missing musically:
  changing the form (which clip, which scene next, how many repeats); weighting other than repeating a value; memory (a
  value coming back, a value avoided); coupling between draws; draws read once a bar or a section, where structure lives.
  Ideas, ranked by musical payoff and novelty (cost S days, M a week or two, L more; * the professor would build first, in
  the order 1, 2, 8, 4): *1. Action cards (M to L): a slot holds a verb, not a number: +3, Transpose +5, Invert, Double
  time, Half time, Mute a track, Fill, Thin, Octave up, Ratchet 3, Hold. A step's new row, Play Card AD, beside Reset,
  carries out the drawn card; the card's scope (a step, a pass, a scene) is part of the card. A bass riff with Play Card AD
  on step 1 and a serial deck of plain, plain, octave up, half time, invert, plain comes back changed each bar, every change
  heard once a round. A slot keeps its number or holds a card, so old files load; cards are picked with the existing picker;
  an action wraps something that exists (transpose, Munge's reverse or invert, the step size). Builds on the Use Draws rows,
  Serial, Munge. The foundation for most of the rest. *2. Deal, a discard pile and reshuffle (S to M): a direction that
  deals without replacing; when the strip is empty the deck stops (the parts that read it go quiet) or waits for a
  reshuffle, by a scene setting Reshuffle AD beside Reset Draws or a Reshuffle card in the deck; the Draws page dims used
  slots so the pile shrinks as you watch. A lead deck of eight phrase variations runs out and the lead drops until the
  chorus reshuffles it: the song breathes with the deck. Builds on Reset Draws, Mute When, Serial. *4. Readings with changing lines (M to L): in the spirit of hexagrams, not
  literally: N lines drawn at once (say six), each a two-way choice, each wired to a part of the arrangement (bass plays or
  rests, straight or swung, high register or low, dense or sparse, major or the relative mode, the lead plays or rests);
  each line may be changing, flipping at the next scene or after N bars, so the reading moves into its second reading and
  the music follows: verse one low, swung, without the lead, two lines changing, verse two climbs and the lead comes in. One
  kind of draw, a Readings tab on the Scene page wiring each line to a setting, and a header glyph of six
  short bars. The most original, the most llamatron-like. Builds on Conditional Execution and the scene's reset. *5. Meta
  cards (M after 1): cards acting on decks: Reverse BD, Shuffle BD, BD goes random, Swap AD and BD, Remove this card, Add a
  copy of this card, Rotate CD by 1, Freeze BD for a pass. One conductor deck read once a bar shapes the decks the players
  use: the melody deck goes forward three bars, then Reverse BD runs the tune backward, then Shuffle BD scatters it, the
  notes kept and the order developed, as a motif is. A change holds until a reset brings back the stored strip, so file and
  export stay deterministic. 6. Suits (M): every card has a suit the user names (such as rhythm, harmony, melody, dynamics);
  a track listens to a suit and ignores another suit's value while still using up the draw, so one deck speaks to the whole
  band and each player answers its own suit, a conversation; a suit field per slot and a suit filter per track; answers
  weakness 1 musically. 7. Hands dealt to the band (M): as a scene starts each track is dealt K cards from a shared deck,
  played in order, unshared; with no duplicates, four players and twelve pitch cards give four disjoint motifs that fit like
  a hocket, new each deal. A scene setting "Deal hands from AD, K each"; the Draws page shows each hand. Extends hocket and
  serial. 8. Walk, the real accumulator (S): an Accumulate mode in which each value adds to a running total kept inside
  Value Min and Max by bouncing, wrapping or folding; slots of +1, +1, -2 make a rising line, as in climbing verses. Makes
  "accumulators" literally true. Builds on the range settings. 9. Fate cards (M): a card marked Fated is set aside when
  first dealt and must return at a set later moment (the last scene, or N bars on): the strange chord heard early and again
  at the climax becomes an earned motif. A flag per slot and a fate slot in the timeline. 10. Weights that change (S to M):
  each slot has a weight; a wearing card loses weight each time it is dealt (a fill frequent early grows rare), a ripening
  card gains it (dissonance creeps in toward the end): an arc without writing one. A weight row under the strip and a drift
  amount. 11. Decks that read draws (M): a slot holds an expression (BD+1, -AD, CD*2, the last value AD gave), coupling
  voices: a harmony always the melody's draw plus 2 follows the melody under chance. Reuses the Conditional Execution
  grammar, which already parses AD + BD. 12. Decks that listen (L): a card's value from what has played (the last note's
  degree, the notes this bar, whether the kick sounded), such as the bass answering the lead's highest note a fifth below;
  an echo slot reading from the timeline; needs care, since draws are timed in the render. 13. A performer's hand in real
  time (L): the player is dealt 3 to 5 action cards on screen and presses 1 to 5 to play one at the next bar, a new card
  drawn to refill: a performance as a card game of limited means, the drums dropped only when that card is held. Care with
  undo and saving; the cards played could be logged. 14. Wager cards (M): a card stakes something on a later draw ("if the
  next CD is even, the chorus doubles, else it is skipped"), a statement with a deferred test. 15. A tension pool (M):
  each dealt card adds or removes points from a song-wide pool; past a threshold the next scene gets a forced release card
  (a drop, a breakdown, a key change); form from building tension; a counter statements can test (TENSION > 10). 16. Spreads
  (M, after 3 and 4): positions dealt once a song (past, present, future, or intro, turn, ending), each wired to a section;
  the future card dealt face down, shown as ? until its scene plays. 17. Cursed and blessed cards (M): a card that stays
  with a track for N passes once dealt, a sticky detune for four bars, or a blessing protecting a track from mutes. Small
  fixes to today's draws, whatever is chosen: draw or look chosen per statement; tracks drawing in column order shown on
  screen, with a draw private to each track as an option; the Use Draws cells dimmed on silenced steps that still draw; the
  documents leading with a rhythm or melody example rather than the twelve-tone row. Claude's assessment: the diagnosis is
  sound, and weaknesses 1 and 2 are real usability problems worth fixing whatever else is chosen. Walk and Deal are cheap
  and make "accumulator" and "deck" true. Action cards are the big decision: they turn draws from numbers into a way of
  changing the arrangement, where the user's meta decks and the tarot and I Ching spirit need to go, but what a card may do
  and over what span needs careful design, so that an export stays repeatable.
  Readings are the most original and closest to the I Ching spirit. Suits partly overlap the simpler private draw per track.
  Open questions: 54, record these as one entry or a group (decks with action cards, Deal and meta cards; Walk; oracle
  draws; readings; dealing to the band; fate and wear; decks that read; games with decks), Claude recommending a group; 55,
  a statement choosing "draws" or "looks" in place of the Conditions redraw flag (needs a migration), recommended; 56, a
  remark on the Draws page that tracks draw left to right plus a setting "Shared by the song" or "Each track its own",
  recommended, or the remark only, or nothing; 57, silenced steps' Use Draws cells drawn dim, recommended; 58, docs/DRAWS.md
  opening with a rhythm or melody example and the twelve-tone row lower, the demo left alone, recommended.
- **Code a person can work on without Claude**: A large task, to be considered before any of it is done: make the code as
  readable as it can be for a person with less understanding of it than Claude has, while keeping it fast and easy to
  change, for a future in which no Claude maintains it. The user's three worries: the text UI may be bound too closely to
  Textual; there may be too many constants to keep in one's head; and adding a feature means touching too many places. As a
  measure of the third, adding the Follow Chords generator touched about thirty files: the file format's names, the settings
  class, the two tables of kinds, the set's reader and writer, the renderer, the strings in five modules, the key bindings,
  the page, the list of pages, the tests' sample set and seven test modules, three tools and four documents. To discuss: one
  declaration of a generator from which the tables, the page, the strings' places and the tests' tours are derived; a thin
  layer of llamatron's own between the pages and Textual, so that a page names no Textual class; a written walk-through for
  each common change, such as adding a generator, a setting, a page or a key, kept true by a test; which constants earn
  their names and which are noise; and a way to measure how many files a common change touches, so that progress shows.
  Nothing of it is started.
- **A knob on a MIDI CC that changes what plays**: A MIDI CC from a controller, turned while a song plays, changes something
  in llamatron as a knob does in Live. Two lanes, by what the knob changes (agreed in the real-time redesign): what changes
  no notes, an outgoing CC, a velocity scale, a transpose, a track's mute, is applied by the Realtime Sender Process to each
  event as it goes out, heard within about a millisecond with nothing rendered, through the knob message the sender's
  protocol keeps room for; what changes the notes, a register's value, a generator's setting, a pattern's step, goes to the
  render process, which keeps the latest value and renders the touched scene at most every few milliseconds. Undecided: how
  a knob is mapped to what it changes, on which page, and whether a knob's turns are recorded into the set.
- **A tempo offset for everything playing on Arrange, while playing live**: The user wants to bump the tempo of everything
  playing on Arrange in live mode, up or down, as a tempo offset held on the song for the time being, not written into the
  scenes' or the song's own tempos. To discuss: the keys that bump it and by how much, whether it is saved with the set or
  forgotten when the set closes, how it is shown (beside the clock on the header, for example), how it meets a scene's own
  tempo and a tempo ramp, and whether an export ever hears it. Underneath, the render process would change the clocks of the
  score it holds and the player hand the sender the events from the change on at the new tempo, the way an edit heard at
  once is handed over now.
- **Global patterns: a song's own or the set's**: The user's idea: a pattern normally belongs to one song, and a pattern may
  instead belong to the set, where every song can use it. Today every pattern belongs to the set and every song shares it,
  so this changes the model and the file format; Claude is to discuss its concerns and ideas with the user, with a drawing
  of the list of patterns and of the main screen, before anything is built. It has to be fitted to pattern groups, built
  since, which the Patterns page now lists by. Settled so far for the Patterns page: it lists the global patterns and the
  current song's own, narrowed by the search where one is typed; a column for global patterns is headed GLOBAL and holds a
  solid circle where the pattern is global; the key that makes a pattern global or a song's own again is named for Global; a
  new pattern is the current song's own. A file saved before the change opens with every pattern global, so nothing changes
  in what it means, and every demo and homage with one song keeps its patterns global (`.claude/rules/PRINCIPLES.md`). The
  main screen's Patterns cell counts the current song's own patterns, the global ones and the total, like `3+2=5`; when
  either of the two is zero, the cell shows the one number alone. A pattern that stops being global: a dialog titled "Copy
  Pattern to Songs" lists the songs, each with how many clips of it play the pattern, like `in 8 clips`, with no OK button;
  several songs can be selected and each gets a copy of its own; it shows ten songs at most and scrolls, with a scroll bar
  drawn at the right of the list, since a set may hold fifty songs. Once the copies are made the global pattern is removed,
  and ENTER is refused while no song is marked. Names: each song has names of its own, so two songs may each have a pattern
  of one name, but a global pattern's name and any song's own pattern's name never match; a copy made into a song keeps the
  global pattern's name, which can't clash. Making a pattern global, or renaming one, where that rule would break opens a
  dialog titled "New name required, conflict in N song(s)", holding only the tracker's standard text field, opened on a free
  numbered name, and its keys, ENTER reading "rename/promote"; only a name free everywhere the pattern would be seen is
  accepted. The user wants generators and chains to work exactly as patterns do in all of this, a song's own or global, once
  Claude has shown it understands what that means; open there: a global chain that links a song's own generator, the order
  of the Generators page, and what the pages' columns show.
- **Importing patterns from another llamatron set**: The main screen's Import opens a dialog that chooses between two kinds
  of import. The first is the MIDI import, as today. The second imports patterns from another llamatron set: a file is
  picked, then a list of every pattern of that set is shown, perhaps in three columns, where the patterns wanted are marked.
  The marked patterns all become global patterns of the set that is open, and a name that is taken is renamed by the naming
  rule (`.claude/rules/UX.md`, "Names the tracker makes"). The mockups and what the import means for the rest, such as the
  scales, grooves and generators a pattern leans on, are to be discussed with the user when this is reached. It depends on
  global patterns.
- **Time signatures, what's left**: Time signatures were built: on the song and optionally on a pattern,
  purely graphical in llamatron (bold step numbers on beats, the signature in the editor's header) and metadata in the
  exports (a meta event in every MIDI file, the Live set's control and each Live clip's own signature). Still to think
  through: - **Scenes.** A meter change mid-song would be an optional `time_signature` on a scene, meaning the song's when
  left out, written as a second meta event where the scene starts and into Live's scene settings. It's rare in this music,
  and it needs no migration, so it waits for a song that needs it. - **Bar lines and bar counts, low priority.** Beats have
  bold numbers and a bold double line down their left edge. The first step of each bar could get one more
  mark, a heavier line or a bar count in the header, which would help most in long patterns, where a block of steps may
  start in the middle of a bar. - **Patterns that don't fill a bar.** A pattern shorter or longer than a bar, or one with a
  pickup, starts its count somewhere, which links to the pickups idea.
- **Morphing**: ### More morph types Morphing today only moves notes from one pattern to the other, sweeping in from the
  left, the right or the middle. Other kinds of morph worth exploring would slowly move between the two patterns' other
  settings too, such as averaging velocities, probabilities or CC values across the repeats, rather than only swapping
  notes. ### Morphers as objects Morph strategies could become their own object type, MORPHERS, defined by name with their
  settings like arps and AutoRatchets are, and then picked on a clip in place of today's `morph_style`. The details haven't
  been discussed yet.
- **Songs with very many patterns**: `examples/by_genre/ragtime/entertainer.yml` is a whole piece written eight bars at a
  time, and it has 81 patterns on six tracks over 20 scenes, and had 107 over 38 when its phrases were four bars. That's a
  realistic size for a full composition, and it shows where a plain list of patterns starts to strain: - **Going straight
  from a clip to its morph target or its chain.** `P` (Pattern) opens a clip's pattern from Arrange and the clip page; the
  same could work for its `morph_to` pattern and for its chain. - **Making many patterns at once.** Typing in a long piece
  means making one pattern per phrase per track. Copying a scene's patterns to new names in one step, or naming new patterns
  from their scene and track, would cut that down. - **Size on disk.** The file is about 50 KB and still reads well in a
  diff, so the file format isn't the limit yet. ### The notes a pattern plays, under every step The pattern editor's
  description line says what the step under the cursor plays, which the user likes, and would really like to see for every
  step at once: a blank line under the step grid, then a row in a lighter colour with the actual note each step plays, like
  `C3 E3 G3 -- C4`, lined up under the steps so the eye can read the melody without moving the cursor. The description line
  of the step under the cursor could then go, with that space used for the default a blank cell would get when the cursor is
  on one, such as `Default gate: 1/16`, where a row has a default to show; a blank Note cell has nothing to show, so the
  space stays empty there. What it touches: `PatternDrawing` already works out what one step plays for `describe()`, through
  the current song's scale and the editor's `cell_text`, so the row is that per step, fitted to the same cell width as the
  grid, and scrolling sideways with it, with the lighter colour being `Style.DIM` because the tracker draws with the
  terminal's own colours only. The 80 by 24 budget is the constraint: the grid grows by two lines (the blank one and the
  notes); a drum pattern's row would show the drum note letters and a chord step the chord's name or its lowest note. The
  defaults shown for a blank cell come from `model/schema/defaults.py` and the set's step size, which the Gate row's default
  is. ### A way home, now that pages can jump `P` (Pattern) was the first jump, and it settled what going back means: ESC
  goes back to the page the jump came from, the crumbs show the path taken (`ARRANGE › clip: (scene 1, lead) › pattern:
  tune`), and a page that comes back redraws from the current set and follows renames. What's left to think about: getting
  to the main screen could take many presses of ESC once more jumps exist, so a key that goes straight there may be needed;
  and if a pattern could jump to the clips that use it, the stack could grow without end, so a jump to a page already on the
  stack might go back to it instead of opening it again.
- **Ideas from other trackers**: Look through other trackers for features worth borrowing, the way the step sequencer and
  the mono groovebox have already given llamatron note grab, registers, step directions, CC slides and its arpeggiator. Ones
  worth a look include the leading trackers on the computer, chip trackers, the tracker on the handheld console, and the
  hardware trackers. Things to look for: how they handle long songs and many patterns (see above), effect columns and
  per-step commands, groove and swing, pattern chaining and song order, and how they keep everything reachable from the
  keyboard.
- **Utility wizards for large changes**: Bigger tools for changes too large to make by hand comfortably: utility work like
  renaming a set of patterns, copying a section to a new key, or splitting a long pattern into phrases. The key that opens
  them needs thought. llamatron must not become an AI music generator, so a wizard never decides the music for you. Every
  wizard asks plenty of questions and does only what the answers say, and what it makes is ordinary patterns, tracks and
  scenes that can be edited afterwards. To be explored later. The wizard that makes a starter song in a style is the song
  wizard (`.claude/planning/WIZARD_DESIGNS.md`).
- **Live launching scenes in line with llamatron's**: In llamatron a scene finishes before the next
  starts, and the exported Arrangement View lays the scenes end to end at exactly those lengths. Session View is different:
  launching a scene fires its clips together at the next launch quantization boundary (a bar by default, counted by the time
  signature), each clip then loops on its own, and nothing waits for a scene to finish. So a scene whose length isn't a
  whole number of bars (it lasts as long as its longest non-looping clip) drifts from where the Arrangement put it when
  launched by hand. Two things could help: the Arrange page showing a scene's length in bars and marking one that doesn't
  divide evenly; and writing Live's scene follow actions, which can advance to the next scene after a set time, so that
  Session View plays the set the way llamatron does. The second needs checking against the template and proving in Live, and
  it's the same auto-advance idea as the real-time playback design below, on Live's side.
- **An analyzer that checks a set for problems and makes recommendations**: While designing the
  Harmonizer, a generator that keys off a track it names: deleting that track would set the name to nothing and leave the
  harmonizer doing nothing, which is fine for now, but a set can quietly stop doing what was meant. The idea is an analyzer
  that reads a set and reports such things, with recommendations: a generator naming a track that is gone, a register bound
  to a lane with no CC number, a condition comparing registers nothing changes, an add past a register's limit, a pattern no
  clip plays, a scene that waits forever. What it needs: a list of checks, each a function of the set returning findings in
  the tracker's words, run on demand from a page or the command line, and perhaps on save; some checks overlap the uses and
  corrections the tracker already has (`interface/pages/uses.py`, `model/file/corrections.py`), which it would build on
  rather than repeat. Undecided: where its report shows, whether it can fix what it finds, and which checks come first. The
  user added, while designing Progression: it could flag things that don't make sense, like a progression on a drum track
  (which does nothing), recommend features, and perhaps refactor a song. It also reports on a song and suggests things to
  look at, without changing anything (once the idea of a Metrics Wizard): - how long each scene and the song are, and how
  often each pattern is used, including unused patterns; - each track's range of notes, and notes that fall outside a
  typical instrument's range; - how busy each scene is, in notes per bar for each track; - notes outside the scale, and
  tracks that clash, such as a half step apart on a strong beat; - velocities that never change, or clips much shorter than
  their scene; - how much repeats exactly, which hints at where an Optimizer Wizard could help.
- **Real-time MIDI, what's left**: Real-time playback is built: the Instruments section and the main screen's Real Time
  switch, the Realtime Sender Process, Space on Arrange with every start by hand at the next bar, `L` (Listen) on the clip
  page and in the pattern editor, the lights, the clock and Ctrl+T (`.claude/features/REALTIME_PLAYBACK.md`, "Real-time
  playback"; `.claude/features/REALTIME_PLAYBACK.md`, "Real-time playback"). The exports stay exactly as they were. What the
  user's design still has in it, to do one item at a time: - **More follow actions, like
  Live's.** with the Advance field's "With Scene", "Next" and "Off": Live's "Previous", "First"
  and "Last" could follow, each a value of `FollowAction` that `Player._send_starts` turns into a scene other than the one
  below, with the same Launch together rule when the start arrives. "Any" and "Other", Live's random ones, would take the
  song's seed. Nothing in the format changes but the list of choices. - **Testing over the wire with a receiver**, from the
  user: a small program the tests spin up, which makes itself visible as a MIDI device (a virtual port through
  CoreMIDI's virtual sources on a Mac, or the IAC driver) and records every event with its time, so that
  what the tracker sends over a real port is compared with the MIDI export, every example and demo through it, the timing
  errors reported to the user with Claude's opinion of whether they would sound tight. Today the suite holds the player to
  the export inside the process (`tests/realtime/test_realtime.py`) and the report measures the Realtime Sender Process on
  recording outputs, which open no port. - **MIDI clock**, so that other gear follows, from the same sender. - **The
  timestamped and compiled senders**, kept in reserve from Claude's proposals in case Python ever drifts:
  timestamped output through CoreMIDI or the ALSA sequencer (PortMidi exposes it portably, python-rtmidi doesn't; Windows
  has no such queue), a compiled scheduler in process (a CPython extension, or Rust through PyO3), or a helper program in
  Rust or C fed over a pipe. The Realtime Sender Process measured within 0.11 ms on every event
  (`py_legacy/internal_tools/midi_timing_spike.py`, `py_legacy/internal_tools/midi_spike.sh`), so none is needed yet.
- **Exporting to other DAWs**: Today llamatron exports an Ableton Live set, one MIDI file of the whole song, MIDI stems or a
  folder of MIDI clips. Which other DAWs get a project format of their own is to be decided: for now the stems
  and the single MIDI file are the way into any other DAW, and real-time MIDI will be the other. When one is chosen, a new
  kind is one subclass of `Exporter` (`py_legacy/src/llamatron/exporters/exporter.py`) listed in `py_legacy/src/llamatron/exporters/exports.py`,
  sharing the note timing in `py_legacy/src/llamatron/engine/timing/timing.py`, so it mainly needs to write the format.
- **Tidying away unused patterns**: With the MIDI import, since a bad import is undone by
  deleting its song. Deleting a song offers to delete the patterns that song used and no other song uses, in a question that
  lists them. The Patterns page gets a key that deletes every pattern no song uses, after a confirmation that says how many.
  What it would mean for the code: `uses_of` and the Patterns page's USED count already know which patterns are unused, so
  it's a question after the Songs page's delete and a key on the Patterns page, each one undo step. Undecided: the key's
  letter, and whether the question lists the patterns or only counts them.
- **More ideas from Claude, noted for later**: These came from building the demos. The user chose which to keep. ### Song
  order, given that scenes are already ordered Most trackers have an order list naming sections in the order they play, with
  repeats, so that "A, A, B, B, A" is five short entries rather than twenty copied scenes. The Entertainer demo has 20
  scenes because every repeat is written out. But llamatron's scenes already play in order, top to bottom, so how an order
  list would fit needs thinking about first. It could be a separate list that refers to scenes, scenes could get a way to
  say "play scene 3 again here", or a scene's `repeat` might already cover most of it. Live has its own idea of scenes,
  which matters too. ### Pickups, if they can be intuitive in the pattern A way to write a pickup, the notes before the
  first full bar, as the music has it. Simple Gifts starts with a two-note pickup, which had to be moved to the front of the
  pattern so that it loops cleanly. Only worth doing if it reads naturally in the pattern editor, such as marking where bar
  one starts within a pattern. A clip setting that starts it partway through is the other way. ### Grooves, what's left
  Timing grooves were built, as decided with the user: a `grooves` section of rows of cells, the factory
  grooves, the song's, scene's and track's choices with `false` switching grooving off, applied in the exporters' timing so
  that all four exports groove the same. What's still open: - **Velocity in grooves**: See "Accents on beats: velocity in
  grooves". - **Random timing jitter** in a groove, which would use the song's seed like probability does. -
  **Polyrhythms**: Parts in different meters against each other, such as a track in 7 against 4, and what that means for
  scene lengths. - **Notes off the grid.** A note between two cells, such as a 32nd in a 16th groove, takes the amount of
  the cell it falls in. Live moves such notes towards the groove's positions instead; whether that's wanted can be decided
  when a groove with short notes sounds wrong. - **The last note of a clip.** A note delayed past the end of its clip is cut
  there, as every note is, so a swung last 16th is a little shorter. Letting it run into the next scene would mean clips
  that overlap, which Live doesn't do. ### Sequencer inspiration from the classic samplers, to think about The user wants a
  pass over the best-loved classic samplers (the late-1980s and 1990s models especially) for ideas, once grooves exist:
  their groove and swing patterns and what made the feel famous, note repeat, the 16 levels mode, timing correct and shift
  timing, and any other quirks of their sequencers that a step tracker could borrow, in the spirit of
  `docs/WHY_LLAMATRON.md`. ### (Low priority) Named drum maps Drum patterns name hits by note letter and octave, so a kick
  is "C, octave 1". A map on a drum track, like `kick: C1`, would make drum patterns easier to read. But the user uses a
  separate instrument in Live for each drum track, so it would need testing in a way they don't usually work, and drum maps
  differ between instruments in Live anyway. ### (Low priority) A library of patterns, chains and arps A file of reusable
  parts that any song could copy from, and the base for song templates. The difficulty is keeping it from being confusing in
  the text UI, alongside each song's own patterns and generators.
- **Rendering a Live set, measured**: each track is a copy of the template's track and every shared id is renumbered by
  walking the whole tree; fine for a few tracks, but worth measuring for songs with many tracks and scenes, since the Live
  set is the slowest part of rendering a big song. A faster version goes in only where it is measurably needed, as clear as
  what it replaces.
- **Chords From a Named Scale, and Typed Chords**: Of the chords that leave the scale, now that a step and a progression's
  chord have a Scale, a Quality and Tensions and one Chord dialog. Not built: borrowing from a named scale with a root of
  its own (only a scale type on the clip's root is borrowed); typing a chord as a numeral or a name in the Chord dialog;
  shortcuts for the dominant of the next chord and the tritone substitute; the piano roll's thin lines for a chord's
  tensions.
- **TiMidity as a Second Synthesizer**: The user's idea, to consider. TiMidity supported beside FluidSynth as what makes
  sound with no DAW. When both are installed the tracker asks which to use as it starts; an environment variable sets the
  default and skips the question; when only one is installed there is no question. It means: TiMidity found, started, waited
  for and ended as FluidSynth is; an instrument's device able to name either; the question at startup and the variable that
  answers it; the WAV export and the scripts that make and record the demos choosing the same way; an install script that
  offers it; and the pages on FluidSynth saying so.

- **The website, what's left**: The site builds from `docs/GUIDE.md` and `docs/` with VitePress and is built into
  `output/web_docs/`, which git ignores, and published by `internal_tools/publish_docs.sh`, as the `gh-pages` branch. Still
  to do: - A landing page with a hero section and feature cards, in place of the guide's opening as the front page, which
  would need new text the user writes or confirms. - "Edit this page on GitHub" links, VitePress's `editLink`, pointing at
  each Markdown source. - A logo and a favicon. - Nicer addresses: the pages are named by their files, like
  `/llamatron/PATTERNS`; lower case would need the staging to rename the pages and rewrite the links. - Links from the
  documents to files in the repository, like `examples/by_genre/electronic/edm_density.yml`, are dead on the site and
  ignored (`ignoreDeadLinks`); the staging could point them at the files on GitHub. - The screenshots are light SVGs, which
  look harsh in the site's dark mode. - Mermaid makes VitePress warn of a large bundle; loading it only on the pages with
  diagrams would help. - A look through the site in a browser for anything that renders oddly.
- **Guides on subjects that cross chapters**: Chapters on chaos (registers, binding, conditions, probability, generators,
  Drift, saying chaos suits tame songs too), on harmony (the Harmonizer, the Hocket, Grab, chords, progressions, voice
  leading) and on density (Density, Swell and Articulate), each in `docs/` and in `docs/GUIDE.md`'s table of guides, linking
  the page chapters rather than repeating them, since each thing is described in one chapter only; and a chapter on the
  render pipeline, linked from `developer_docs/ARCHITECTURE.md`, with every stage and its order of precedence.
  `docs/CONCEPTS.md` already covers part of the first three as recipes.
- **Two tutorials from screenshots, for people starting from scratch**: A very easy walk-through for someone who has never
  opened llamatron, built around screenshots of the real tracker: starting a set, writing a simple song of a couple of
  patterns, arranging them in a scene or two, saving, and exporting it as a Live set and as MIDI stems. Then a second, the
  advanced steps on the same song: grooves, chains and generators, registers, grabs, morphs and the rest, one at a time.
  Both are chapters in `docs/` linked from `docs/GUIDE.md`, the user will edit them, and Claude takes the first shot.
  `docs/CONCEPTS.md` is the order to use the pages in, without screenshots, and the tutorials would link to it rather than
  repeat it. How they're written: by what's selected and what's seen, never by counted presses. "Select Patterns from the
  main menu and press ENTER", "on the Song page, select Tempo and type 124", not "go down three steps", because counts break
  the moment a row is added. Keystrokes are named where they help, in the words the legend uses, and every one of them has
  to be kept true as keys change: a check like `tests/rules/test_doc_paths.py`'s, reading the key names the tutorials quote
  against the pages' `keys()`, would keep them honest, and `py_legacy/internal_tools/make_screenshots.py` already regenerates the
  screenshots from the real tracker, so the tutorials' shots join its list and are retaken the same way. The song the
  tutorials build should be a set in `examples/`, so that each step's screenshot comes from a real file and the finished
  song can be loaded to compare.
- **A tips and tricks document, and a FAQ**: A tips and tricks document for ways of working that need no new feature, and a
  FAQ beside it. The first tip to include is pattern categories by naming: a set shares its patterns between every song, so
  the list grows, and naming patterns with a prefix like `leads foo` and `bass foo` groups them, since the Patterns page
  sorts by name with `S` (Sort). The earlier idea of a `category` field with a completing picker is folded into this; a
  filter on the Patterns page can come later if naming isn't enough.
- **Sheet music for the examples, to be discussed**: The user wants to talk about open-source tools that could make sheet
  music of the examples for the documentation website, and wants it only if the result won't look terrible, since many
  examples have a lot of tracks. Nothing is to be built before that talk. Points to bring to it: - Candidate tools: LilyPond
  (engraving from its own text format, the best-looking output, and `examples/midi/` already keeps the Entertainer's
  LilyPond source), MuseScore's command line (MusicXML or MIDI in, PDF or SVG out), and Verovio (MusicXML or MEI in, SVG
  out, small enough to run in the build), with music21 or the MIDI export as the way in. - Ways to keep a score readable:
  one or two chosen tracks only, such as the lead and the bass, named by each set; a lead sheet (the melody with chord
  symbols from the Progression chains) instead of every part; the first scene alone; drums left out or on one line. - What
  the export gives: llamatron already writes MIDI per track (stems) and General MIDI, but notation needs more than MIDI
  holds, such as the key, beams and ties at bar lines, so a tool that quantizes and spells notes well matters. - Where it
  would go: an image under each demo's summary on its genre page, made by the docs build, never by hand.
- **Keyswitches: what the first build left out**: An instrument's Keyswitch Map, a pattern's Keyswitch row and their playing
  are built (.claude/format/FILE_RULES.md, "Instruments"). Left for later, none of it designed: a slot that switches by a
  controller's value, a program change or a MIDI channel rather than a note, to be read from a plugin's own documentation
  and not from memory; a generator naming a slot, as the guitar generators' muted strokes would; whether a ready-made map
  ships for any plugin, which depends on what may be said about a product's layout; and a demo, which waits for the user's
  word.
- **One song per movement, when the Import Wizard brings in a suite or a multi-movement work**: The professor's advice for
  the Import Wizard: a suite or a multi-movement work comes in as one song per movement or dance in one set, since each
  movement has its own tempo, key and form. Waits for a way for a song to go on to the next song of the set when it ends (a
  song advance), which llamatron doesn't have and which would be tiresome to set up by hand; until then the import makes one
  song (23 B).
