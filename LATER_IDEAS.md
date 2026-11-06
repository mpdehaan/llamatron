# Later ideas

The user's ideas for later, recorded by Claude, with what each one would mean for the code. It's
also where the user asks what they want to do and what would need to change as a result, so each
idea notes its implications: what it touches, what it depends on, and what's still undecided.
Nothing here is built or fully agreed yet. Ideas are added when the user asks.

Ideas are marked **HIGH PRIORITY** or **low priority** where the user has said so. Everything
else is unranked.

## HIGH PRIORITY

### Note lengths as gates

**Done, in version 1.0.5.** Every step of a pattern now lasts its step size (`step_size`, set
on the song and optionally on a pattern, replacing `granularity` and `default_length`), and a
step's `gate` says how long its note sounds, with a `dot` row for dotted and triplet gates. A
gate can run past later steps, up to the end of the pattern. Every example was converted, and
renders exactly as before, except the scenes that play in a direction, which the user accepted.
What follows is the original note. The user's intent was that Granularity sets the width of each cell in the
pattern editor, and so how far apart steps and rests are, while a note's length is its gate:
how long the note sounds, which can be shorter than its cell. Today it works the other way. Each
step's Duration is both how long its note sounds and how far it is to the next step, so a short
note needs a rest step after it. CLAUDE.md describes the current way as deliberate ("steps aren't
fixed slices of time"), so that rule changes with this.

The demos show the cost. The staccato theme of In the Hall of the Mountain King had to be
written as plain legato eighths, and The Entertainer needed a rest step after every note that
doesn't fill its space.

To think through before building it:

- **Existing files.** Songs written today use Duration as spacing. They'd need to keep working,
  which makes this a structural change of the kind the format version number (below) is for.
- **Notes longer than their cell.** If a gate can be longer than the cell, notes overlap, and a
  track plays more than one note at once. Whether that's allowed, cut at the next note, or
  handled by the tie row needs deciding.
- **Everything that works on steps.** Ratchet would split the cell or the gate. Glide runs a
  note into the next one. Directions, `rhythm_from`, morphing and grabs all assume a step's
  length today, and arpeggiators and AutoRatchets fill a note's length.
- **The pattern editor.** Cells of equal width make bars visible, which the editor deliberately
  doesn't draw today, so the screen could change a lot.
- **The renderers.** Timing comes from `src/llamatron/renderers/timing.py` for both renderers,
  so the change would be made in one place there.

### A Tie row

**HIGH PRIORITY, and smaller now.** Gates already hold a note across steps within a pattern, so a
tie is only needed to carry a note across the end of a pattern, into the next repeat or clip,
which gates deliberately don't do. A toggle row on the editor's normal rows, the main page, that carries a note
on into the next step instead of playing it again, and across the end of a pattern into the
next clip. The Entertainer needed it all through: a note held over the end of a four-bar phrase
is cut there and played again. With equal cells, a tie also makes a long note out of several
cells, which could make a separate gate length less needed. The two ideas have to be thought
through together.

To think about: what a tie does into a rest or a different pitch, ties across repeats and
loops, ties into a clip on another scene, and how ties interact with ratchets, directions,
morphs and grabs.

### Scene names

Ableton clips should use the name of the pattern, not the name of the scene.  Ableton scenes
should keep the scene names.

### Demo velocity and time signatures

We should use the time signature information of the arrangement demo to add velocity on beats.
We should research whether we can automatically use, in a per track setting, some knowledge
of time signature to maybe auto fill in the velocity numbers, but this can be explored seperately.

### Modal interchange exploration

There was a suggestion to explore whether there is some way we can explore playing with modal
interchange and jazz techniques, I have no idea where this would fit in most logically. We
can maybe do this as a pattern helper (name TBD) on the pattern page, along with where we might
make some generators for lead patterns and bass patterns and so on

## Suggested order

An order for working through this document, with refactoring first, as the user asked. Each step
comes after the things it depends on. The ordering principles are: discuss before building where
something's still undecided, put structural file changes behind the version number, and build
each feature after the refactoring that makes it cheap.

**Phase 0: decide, and prepare, before changing code**

1. The long-term direction conversation (see "Asking about the long-term direction"). It
   decides which ideas matter most, and so how the refactoring should be shaped.
2. A format version number, needed before any structural change to the file.
3. A faster test loop, and the first part of the test refactoring: split out the slow text UI
   tests, and extend `select_field` to rows and dialogs. Refactoring means running tests
   constantly and changing pages, so both pay off at once.

The user doesn't want exact MIDI timing tested for now, so there are no render snapshots. The
safety net for refactoring is the existing tests, including the ones that check each demo
generator against its sources, plus comparing what each demo renders before and after a change
by hand, as a one-off check while refactoring, rather than as a kept test.

**Phase 1: refactoring** (see "Refactoring"). Started on 2026-11-06, in this order: steps 6
and 7's new classes first, with the serialization, then the tracker moved onto them, then
gates (Phase 2) as the next piece of work. Retiring AutoRatchet waits until after, as a step of
its own, because it changes what songs play and would get in the way of checking that the
refactoring changes nothing.

4. Decide which is the real model of a song. The serialization plan under "Refactoring" answers
   it in favor of the objects, if the user agrees.
5. Retire AutoRatchet, once what replaces it is decided. Moved to after the refactoring: it's
   converted to the new classes like everything else first, as the user decided.
6. Eliminate `song_file.py` as a class: every object gets `to_data()` and `from_data()`, the song
   saves and loads itself through them, and the music logic moves into objects with one job
   each, keeping behavior identical.
7. The accessor audit: one class per file, `get_` and `set_` methods with validation in place
   of `_Validated` and attribute access, only where other classes use them, and every page
   change going through `Document` methods.
8. Octave numbering: the song file switches to llamatron's own numbering, starting at 0, with
   the format version going up and the examples converted, and the tracker shows octaves through
   a display setting on the song that defaults to Live's labels (see "Octave numbering" under
   "Other design decisions to revisit").
9. The seed check, which may change random outcomes once, on purpose.

**Phase 2: the HIGH PRIORITY timing changes**

10. Gates are done (version 1.0.5). Still to do here: the Tie row, for notes that carry across
    the end of a pattern, and time signatures, with beats in bold.
11. Undo and redo, which is simple once every change goes through `Document`. It could move
    earlier if it's needed while testing songs by hand.

**Phase 3: what a song can express**

12. Transpose on a clip.
13. Pickups, if they can be made intuitive, after gates, ties and time signatures change how
    bars work.
14. Custom chord types and scale types, then inversions, with grabs aware of them, then grabbing
    whole chords.
15. Sections, with their overrides, and the song order list of sections that plays them, which
    together replace the separate song order idea. Unique names (scenes especially) come first,
    and naming copies with numbers can be done at any time, since it's small.
16. Swing and groove: the discussion of what it does to the MIDI first, then building it, after
    gates, since swing moves notes against their cells.

**Phase 4: working with big songs**

17. The many-patterns ideas: filtering, usage counts and going straight from a clip to its
    pattern, with `examples/entertainer_demo.yml` as the test case. Decide what Tab means
    before adding the first jump.
    Profile the same song for performance hot spots at this point (see "Performance hot
    spots"), since big songs are where they show.
    Fix moving through long patterns in the pattern editor here too, or with time signatures,
    since bars may decide how a long pattern is laid out.
18. Looking at other trackers for ideas, before designing the larger features below. This can
    also happen at any time in the background.

**Phase 5: generators, morphing and wizards**

19. More morph types, and morphers as objects.
20. Pattern generators and transforms, as generators or pattern mutators.
21. A wizard framework, starting with the Metrics Wizard, which only reports and changes nothing.
22. The Optimizer Wizard, which keeps a rewrite only if the song renders exactly the same notes.
23. The MIDI import wizard, the hardest, building on the demo generator's approach.

**Phase 6: getting music out**

24. Exporting to Reaper, which is straightforward once the pattern player is separate from the
    file reading. It could move up if trying another DAW soon matters.
25. Real-time preview: a MIDI channel per track, choosing a port, the discussion of Python's
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
`src/llamatron/clip_grid.py`, so `Song` in `composition/song.py` is the only song. Still to do:
the tracker moving onto the objects, page by page, and the accessor
audit, which replaces `_Validated` and attribute access with `get_` and `set_` methods in
`clip_grid.py`, the generators and renderers, and `Note`'s `midi_number` property.

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

Object orientation is a design goal throughout. `src/llamatron/song_file.py` does three jobs in
about 900 lines: it reads and checks the file, it holds most of the music logic (grabs,
accumulators, directions, `rhythm_from`, morphs, probability, CC lanes and turning steps into
notes), and it builds the `Song` objects. It should go away as a class, with its work moved into
the objects it's about: a pattern player that turns a pattern's steps into notes, separate
classes for grabs, accumulators and directions, and the reading and writing below. Real-time
preview, exports to other DAWs and the wizards would all want the music logic without the file
reading, and it would be easier to test and read in pieces.

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

### Retiring AutoRatchet

The user thinks AutoRatchet should be retired. Today it's used by `acid_techno.yml`,
`chain_demo.yml` and `ratchet_demo.yml`, and a test requires every generator to appear in an
example, so those would need rewriting, most likely with the pattern's own Ratchet row, and the
ratchet demo would become only Ratchet scenes. Removing it also takes it out of `GENERATORS`,
the Generators page, the file format (`auto_ratchets`) and GUIDE.md. By the defaults rule, older
files that still have an `auto_ratchets` section should probably still load, perhaps with a
warning that it's ignored, rather than fail. Whatever replaces what only AutoRatchet can do, such
as cycling counts that ignore the pattern's length, is still to be decided.

## Time signatures

llamatron is going to have time signatures. In the pattern editor, the cells where quarter notes
fall, according to the time signature, should be bold, so that the beat can be seen while
writing. Bold is one of the few styles the text UI allows, along with dim and reverse, so it fits
the design rules. This goes with the HIGH PRIORITY gate and tie items, since equal-width cells
are what make beats line up on screen, and it's in the same step of the suggested order.

To think through:

- **Where a time signature is set.** On the song, with scenes able to change it, the way scales
  work, seems most natural. A pattern could also be written in a time signature of its own.
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
  its `morph_to` and `rhythm_from` patterns, and for its chain. See "What Tab means" below,
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
Monomachine have already given llamatron note grab, accumulators, step directions, CC slides
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

### A MIDI import wizard

One wizard could import a MIDI file, working out how to cut it into patterns, tracks and
scenes. This could be very hard in general, and may not happen for some time. The generator
that made `examples/entertainer_demo.yml` (`test/demo_sources/make_demos.py`) is a rough first try at
one piano piece. It splits each hand into voices by pitch, because a step holds one note or one
chord symbol, cuts the piece into four-bar phrases, and reuses a pattern wherever a phrase
repeats exactly. The hard parts it shows are guessing where bars and phrases start, splitting
chords that no chord symbol fits, notes held across a phrase's end, choosing a key to write
degrees in, and naming everything. A wizard would ask about each of these rather than guess.

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
- patterns that share a rhythm but not notes use `rhythm_from`;
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

### A faster test loop

The full suite takes about 110 seconds, nearly all of it in the text UI tests that press real
keys. Splitting the slow page tests from the quick ones would give a fast run for most changes,
with the whole suite run before committing. This goes with the test refactoring idea above.

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

the acid_techno and retro_chill demos are old, so we may want to rewrite them with new features and  make them
even better.  To be discussed with respect to details.  The minimal techno example seems unneeded
now that we have the morph demo, maybe rename the morph demo to minimal_morph.yml

## File protect

The song should have a protect option that allows it to be changed but not saved, so the demos
can be protected and not accidentally overwritten.  You should be able to turn off the protec:wqt
toggle and it should default to off, except for all the content that is included in the repo.

## Accumulators: research what they do and what they should do

The user wants to research how the accumulators (the Note Add and Velocity Add rows, and the
pattern's add limit) work today, and decide what they should do, because they look incomplete
or confusing. What the code does today (`Accumulators` in `src/llamatron/playback/`, used by
`PatternPlayer.play_pass`):

- Each clip keeps a note total and a velocity total, starting at zero when the clip starts and
  carrying on across its repeats and loops. Each repeat of a scene is a new clip, so the totals
  start again there.
- A step's add is added before the step plays, so a step's own add already applies to it.
- **Rests never add.** A Note Add or Velocity Add on a step with no degree is ignored, because a
  rest skips the rest of the step. That's easy to miss in the editor, which lets a rest hold one.
- **A morph adds twice.** While a clip morphs, each repeat plays its own pattern and the target,
  and both passes add to the same totals, so the totals move twice as fast as written, and the
  target's adds count too. This looks like a bug rather than a choice.
- A step that probability drops still adds, since the add happens before the roll.
- Steps add in the order they play, so a direction changes how the total builds.
- When a total goes past the limit in either direction, it clears to zero, and the step that
  went past plays at zero. The limit defaults to 36, and the note total uses the notes
  pattern's limit while the velocity total uses the rhythm pattern's, which matters with
  `rhythm_from`.
- The note total moves notes along the scale, after the track's transpose, and moves grabbed
  notes too. A note pushed out of the MIDI range moves to the nearest octave that fits.
  Velocity stays from 1 to 127.
- Nothing on screen shows the running totals, so the effect can only be heard.

Questions to settle: whether rests and dropped steps should add; how morphs should handle the
totals; whether clearing to zero is right, or whether a total should wrap or turn back at the
limit, and what the Cirklon itself offers here; whether totals should carry across a scene's
repeats; and how the editor could show what a total will be at each step.

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
