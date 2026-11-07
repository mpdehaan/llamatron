# Later ideas

The user's ideas for later, recorded by Claude, with what each one would mean for the code. It's
also where the user asks what they want to do and what would need to change as a result, so each
idea notes its implications: what it touches, what it depends on, and what's still undecided.
Nothing here is finished: an idea is removed once it's built. Ideas are added when the user asks.

Ideas are marked **HIGH PRIORITY** or **low priority** where the user has said so. Everything
else is unranked. Anything marked **In progress**, started but not finished, counts as a
priority without being marked one: when the user asks what to do next, name the unfinished work
first, before any idea that hasn't been started.

## HIGH PRIORITY

### Better Readme

The readme should make sure it showcases the demos prominently.  Link with DEMOS.md in a way
that makes the hyperlink work in GitHub

Make sure every song mentions where it came from or if it is original, and what features it showcases.

Keep the format consistent for each song, keep the demos sorted by name in this file.

The README needs a screenshot so I'll take one and you can add it above the fold after the initial description.

### Demo velocity and time signatures

We should use the time signature information of the arrangement demo to add velocity on beats.
We should research whether we can automatically use, in a per track setting, some knowledge
of time signature to maybe auto fill in the velocity numbers, but this can be explored seperately.

### Modal interchange exploration

There was a suggestion to explore whether there is some way we can explore playing with modal
interchange and jazz techniques, I have no idea where this would fit in most logically. We
can maybe do this as a pattern helper (name TBD) on the pattern page, along with where we might
make some generators for lead patterns and bass patterns and so on

**To discuss: much of this may already be possible.** Claude's look at the code, for the
discussion. Modal interchange borrows chords or notes from a parallel mode, like the minor iv chord
in a major key. What llamatron can already do:

- A step's Chord row can use a named chord, like `m` or `dom7`, which is built in exact half
  steps and can leave the scale, so degree 4 with `m` in C major plays F minor.
- A step's `#/b` row moves a note a half step, so a flat 3, 6 or 7 can be borrowed one note at a
  time.
- A scene can set its own scale, so a whole section can move to the parallel minor or another
  mode.

What it can't do yet: a scale for one track or clip in a scene while the others keep the scene's,
since scales resolve only from the scene and then the song, and the scale chords (`3`, `7` and the
other numbers) always come from the scene's scale, so they can't be borrowed from another mode on
one step. So there may be nothing to build, or only a per-clip scale or a "borrow from" setting on
a step. To be decided in the discussion.

## Suggested order

An order for working through this document, with refactoring first, as the user asked. Each step
comes after the things it depends on. The ordering principles are: discuss before building where
something's still undecided, put structural file changes behind the version number, and build
each feature after the refactoring that makes it cheap.

**Phase 0: decide, and prepare, before changing code**

1. The long-term direction conversation (see "Asking about the long-term direction"). It
   decides which ideas matter most, and so how the refactoring should be shaped.
2. A format version number, needed before any structural change to the file.
3. The first part of the test refactoring: extend `select_field` to rows and dialogs.
   Refactoring means changing pages constantly, so it pays off at once. (The test suite runs in
   parallel now, about 20 seconds, so the faster test loop is done.)

The user doesn't want exact MIDI timing tested for now, so there are no render snapshots. The
safety net for refactoring is the existing tests, including the ones that check each demo
generator against its sources, plus comparing what each demo renders before and after a change
by hand, as a one-off check while refactoring, rather than as a kept test.

**Phase 1: refactoring** (see "Refactoring"). Started on 2026-11-06, in this order: step 5's
new classes first, with the serialization, which is done, then the tracker moved onto them and
step 6's accessor audit, which are still to do. Gates, the Tie row and registers were built in
between.

4. Decide which is the real model of a song. The serialization plan under "Refactoring" answers
   it in favor of the objects, if the user agrees.
5. Eliminate `song_file.py` as a class: every object gets `to_data()` and `from_data()`, the song
   saves and loads itself through them, and the music logic moves into objects with one job
   each, keeping behavior identical.
6. The accessor audit: one class per file, `get_` and `set_` methods with validation in place
   of `_Validated` and attribute access, only where other classes use them, and every page
   change going through `Document` methods.
7. Octave numbering: the song file switches to llamatron's own numbering, starting at 0, with
   the format version going up and the examples converted, and the tracker shows octaves through
   a display setting on the song that defaults to Live's labels (see "Octave numbering" under
   "Other design decisions to revisit").
8. The seed check, which may change random outcomes once, on purpose.

**Phase 2: the HIGH PRIORITY timing changes**

9. Time signatures, with beats in bold.
10. Undo and redo, which is simple once every change goes through `Document`. It could move
    earlier if it's needed while testing songs by hand.

**Phase 3: what a song can express**

11. Transpose on a clip.
12. Pickups, if they can be made intuitive, after gates, ties and time signatures change how
    bars work.
13. Custom chord types and scale types, then inversions, with grabs aware of them, then grabbing
    whole chords.
14. Sections, with their overrides, and the song order list of sections that plays them, which
    together replace the separate song order idea. Unique names (scenes especially) come first,
    and naming copies with numbers can be done at any time, since it's small.
15. Swing and groove: the discussion of what it does to the MIDI first, then building it, after
    gates, since swing moves notes against their cells.

**Phase 4: working with big songs**

16. The many-patterns ideas: filtering, usage counts and going straight from a clip to its
    pattern, with `examples/entertainer_demo.yml` as the test case. Decide what Tab means
    before adding the first jump.
    Profile the same song for performance hot spots at this point (see "Performance hot
    spots"), since big songs are where they show.
    Fix moving through long patterns in the pattern editor here too, or with time signatures,
    since bars may decide how a long pattern is laid out.
17. Looking at other trackers for ideas, before designing the larger features below. This can
    also happen at any time in the background.

**Phase 5: generators, morphing and wizards**

18. More morph types, and morphers as objects.
19. Pattern generators and transforms, as generators or pattern mutators.
20. A wizard framework, starting with the Metrics Wizard, which only reports and changes nothing.
21. The Optimizer Wizard, which keeps a rewrite only if the song renders exactly the same notes.
22. The MIDI import wizard, the hardest, building on the demo generator's approach.

**Phase 6: getting music out**

23. Exporting to Reaper, which is straightforward once the pattern player is separate from the
    file reading. It could move up if trying another DAW soon matters.
24. Real-time preview: a MIDI channel per track, choosing a port, the discussion of Python's
    timing, then the helper program.

**Low priority, whenever it suits:** named drum maps, and the shared library of patterns, chains
and arps.

## Refactoring

### The goal

The long-term goal is very readable, object-oriented code: classes in files of their own,
designed with care, each doing one clear job, and never cryptic or obfuscated. Someone reading
it without AI help should be able to see what each class is for and how the pieces fit. The
earlier readability ideas belong here: moving classes into individual files, sharing behavior
through base classes where several classes repeat the same shape, more small helper methods
with names that say what they do, and code and comments that explain the why, in the order a
reader needs it.

### Rules for every class

- **No class reads or changes another class's data members directly.** Everything goes
  through methods on the class that owns the data.
- **Nobody uses the classes as an API.** llamatron is used through the text UI, so the classes
  are internal and their methods can be renamed or reshaped freely to suit the design.
- **Plain accessor methods, not Python's accessor magic.** Another class changes a member only
  through a method like `set_name(name)`, and reads it only through one like `get_name()`,
  rather than through properties or descriptors, so that what happens is visible where it
  happens, and every setter can validate what it's given. Setters can take sensible defaults,
  like `set_name(name=None)`.
- **Only the accessors that are used.** Getters and setters aren't added for every member
  automatically. A class has only the ones other classes actually call, so its accessors show
  what's part of its contract with the rest of the program.
- **An audit of the whole codebase** to bring every class in line with these rules.

These conflict with how the code works today, so CLAUDE.md will need changing when the audit
happens. `Song`, `Track`, `Scene` and `Clip` use the `_Validated` descriptor so that plain
assignment, like `clip.name = 'x'`, is validated, which is exactly the accessor magic to remove,
and `Note`, `Chord` and `Scale` are dataclasses read by attribute everywhere. The text UI pages
also write into the song's data directly in places, such as the Song page doing
`self.document.data[name] = value`, and those should become methods on `Document`. That also
makes undo, redo and wizards easier, because every change then goes through one place.

### Eliminating song_file.py, with every object saving and loading itself

**In progress.** Done so far: `song_file.py` is gone. Songs load into the composition objects
(`Song.read_file`), which save and load themselves, and `SongRenderer` in
`src/llamatron/playback/` plays them into finished clips. Everything outside the text UI follows
the readability rules in CLAUDE.md (named constants, `MSG_` templates, named helpers and
`__slots__`), including the symbols the format defines: note names are `NoteName` constants and
chord symbols are `ChordSymbol` constants. The grid of finished clips is `ClipGrid` in
`src/llamatron/clip_grid.py`, so `Song` in `composition/song.py` is the only song. Every page
of the tracker now reads the song through `document.song()`, a `Song` built from the document's
data and kept until the next change, and changes it only through `Document` methods, and the
tests do the same (no test touches `document.data`). Still to do: `Document` itself still holds
the file's data and edits it in those methods, so the next step is setters on the composition
objects that share their checks with `from_data`, after which `Document` holds a `Song` and the
data goes away; then the accessor audit, which replaces `_Validated` and attribute access with
`get_` and `set_` methods in `clip_grid.py`, the generators and renderers, and `Note`'s
`midi_number` property.

Decided with the user on 2026-11-06:

- Every saved object extends a `LlamaData` base class, whose `to_data()` and `from_data()` raise
  `NotImplementedError` unless the class defines them, and a test checks that every subclass
  does. `from_data(data, where)` is a class method, and `where` names the place in the file for
  error messages.
- The saved objects are the composition model, in `src/llamatron/composition/`, one class to a
  file, and the music logic goes in `src/llamatron/playback/`.
- What was `Song` in `src/llamatron/song.py`, the grid of finished clips that renderers take, is
  now `ClipGrid` in `src/llamatron/clip_grid.py`, since it maps clips to tracks and scenes. The composition model's song
  becomes `Song`.
- References between objects stay names, looked up when rendering, which keeps binding late.
- The tracker moves onto the objects too: `Document` holds a `Song`, and pages call its methods
  instead of editing the file's plain data, so that the objects are the only model.
- While refactoring, every example song is rendered both ways, and saved, before and after each
  step, and compared byte for byte, in Claude's scratchpad rather than in the project, along
  with the full test suite. AutoRatchet is converted along with everything else.

Object orientation is a design goal throughout. `src/llamatron/song_file.py` used to do three
jobs in about 900 lines: reading and checking the file, most of the music logic, and building
the `Song` objects. It's gone now, split as planned into the composition objects and the pattern
player, with separate classes for grabs, registers and directions (see below). Real-time
preview, exports to other DAWs and the wizards all want the music logic without the file
reading, which that split gives them.

**Every object serializes itself.** Each object in a song, such as a track, has two clear
methods: `to_data()`, which returns its settings as plain data (dictionaries, lists, text and
numbers) in the file format, and `from_data(data)`, which builds the object from that data,
checking it and filling in defaults. The song's `to_data()` and `from_data()` call those of
every object it holds, so a song saves and loads itself, and nothing else knows how any object
is stored. What this means:

- **It settles which model is real.** The objects become the song, and the file's plain data is
  only what they save to. That answers step 4 of the suggested order. Today the tracker edits
  the plain data directly, so the tracker would change to call the objects' methods, which also
  suits undo and the accessor rules.
- **New classes are needed.** Patterns, named scales, arps and chains are plain dictionaries
  today, with no class of their own, so each needs one, with its own `to_data()` and
  `from_data()`.
- **Loading has two passes.** Some settings name other objects, like a clip's `pattern`,
  `grab_track` or `chain`, and a scene's `scale`. Each object can read its own data first, and
  the song can then connect the names, so that a missing name is reported clearly, saying where
  it was used.
- **Errors say where.** `from_data` needs to know where it is in the file, such as "scene 3,
  track bass", so that a problem is reported the way `SongFileError` messages are today.
- **The defaults rule lives in `from_data`.** Each object fills in its own defaults for missing
  settings, so that older files still load, and the song's `from_data` is where the format
  version number is checked.
- **Writing the YAML stays separate.** `to_data()` returns plain data, and
  `src/llamatron/song_writer.py` keeps deciding how it's laid out in the file, such as one list
  per pattern row and settings in braces, so that diffs stay small. YAML is always read with
  `yaml.safe_load`, so that loading never runs code.
- **Each object's round trip can be tested on its own**: `from_data(to_data())` gives back an
  equal object.

### Other design decisions to revisit

- **Note lengths as spacing.** The HIGH PRIORITY gate item at the top is the deepest of these,
  because the editor, the file format and the step logic all assume it. It's best changed
  early, while there are few songs to keep working.
- **Octave numbering, decided.** llamatron's own numbering counts from C0 as MIDI 0. Every DAW
  labels octaves differently, and Live, the only DAW implemented so far, labels MIDI 0 as C-2.
  The user has decided:
  - the song file stores llamatron's own numbering, starting at 0;
  - the tracker shows octaves through a display setting on the song, defaulting to Live's
    labels, since Live is what's output for now;
  - what's rendered doesn't change, since MIDI note numbers are the same whatever the labels.

  What it touches: every `octave` row and the `default_octave` and `default_drum_octave`
  settings in every song file move up by 2, so the examples and the demo generator need
  converting, and the format version number (Phase 0) marks the change, so that an older file
  can be told apart. In the tracker, octaves are typed and shown in the display numbering and
  converted when stored, including the octave limits, which are -2 to 8 in Live's labels today.
  `LIVE_OCTAVE_OFFSET` moves from the file reader to the display setting, and GUIDE.md's
  description of octaves changes. The display setting is a new song setting, with a default, so
  older files still load.
- **Two models of a song.** The tracker edits the file's plain data, and rendering turns that
  into `Song`, `Clip` and `Note` objects, which have become mostly a render target. Decide on
  purpose which is the real model, since undo, wizards and an Optimizer Wizard will all work on
  it.
- **The seed.** There's one global seed in the song. Check how it's used: if probability and
  random directions each draw from one generator in the order things happen while rendering,
  then adding a step early in a song changes every random choice after it, even in other clips.
  If that's a concern, each roll could get a seed derived from its pattern, step and repeat, so
  that changing one part leaves the rest of the song as it was.
- **Chain generators work on rendered notes, not steps.** That keeps binding late, so a chain
  follows scale changes, but a chain's result can never be seen or edited in the tracker, and a
  generator can't think in steps. Worth keeping in mind when designing the pattern generators
  above, which would write steps instead.

## Time signatures

llamatron is going to have time signatures. In the pattern editor, the cells where quarter notes
fall, according to the time signature, should be bold, so that the beat can be seen while
writing. Bold is one of the few styles the text UI allows, along with dim and reverse, so it fits
the design rules. This goes with the HIGH PRIORITY gate and tie items, since equal-width cells
are what make beats line up on screen, and it's in the same step of the suggested order.

To think through:

- **Where a time signature is set.** On the song, with scenes able to change it, the way scales
  work, seems most natural. A pattern could also be written in a time signature of its own.
- **The MIDI files need it too.** The MIDI file, the stems and the clip tree carry no time
  signature today, so a DAW assumes 4/4 for its bar lines. Each should get a time signature meta
  message at the start of every scene whose signature differs from the one before, written the
  way `_Arrangement.tempo_events` writes tempo changes, with the clip tree writing its clip's.
- **Quarter notes or beats.** In 4/4 the quarter notes are the beats. In 6/8 the beats are
  dotted quarters, so bolding quarter notes there wouldn't match how the bar is counted. Whether
  to bold the beats, or the quarter notes as such, needs deciding, and the first beat of each bar
  might want marking differently again, such as a bar number or a rule above the row.
- **Which cells.** With 1/16 cells, every fourth cell starts a quarter note, and with 1/32 cells,
  every eighth. Until gates arrive, steps have their own durations, so a step would be bold when
  it starts on a quarter note, and some quarter notes would fall inside a step.
- **Patterns that don't fill a bar.** A pattern shorter or longer than a bar, or one with a
  pickup, starts its count somewhere. That links to the pickups idea.
- **Directions and morphs.** The bold marks belong to time, not to steps, so when a direction
  plays steps in another order, the marks stay where the beats are.
- **The renderers.** The Live renderer writes a fixed 4/4 today, so it would write the song's
  time signature, and scene changes too, which Live supports on scenes. The MIDI clip files
  would get a time signature event. Tempo stays in quarter notes per minute.
- **The file format.** A new setting, with a default of 4/4 so that older files still load,
  following the defaults rule.

## Chords

### Inversions

A pattern row to invert chords, so a chord can be played with its third or fifth at the bottom.

When this arrives, grabbing has to know about it. Today a grab from a track that plays a chord
takes the chord's lowest note, which works only because chords are built upward from the root, so
the lowest note is always the root. Once a chord can be inverted, its lowest note may be its third
or fifth, and the grab should use the inversion to decide what to take.

### Grabbing whole chords

Today a grab step plays a single note and never a chord, even when the track it grabs from plays
one, and even when the grab step's own Chord row has a symbol. A chord grab feature could let a
step take the whole chord, or build its own chord symbol on the grabbed note, so that a pad could
follow a silent track of roots. If it comes, it should probably be a choice rather than a change,
because single-note grabs are what basslines and hocketing need.

### Custom chord types and scale types

Let a song define its own chord types and scale types, each a new kind of named object kept
in the song, like scales and arps already are, and then usable anywhere the built-in ones are.

A custom chord wouldn't need to be musically "right". It's just a shape of notes built from the
step's note, such as three power chords stacked in octaves, an octave doubling with a note in
between, or a cluster. It would be written as half steps above the note, like the named chords
(`M`, `dom7`) are, or as scale steps, like the numbered ones (`3`, `7`), so that it follows the
scale. It would also fix most of the problem with The Entertainer described above: Joplin's
right hand is mostly a melody note doubled an octave down with a note between, a shape no
built-in symbol has, so each hand had to be split across three tracks.

A custom scale type would be one octave of half steps, as `ScaleType` values are, and a named
scale could then use it as its type. Things to settle: names have to fit the pattern editor's
5-character chord cell and be told apart from the built-in symbols, the chord and scale pickers
would need a page for the song's own, and renaming or deleting one has to update or refuse its
uses, as with everything else.

## Morphing

### More morph types

Morphing today only moves notes from one pattern to the other, sweeping in from the left, the
right or the middle. Other kinds of morph worth exploring would slowly move between the two
patterns' other settings too, such as averaging velocities, probabilities or CC values across the
repeats, rather than only swapping notes.

### Morphers as objects

Morph strategies could become their own object type, MORPHERS, defined by name with their
settings like arps and AutoRatchets are, and then picked on a clip in place of today's
`morph_style`. The details haven't been discussed yet.

## Songs with very many patterns

`examples/entertainer_demo.yml` is a whole piece written four bars at a time, and it has 107
patterns on six tracks over 38 scenes. That's a realistic size for a full composition, and it
shows where a plain list of patterns starts to strain:

- **Finding a pattern.** A flat list of 100 or more names needs scrolling or typing to find one.
  A filter that narrows the list as you type, or jumping to a pattern by its first letters,
  would help most.
- **Seeing what belongs together.** Names like `A 1-4 treble 1` group themselves by section and
  by track only by convention. The list could group or sort by a name's prefix, or by the track
  a pattern is used on, or show only the patterns one track or one scene uses.
- **Knowing where a pattern is used.** With many patterns, it's easy to lose track of which are
  shared, which are used once and which aren't used at all. A column for how many clips use a
  pattern, and a way to list them, would answer that, and would make tidying up safe.
- **Going straight from a clip to its pattern.** From a clip's page, or from a cell on the
  Arrange page, a key that opens that clip's pattern in the pattern editor, without going
  through the pattern list, would save the most steps in a long song. The same could work for
  its `morph_to` pattern, and for its chain. See "What Tab means" below,
  because a jump like this changes what going back means.
- **Making many patterns at once.** Typing in a long piece means making one pattern per phrase
  per track. Copying a scene's patterns to new names in one step, or naming new patterns from
  their scene and track, would cut that down.
- **Size on disk.** The file is about 50 KB and still reads well in a diff, so the file format
  isn't the limit yet.

### Long patterns in the pattern editor

When a pattern has more steps than fit across the screen, the editor wraps them into blocks
stacked down the screen (`steps_per_block` and `body` in `src/llamatron/tui/pattern_editor.py`),
about 10 steps to a block on an 80-column console. But Up and Down only move between the rows of
the block the cursor is in, and from the last row they wrap back to its first row (`move` in the
same file), so the block below can only be reached with Right, a step at a time. The user is
fine with either of two fixes:

- **Scroll sideways instead of wrapping.** Show one block, as wide as the screen, that scrolls
  left and right to follow the cursor, so Up and Down always mean the rows. The top line would
  need to say which steps are showing, like "steps 17-26 of 64", perhaps with a mark at an edge
  when there are more steps that way. It's simple, and works for any length, but only part of a
  long pattern can be seen at once.
- **Keep wrapping, and let Up and Down cross blocks.** Down from a block's last row goes to the
  first row of the block below, on the step in the same column, and Up from the first row goes
  to the last row of the block above. The whole pattern stays visible, but moving up or down then
  changes which step the cursor is on, which could surprise, and the last block is usually
  shorter, so the cursor needs a step to land on when the column below is empty. Today's wrap
  from the last row back to the first would go, except perhaps at the very top and bottom.

Either way, the pattern editor's tests and GUIDE.md change with it. Time signatures (above)
could also shape the choice: blocks, or the sideways scroll, could move a bar at a time, with
the beats in bold lining up from block to block.

### What Tab means, once pages can jump

The user isn't sure about this yet, so it needs thinking about. Should Tab mean "back", to
wherever you just were, rather than "up a level", to the page above?

Today they're the same thing. Every page opens by being pushed onto a stack, and Tab pops it
(`go_back` in `src/llamatron/tui/base.py`), so Tab already returns you to wherever you came from.
But each page can only be reached from the page above it, so where you came from is always the
level above. The breadcrumbs at the top, like `ARRANGE › verse › bass`, describe that same path.

A jump from a clip to its pattern would be the first time back and up differ. The pattern editor
would show `PATTERNS › name` at the top, while Tab would return to the clip, not the Patterns
list. Things to settle:

- **Which one Tab does.** Back is what a jump wants, since you'd usually look at the pattern and
  return to the clip. Up matches the breadcrumbs.
- **The breadcrumbs.** If Tab means back, the top line could show the path you took to get here,
  like `ARRANGE › verse › bass › pattern`, so that it still says where Tab goes.
- **A way home.** Once jumps exist, getting back to the main screen could take many presses of
  Tab, so a key that goes straight to the main screen, or to the page above, may be needed.
- **Jumps that go round.** If a pattern could also jump to the clips that use it, the stack
  could grow without end, so a jump to a page already on the stack might go back to it instead
  of opening it again.
- **Pages that change underneath.** A page you go back to must redraw from the current song, in
  case the jump renamed or deleted what it showed. Pages already redraw when they come back
  (`on_screen_resume`), but a page holding a name that no longer exists would need to handle it.
- **The rules that stay.** Tab never quits, and Q quits only from the main screen, whichever
  meaning Tab gets. GUIDE.md says "Tab goes back", which would need to say which kind.

## Tests with less hard coding

Many of the text UI tests reach a setting by pressing a counted number of keys, like down, down,
enter, which breaks whenever a page gains or reorders a field, and has to be worked out again by
hand each time. The tests should instead ask each page where things are and navigate there, using
the same ordered lists that the page draws from: its fields, its rows and its keys.
`select_field(label)` in `test/test_tui_pages.py` is a start, for settings pages: it finds a
field by its label in the page's own `fields()` and presses up or down as far as needed. The
same idea could cover list rows, pattern editor rows and dialog options, and then the existing
tests could be changed over to it. The aim is tests that a person can read, and change,
without counting key presses.

## Ideas from other trackers

Look through other trackers for features worth borrowing, the way the Cirklon and the Elektron
Monomachine have already given llamatron note grab, registers, step directions, CC slides
and its arpeggiator. Ones worth a look include Renoise, OpenMPT, Furnace and SunVox on the
computer, LSDJ on the Game Boy, and the Polyend Tracker and Dirtywave M8 as hardware. Things to
look for: how they handle long songs and many patterns (see above), effect columns and per-step
commands, groove and swing, pattern chaining and song order, and how they keep everything
reachable from the keyboard.

## Pattern generators on the Patterns page

Tools on the Patterns page that write a new pattern, or fill one in, from a few choices: a
melody, a bassline, a chord progression, a drum beat and so on. They'd be different from today's
generators, which change a clip at render time in a chain: these would write ordinary steps into
a pattern once, which can then be edited by hand like any other. CLAUDE.md already plans for them
in `src/llamatron/generators`, with pattern mutators in `src/llamatron/pattern_mutators`.

Making them intuitive will take some thought, so nothing is decided yet. Questions to settle
first:

- **Where they live.** A key on the Patterns page that makes a new pattern, a key in the pattern
  editor that fills in or rewrites the rows under the cursor, or both.
- **How few choices are enough.** Something like "bassline, 16 steps, follows these chords" is
  easy to pick, but every extra setting makes the dialog harder to use.
- **Trying again.** A generated pattern is rarely right the first time, so generating again with
  another seed, and undoing, should each be one key.
- **Following the song.** Writing degrees rather than notes keeps a generated pattern following
  the scale, as everything else does. A bassline or melody could also take its chords from
  another pattern, the way a grab takes notes from a track.

## Wizards for large changes

Bigger tools, possibly opened with `W`, for changes too large to make by hand comfortably:
starting a song from a template (a set of tracks, scales and empty scenes for a style), or
utility work like renaming a set of patterns, copying a section to a new key, or splitting a
long pattern into phrases. W already saves under a new name on the Song page, so the key
would need some thought.

llamatron must not become an AI music generator, so a wizard never decides the music for you.
Every wizard asks plenty of questions and does only what the answers say, and what it makes is
ordinary patterns, tracks and scenes that can be edited afterwards. To be explored later.

### Style wizards for starter songs

**MEDIUM PRIORITY, and very interesting to the user.** Wizards that make a starter song in a
style, which the user then edits like any other: every pattern, track and scene stays ordinary
and editable. Styles the user mentioned:

- country rock, with options named in the spirit of artists without copying them, like "Neil"
  and "LargeBirds"
- classic metal, and the new wave of British heavy metal
- classical composers' styles
- jazz, in its various modes
- blues, especially 12-bar blues and its variations

The rules:

- It's a fun starting point, not an AI generator. Each wizard asks key questions every time, so
  the user has to make the human choices: how long the song is, which scale to use from a list
  the style suggests, and so on.
- Styles, not songs: nothing copies a real piece's melody or arrangement, so there's no copyright
  problem. A style is things like its chord progressions, rhythms, tempos, scales and form.
- Songs consider key changes where the style has them, such as a modulation up for a last
  chorus, which scenes' own scales can already do.
- Each style needs research before it's written, and styles can be added and improved over time.
- It needs its own package, perhaps `src/llamatron/wizards/`, with one module per style, to keep
  the code clean.

What it touches in the code: wizards would build songs through the composition objects rather
than file data, so this fits best after the tracker moves onto the objects (step 5). It likely
shares code with the pattern generators above, and blues and jazz progressions would want the
scale chords and per-scene scales that already exist. The wizard key is still to be decided (see
above, and the hotkey review).

### A MIDI import wizard

One wizard could import a MIDI file, working out how to cut it into patterns, tracks and
scenes. This could be very hard in general, and may not happen for some time. The generator
that made `examples/entertainer_demo.yml` (`test/demo_sources/make_demos.py`) is a rough first try at
one piano piece. It splits each hand into voices by pitch, because a step holds one note or one
chord symbol, cuts the piece into four-bar phrases, and reuses a pattern wherever a phrase
repeats exactly. The hard parts it shows are guessing where bars and phrases start, splitting
chords that no chord symbol fits, notes held across a phrase's end, choosing a key to write
degrees in, and naming everything. A wizard would ask about each of these rather than guess.

The user's request (2026-11-08): an import on the Song page, or a wizard, that takes the path
to a MIDI file and splits it intelligently into a smart arrangement. It doesn't need to use any
of llamatron's features, just plain patterns, tracks and scenes, but it should make a small
number of scenes rather than one long one, with each MIDI track becoming a track, and it should
identify repeating patterns, as an option, so that a phrase that comes back is one pattern used
in several scenes rather than written out each time. What that needs, roughly: read the file
with `mido`, take the tempo and time signature from it (or ask), choose a step size that fits
the shortest note (or ask), cut the piece at bar lines into phrases of a few bars, which become
the scenes, give each track's phrase a pattern, and merge patterns whose steps come out
identical, exactly or after moving them to the same octave, when the option is on. Overlapping
notes on one track go into voices, as the Entertainer generator does, or into chords where a
chord symbol fits. Everything it can't decide, it asks, in keeping with the wizard rules above.

## Previewing with real-time MIDI

A PREVIEW feature that plays the song, or a clip, out of the computer's MIDI ports in real time,
instead of only rendering files for Live. Python may not keep good enough time for this, so the
idea is a small helper program in a language with good timing, Rust for example, which the
tracker starts and stops. Keeping the number of languages in the project small matters, so this
would be the only one besides Python.

What it would need:

- **Choosing a port.** mido can list the attached MIDI interfaces, so the tracker can offer them
  and remember the choice.
- **A MIDI channel on each track.** At least that, so that each track can reach its own synth.
- **Files to play.** The tracker writes one MIDI file per track into a temporary folder, as the
  clip tree renderer already does per clip, and the helper plays them together. These would be the
  program's first temporary files, since rendering uses none today. The folder should come from
  Python's `tempfile`, so that it's in the system's temporary location, and its location should
  be documented in GUIDE.md. It must be removed when the preview stops, when the tracker quits,
  and on the next start if a crash left one behind.
- **Starting and stopping.** The tracker launches the helper and stops it, and the helper must
  never leave a note stuck on. Before starting and when stopping, it sends a note off (a note
  on with velocity 0) for every note on every channel the song uses, and the All Notes Off and
  All Sound Off controllers (CC 123 and CC 120) too, since some synths only listen to those.
- **Talking it over first.** Whether Python could be good enough after all, with a separate
  process doing nothing but sending, is worth measuring before adding a language. Sending MIDI
  clock, so that other gear follows along, could come later.

## Exporting to other DAWs

Today llamatron renders an Ableton Live set or a folder of MIDI clips. Other DAWs could get
their own export, with Reaper as a good first example because it's inexpensive. Reaper's
project files (`.rpp`) are plain text and documented far better than Live's, which should make
a renderer simpler to write and to test than `AbletonProject` was. A Reaper export would put
each track's clips on its own track as MIDI items, laid end to end as in Live's Arrangement
View, since Reaper has nothing like Session View. Renderers already share their note timing
through `src/llamatron/renderers/timing.py`, so a new one mainly needs to write the format.

### MIDI export with a choice of layout

**Done (2026-11-08):** `M` on the Song page offers one MIDI file, stems and named clips, and
`--to midi`, `--to stems` and `--to cliptree` do the same from the command line, with muted
tracks left out of the first two. What's still to do is in the time signatures section: until
there is one, the MIDI files carry none, so a DAW draws bar lines as if the song were in 4/4,
and the time signature work should write a time signature meta message at the start of each
scene whose signature changes, in `tempo_events`' way, into the song file, the stems and the
clip tree.

The user's idea (2026-11-08): the MIDI export should come in two versions, chosen in a dialog
that opens when the export key is pressed. One is the clip tree as it is now, a file per clip.
The other is one long MIDI file per track, with the scenes laid end to end in order as Live's
Arrangement View lays them, for DAWs that have no session grid. A track that plays nothing in
the first scenes is padded with silence so that every track's file starts at the song's start
and they all line up when dropped into a DAW together. The Live export stays exactly as it is;
this is only about exports to the file system.

Claude's view: worth doing and not large, because every piece exists. The rendered `ClipGrid`
already holds one scene per written-out repeat, with looping clips filled to the scene, so a
track's long file is its clips placed at the scene starts, and a scene it plays nothing in is
just a gap, which costs nothing in MIDI since the next event's delta time covers it. The scene
starts are what `AbletonProject` works out for Arrangement View, so that arithmetic should move
somewhere both can share, such as the grid. Per-scene tempos become tempo meta messages at the
scene starts, as the Live arrangement does with its tempo automation, and every file ends with
an end-of-track at the song's end so the files are the same length. One thing to consider
adding as a third choice: a single multi-track MIDI file (format 1), with a tempo track and one
track per llamatron track, because most DAWs without a session grid (Logic, Reaper, Bitwig,
Cubase) import one such file as aligned tracks with the tempo map in one drop, which is the
surest way to have everything line up; separate files rely on the person dropping each at the
same position. The per-track files are still right for hardware and samplers that take one file.
Without time signatures (see above) a DAW will assume 4/4 for bar lines, which is the same gap
the clip tree has today. The command line would take the new layouts as values of `--to`, and
the Song page's `M` would open the choice dialog, with the help text and `GUIDE.md` updated.

## Asking about the long-term direction

At some point, ask Claude about where the program is heading in the long run, and which
changes made now would make those directions cheaper to reach later. Some ideas here pull in
different directions: real-time preview, exports to other DAWs, wizards and pattern
generators all lean on the song model and renderers in different ways. Deciding early which
of them matter most, and shaping the code for those, could save rewriting parts of it later.

## An Optimizer Wizard

A wizard that takes a song entered in a plain way, such as every note typed out (as a MIDI import
would give), and rewrites it with fewer, more reusable patterns and generators. It should do
this without needing much AI, by searching rather than guessing.

The search would try rewrites like these, each of which can be checked exactly:

- two patterns that are the same become one;
- patterns that differ only by moving along the scale become one pattern plus a transpose,
  where the tracks allow it;
- repeated equal notes become a Ratchet, or an AutoRatchet in a chain;
- a run of notes that walks a chord becomes the chord plus an arpeggiator;
- a passage that repeats becomes a clip with a repeat count.

The method would be a search with a cost, rather than minimax, which is for games against an
opponent. The cost could be something like the number of patterns plus the number of steps, and
the search could be greedy (always take the rewrite that saves most) or a beam or
branch-and-bound search that tries a few paths. The rule that matters most: a rewrite is only
kept if the song still renders exactly the same notes, compared event by event, so the wizard
can never change the music. Like every wizard, it would ask before each kind of change, and
show what it would do.

## A Metrics Wizard, and transforms that enrich a melody

### Metrics

A wizard that reports on a song and suggests things to look at, without changing anything:

- how long each scene and the song are, and how often each pattern is used, including unused
  patterns;
- each track's range of notes, and notes that fall outside a typical instrument's range;
- how busy each scene is, in notes per bar for each track;
- notes outside the scale, and tracks that clash, such as a half step apart on a strong beat;
- velocities that never change, or clips much shorter than their scene;
- how much repeats exactly, which hints at where an Optimizer Wizard could help.

### Transforms

Ways to make a basic melody or part richer, each one a choice the user makes, and repeatable
with a seed:

- passing tones and neighbor tones between melody notes;
- chord extensions, turning triads into sevenths, ninths and more;
- syncopation, swing, and moving notes ahead of the beat;
- ornaments such as trills, turns and grace notes;
- octave doubling, and a harmony line in thirds or sixths;
- reharmonizing a chord progression with substitute chords.

Some of these could be generators that run in a chain at render time, so that the plain pattern
stays as written and the transform can be turned off. Others could be the pattern mutators that
CLAUDE.md already plans for `src/llamatron/pattern_mutators`, which rewrite a pattern's steps
once, so they can be edited afterwards. Either way, nothing is generated unless the user asks,
and what comes out is ordinary patterns and settings.

## More ideas from Claude, noted for later

These came from building the demos. The user chose which to keep.

### Song order, given that scenes are already ordered

Most trackers have an order list naming sections in the order they play, with repeats, so that
"A, A, B, B, A" is five short entries rather than twenty copied scenes. The Entertainer has 38
scenes because every repeat is written out. But llamatron's scenes already play in order, top to
bottom, so how an order list would fit needs thinking about first. It could be a separate list
that refers to scenes, scenes could get a way to say "play scene 3 again here", or a scene's
`repeat` might already cover most of it. Live has its own idea of scenes, which matters too.

### Pickups, if they can be intuitive in the pattern

A way to write a pickup, the notes before the first full bar, as the music has it. Simple Gifts
starts with a two-note pickup, which had to be moved to the front of the pattern so that it loops
cleanly. Only worth doing if it reads naturally in the pattern editor, such as marking where bar
one starts within a pattern. A clip setting that starts it partway through is the other way.

### Transpose on a clip

Today transpose is set on a track and moves every clip on it. A clip's own transpose would let
one pattern play at different pitches in different places on the same track, which is the most
common kind of reuse in songs, and would let an Optimizer Wizard merge many more patterns.

### Undo and redo

The tracker has no general undo yet. Only F and S in the pattern editor undo themselves when
pressed again. Wizards and transforms would make undo much more important. The Document keeps
the song as plain data, so keeping a snapshot after each change would be one simple way.

### Swing and groove, to discuss

A setting that delays every second sixteenth, or a named groove object like the arps, would
make parts feel less mechanical. This is for discussion first: the user wants to understand how
it changes the MIDI that's written before deciding. For example, swing would move notes off the
grid in the rendered MIDI, and whether those notes keep their length or end on time changes how
they sound. It would also affect how CC values, glides and grabs line up with the moved notes.

### A format version number

A version number in the song file, like `format: 1`. Defaults already let older files load after
small additions. A version number would let a newer program say clearly when a file comes from a
structurally different version, instead of failing on an unknown key, and would mark the point
where the gate change above happens.

### Snapshots of the demos' renders (not for now)

Keeping each demo's rendered notes as data files and comparing against them. The user doesn't
want exact MIDI timing tested for now, so this isn't planned. It's kept here in case it's wanted
later, and Claude should advise on setting it up if it is.

### Named drum maps (low priority)

**Low priority.** Drum patterns name hits by note letter and octave, so a kick is "C, octave 1".
A map on a drum track, like `kick: C1`, would make drum patterns easier to read. But the user
uses a separate instrument in Live for each drum track, so it would need testing in a way they
don't usually work, and drum maps differ between instruments in Live anyway.

### A library of patterns, chains and arps (low priority)

**Low priority.** A file of reusable parts that any song could copy from, and the base for song
templates. The difficulty is keeping it from being confusing in the text UI, alongside each
song's own patterns and generators.

## Performance hot spots

Check where the code spends its time, and look for ways to make it more efficient, measuring
first with Python's profiler (`python -m cProfile`) on a large song like
`examples/entertainer_demo.yml`, so that effort goes where it counts. Candidates noticed so far,
none of them measured in detail yet:

- **Estimating the song after every change.** The tracker shows how long the song and each
  scene last, and `Document.changed()` throws the estimate away after every edit, so the whole
  song is built again for the next screen. For The Entertainer that takes about 0.1 seconds, and
  building it fully about 0.2, so typing in a long song could start to feel slow. Estimating
  only the scenes that changed, or after typing pauses, would fix that.
- **Grabs search from the start.** A grab looks up what the other track most recently started
  by going through every earlier note each time, so a long clip grabbing from a long clip takes
  time that grows with the square of its length. A binary search (`bisect`) over the sorted
  start times would make each lookup quick.
- **Building clips more than once.** The song builder remembers clips it has built, but the
  length of a scene builds clips without grabs separately from the clips that are played, so
  some are built twice.
- **The test suite.** About 110 seconds, nearly all in the text UI tests, which is covered by
  "A faster test loop" above.
- **Rendering a Live set.** Each track is a deep copy of the template's track, and every
  shared id is renumbered by walking the whole tree. That's fine for a few tracks, but worth
  measuring for songs with many tracks and scenes.

Efficiency shouldn't cost readability, which matters more here: a faster version only goes in
where it's measurably needed, and stays as clear as what it replaces.

## Sections: groups of scenes, with their own overrides

Group scenes into sections, so that a long piece, such as a large classical performance in
several movements, stays manageable in the tracker. A section is a named run of scenes in
order, like the verse, the chorus, or a movement, and it can also change how its scenes play,
so a section can be played again in a different key or with other changes. By default every
song has one section holding all its scenes, so every song written so far just has one
section, and nothing about it changes.

The user suggested it might be called a Stanza. Claude's suggestion is "Section", which says what
it is more plainly. A classical piece might call
its sections movements, which a section's name can say.

### What a section could override

These are Claude's suggestions, to be decided. Each resolves at render, like scales do today,
so binding stays as late as possible, and the order would be clip, then scene, then section,
then song:

- **Key.** The section's scale, so that playing it again in G major moves every degree.
- **Transpose.** Moving every track along the scale, on top of each track's own transpose.
- **Tempo.** Its own tempo, or a ramp across the section, as scenes have.
- **Dynamics.** Scaling every velocity, like playing the whole section softer, from pp to ff.
- **Which tracks play.** Muting tracks for the section, to thin it out the second time.
- **Seed.** A different seed, so that probability and random directions give a new take.
- **Generators.** Swapping one arp or chain for another throughout, like a busier arpeggio on
  the repeat.
- **Time signature,** once time signatures exist.

### Playing a section again with changes

Repeating a section with different settings is where sections meet the song order idea. A song
could have a list of section entries in play order, where each entry names a section and can
override its settings, like `A`, `A` in G major, `B`, `A` softer. The scenes stay in order
inside each section, which answers the open question in "Song order, given that scenes are
already ordered": the order list arranges sections, not scenes.

### What it touches

- **The file format.** Following the inline rule, sections would hold their scenes inside
  them, each with its settings, which is a structural change for the format version number. A
  file without sections loads as one section holding all its scenes, by the defaults rule.
- **The Arrange page.** Scenes grouped under section headings, which could fold away, with keys
  to jump between sections, and a section's settings page.
- **Organizing patterns.** Patterns could be grouped by section too, so that the pattern list
  shows only a section's patterns, and names like `A 1-4 treble 1` in The Entertainer wouldn't
  need the section in them. But that conflicts with names being unique across the song (see
  "Every object has a unique name" below), so whether a pattern belongs to a section, or is
  only tagged or filtered by one, needs deciding.
- **Live.** Session View has no sections. Playing a section again with a different key needs
  new clips, so each section entry would become its own run of scenes in the Live set. In
  Arrangement View, Live's locators could mark where each section starts.
- **The many-patterns ideas,** which sections would help with, and The Entertainer, whose
  strains (Intro, A, B, C trio, D) are exactly sections, with the trio in another key.

## Naming copies with numbers

When something is copied, the copy should take the original's name with a number after it,
choosing the first number that isn't already used: copying `bass` gives `bass 2`, then `bass 3`.
Copying `bass 2` should also give the next free number, `bass 3`, rather than `bass 2 2`, so a
number already at the end of the name is counted up from. Today copies are called `bass copy`,
with a number only when that's taken, so copying a copy gives `bass copy copy`. The user asked
for this for patterns, and it makes sense for everything that can be copied: tracks, scales,
arps, AutoRatchets, chains and scenes all go through `unique_name` in
`src/llamatron/tui/document.py` today, so changing it there changes them all.

To think about: a name that ends in a number for another reason, like `verse 1` meaning the
first verse, would become `verse 2` when copied, which is probably what's wanted anyway.

## Every object has a unique name

All objects must have unique names. Patterns, tracks, scales, arps, AutoRatchets and chains
already do, within each kind, because the file stores them by name. The exception is scenes:
their names are optional and can repeat, which is why `Song`, `Track` and `Scene` have
separate ids today. Making this a rule means:

- **Scenes always get a name,** and a unique one. A new scene already gets a name like
  `scene 3`, so mostly this means refusing duplicates, and naming the unnamed scenes in older
  files when they load, by the defaults rule.
- **Unique within a kind, or across all kinds?** A pattern and a chain both called `bass` don't
  clash today, because every reference says what kind it names. Unique within each kind is
  probably enough, but this needs deciding, and sections may change the answer if patterns
  belong to sections.
- **Ids may become unnecessary.** With unique scene names, the ids on `Track` and `Scene`,
  which exist only because names could repeat, could perhaps go, and the clip tree's file names,
  which use ids, could use names instead.

## The grab_demo.yml doesn't make a good song

The grab_demo.yml should take the original melody and not have different people come in at
different times, it is just like four voices and they alternate singing notes so voice1 sings
note1, voice2 does voice2, and so on.  The full "grab track" voice should be silent but
music should start immediately with all voices active for the full track.

## Arpeggiator demo notes

The arp demo is good in the first section and then halfway into the synthwave section, but the
rest of the demo should be dropped

A lot of the other demos are EXCELLENT

## Basic Classical Demo

This is pachebel's cannon so rename it pachebel.yml

## Other renames

The arrangement_demo is the wellerman so rename it wellerman.yml

## Original demos and names and redundancy

The minimal techno example seems unneeded now that we have the morph demo, maybe rename the morph
demo to minimal_morph.yml. (acid_techno was replaced by `registers_demo.yml`, and retro_chill was
rewritten on 2026-11-07 as an original piece using ties, registers, grabs, a morph, a CC slide, a
scene scale change and a tempo ramp.)

## File protect

The song should have a protect option that allows it to be changed but not saved, so the demos
can be protected and not accidentally overwritten.  You should be able to turn off the protec:wqt
toggle and it should default to off, except for all the content that is included in the repo.

## Reviewing every hotkey in the text UI

Review the letter keys on every page of the text UI, to see whether any could be more logical,
and only change them if it's warranted. This needs discussing before anything changes. Making
one key more logical can mean moving another to free its letter, so the review should look at
every page together. Each page lists its keys in its `keys()` method, which is also what draws
them, so that's the complete list to work from.

Things already worth a look:

- **The same letter meaning different things on different pages.** `S` opens the Song page from
  the main screen, saves on the Song page, and swaps both sides of the cursor in the pattern
  editor. `D` opens the description on the Song page, and moves things down in lists.
- **Letters that are text in some places.** On a drum pattern's Note row, `A` and `F` type note
  letters, so the editor's `A` (change rows) and `F` (flip) aren't available there.
- **Letters chosen because the obvious one was taken.** In the pattern editor, `R` resizes and `O`
  was used for an older feature, and the new step size key is `E`, because `S` (swap) was taken.
- **Whether every page offers the same key for the same kind of action,** such as renaming,
  copying, deleting and moving up or down, wherever those apply.

## A Skip row

A pattern row that skips a step, with a probability, so that a pattern can be copied and made to
skip a step now and then. A skip is not a rest: a rest still takes its step's time in silence,
while a skip leaps straight ahead to the next step, so the steps after it come sooner and the
pass is shorter. Things to settle: what a skipped step's CC values and register changes do
(probably nothing, since the step isn't played), how a skip combines with play directions, and
how a pass that's shorter than its pattern fits a scene's length, since every pass lasts exactly
steps times step size today. Probability would be rolled from the song's seed, like the other
probabilities, so a render is still always the same.

## Euclidean sequencing

Evaluate whether llamatron can already do Euclidean rhythms, which spread a number of hits as
evenly as possible across a number of steps (like 3 hits in 8 steps, which gives the tresillo), or
whether it needs a feature. Today a Euclidean rhythm can be typed by hand into a pattern, since
steps are now all the same length, and a pattern's play direction and repeats work on it as on
any other. What's missing is a way to make one without working it out: perhaps a pattern
generator on the Patterns page (see "Pattern generators on the Patterns page") that fills a row
from hits, steps and a rotation, or a chain generator that does it at render time. To be decided.

## Features the demos underuse

Assess whether any features are used little or not at all in `examples/`, and so may need new
demos. To check when it's done: which settings and rows each example song uses, across chains,
arps, AutoRatchets, morphs, grabs, directions, CC rows and slides, ratchet offsets, transpose,
mute, tempo ramps, scene scales, gates and dots, and registers once they're built. Each demo
teaches one feature (see `examples/DEMOS.md`), so a feature without one is a candidate for a new
demo or for a scene in an existing one.

## Risers, horns and filter sweeps, with smooth automation

Techno often has risers and horn-like swells: a long sustained note while its loudness, filter or
another sound setting moves underneath it. Filter sweeps are the same idea on any sound. Earlier
we talked about how the Elektron Monomachine's parameter locks work (a value set on a step, as
other gear does too), and llamatron's CC rows and Slide already work that way. What needs making
sure of is that when MIDI automation is drawn, the transitions are smooth, not stepped. This may
need a test, and the user checking the result in Ableton Live.

What the code does today, and what it means for this:

- **Velocity can't change during a note.** In MIDI, velocity is sent once, when a note starts,
  so a held note can't swell by velocity. A riser on one long note needs a CC instead, such as
  CC 11 (expression), CC 7 (volume) or a filter cutoff the synth listens to, set in the track's
  `cc` numbers. Velocity, and the registers, can only change from note to note.
  The GUIDE should say so where risers come up.
- **Long notes:** a gate can now be up to 4 whole notes, but it's cut at the end of the
  pattern, so a riser longer than one pattern needs the Tie row, or a long pattern.
- **Slides:** a step with `slide` ramps each CC value to that lane's next value. Live gets two
  envelope points and draws a straight line between them, which is smooth. The `.mid` files get
  a value every `SLIDE_STEP`, which is stepped at a fine grain. Things to check: whether
  `SLIDE_STEP` is fine enough to sound smooth on a slow sweep, since a CC only has 128 values
  anyway; what a slide does when the lane has no later value in the pattern, and across the
  end of a pass into the next repeat; and the hold points (a held value gets a second point at
  the moment of the next one), which have never been confirmed in Live.
- **Shapes:** Live draws straight lines, so a riser that should curve, like an exponential
  filter sweep, would need several points or Live's curved segments. The curve format in a
  `.als` isn't known yet, so that would mean saving a set from Live with a curve and reading it.
- **Testing:** a test can check that the envelope points and the `.mid` control changes are
  where they should be and move in one direction without jumps, but only listening in Live
  proves the result is smooth. A riser scene in a demo would give the user something to check.

## Grouping the main screen's pages

The main screen lists every page in one column: Song, Patterns, Tracks, Chains, Generators,
Scales, Arrange and Quit, with Registers about to join them. The user wants to think about
splitting it into groups with a blank line between them: Song on its own, then the most common
pages, then the more advanced ones, like Registers and the wizards when they come, together.

Which page goes in which group is still to decide. One possibility is Song; then Patterns,
Tracks, Arrange and Scales; then Chains, Generators and Registers; then Quit. In the code,
`MainPage.body` in `src/llamatron/tui/pages.py` draws one line for each of `keys()`, so the groups
could be a small list of where the gaps go, and the order of `keys()` would follow the groups.
The keys stay listed once in `keys()`, as the rule for every page requires, and the test that
every key is shown still applies. It's the main screen of the hotkey review too, so the two could
be done together.

## Moving the help text into help.py

The user wants every page's help text moved into one module, perhaps `src/llamatron/tui/help.py`,
as multi-line string constants, so that help can be edited by hand easily and safely, without
touching code or risking breaking it.

Today each of the 22 pages and dialogs that have help keeps its help as a `HELP` tuple of lines on its class, with `''` for
a blank line, and `Page.show_help` in `src/llamatron/tui/base.py` shows them in a dialog that
wraps each line. Things the move would touch:

- Each constant would be a triple-quoted string, like `PATTERN_EDITOR_HELP = """..."""`, and each
  page would say `HELP = PATTERN_EDITOR_HELP`. Hand-written line breaks inside a paragraph would
  need joining before wrapping, so the rule would be that a blank line starts a new paragraph
  and other line breaks are only for editing. `textwrap.dedent` keeps the indentation in the file
  from showing.
- The test that every page's help fits an 80 by 24 console stays, and runs on the new text, so a
  hand edit that makes help too long fails a test rather than spilling off the screen.
- The guide (`GUIDE.md`) and the help say many of the same things, which is a separate question:
  one could be built from the other someday, but the user edits `GUIDE.md` by hand.
- The format strings in help that name keys or values could use the constants too, but plain text
  is easier to edit, so that's a choice to make when it's done.

## Tests that check shown text through the program's constants

**A rule from the user, with the refactoring still to do.** When a test checks text the program
shows, like a row label (`'│ Degree'`), a key's name, a page's title or a message, it should import
the program's constant for it, like `ROW_LABELS[Row.DEGREE]` or `MSG_NO_SUCH_SCALE`, instead of
writing the words out again. Then renaming something in the program changes the tests with it,
rather than breaking them. CLAUDE.md states the rule, and new tests follow it.

What the refactoring involves:

- The text UI doesn't have constants for most of what it shows yet. Labels, key descriptions,
  field names, status messages and dialog titles are mostly written inline in
  `src/llamatron/tui/`, which is still on `test_slots.py`'s NOT_YET_CONVERTED list and hasn't had
  the constants pass the rest of the program had. So the TUI needs its constants first, page by
  page, which fits the planned move of the tracker onto the composition objects (step 5).
- Then the tests, mostly `test_tui_pages.py`, `test_tui_more.py` and `test_tui_document.py`, swap
  their literal strings for those constants, along with the drawing they wrap them in, like the
  `│` before a row label, which can be a helper in the test file.
- Messages from the non-TUI code are already `MSG_` constants, so tests of song files and
  rendering can switch over straight away, with `assert_refused`-style checks comparing against
  a filled-in template or its fixed part.
- It goes with the other test rules: format strings in tests as constants, one constant per
  line, and limits taken from the program (see CLAUDE.md).

## Refactoring the tests to the program's style rules

**Deferred by the user on 2026-11-06.** The tests are held to the same style rules as the
program (see CLAUDE.md), and new tests follow them, but most existing tests were written before
the rules and still need refactoring:

- **Format strings and messages as constants.** Tests build many strings inline, with f-strings
  and `.format`, like `f'« {item.shown_label()} »'`. Each should be a named constant at the top of
  its test file, or in a shared test module when several files use it.
- **Limits and meaningful numbers named.** Literals like `128` for "just past the top" should
  come from the program's constants (`MAX_REGISTER_VALUE + 1`), and a number that means
  something, like a register's maximum, should be a named variable, so that two 3s that mean
  different things can't be confused. `test/test_registers.py` is an example of the style.
- **Shown text through the program's constants**, as in "Tests that check shown text through the
  program's constants" above, which first needs the text UI to have those constants.
- **Demo tests read from the YAML.** A test of a demo checks values it reads from the demo's
  file, not values written into the test, so that hand edits to a demo don't break it.
- **One constant per line.** About 44 places define several constants on one line with tuple
  syntax, like `MIN_PROBABILITY, MAX_PROBABILITY = 0, 100`, mostly in `src/` but some in tests.
  The rule is new, so these need splitting too, in the program as well as the tests.

It's mechanical but wide: the text UI tests alone are thousands of lines. Doing it a test file at
a time, with the full suite passing after each, keeps it safe, and it fits with the earlier note
on making the tests less hard-coded.

## The Registers page as a grid

The Registers page (`R` on the main screen) lists sixteen settings in one column: AX default, AX
minimum, AX maximum, AX wraps, then the same for BX, CX and DX. The user wants it drawn as a grid
like the pattern editor's instead, with the registers' names, AX, BX, CX and DX, across the top
and one row for each kind of setting down the side: default, minimum, maximum and wraps. Each
value is then a cell, four columns by four rows, which reads at a glance and is much shorter.

What it touches in the code: `RegistersPage` in `src/llamatron/tui/registers_page.py` is a
`FieldPage`, a column of `Field`s, so it would become a page that draws its own grid, with a
cursor that moves in both directions like the pattern editor's, and the keys depending on the
row under the cursor: digits, `+` and `-`, `Enter` and `Bksp` on the number rows, and `Space` or
`Enter` on the wraps row. The grid drawing in `PatternEditor.block_lines` could be shared, since
it's the same box characters and reverse-video cursor. `Document.set_register_setting` and the
refusal messages stay as they are, and `test_tui_pages.TestRegistersPage` would change with the
keys. The help text would need rewriting for the new keys.
