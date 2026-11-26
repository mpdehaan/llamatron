# Other Ideas

Wanted work that is not the synths, the song wizard, a demo or the UX: what each idea is, never its status or order (those
are in `.claude/planning/QUEUE.md`). An agreed design moves to `.claude/planning/DESIGNS.md`; an idea leaves this file once
built.

## The Model and Generators

- **Built-in generators** (DESIGNS.md, "Built-in generators and the tab box"): the plugins self-contained with the shared view
  page; combined into nine generators (Chords from Progression and Follow Chords, 1226 A; Timing from Rush and Drag, Shorten
  perhaps too; whether AutoRatchet joins the Arpeggiator; Strum into Guitarify; Density, Swell and Articulate); the tab box and
  built-ins on clips, tracks and scenes; whether tempo ramps could be a generator.
- **A generator as a self-contained plugin**: its strings, key bindings, editor page, help, limits, file names, tools,
  screenshots and tests in its own folder; a design from what removing Euclid touched.
- **CC ramps** on a scene (954, 955 open).
- **A clip's list of patterns** (DESIGNS.md); a Repeat Behavior idea may change what Repeat counts; a clip's other pattern by a
  table, thought over on top of it.
- **Shifts** on an instrument, a track and a scene: octave, then scale step, then semitone; then **velocity adjust**
  (DESIGNS.md).
- **Enabled** on a generator and a chain, and on a track and an instrument; **Skip over** on a scene; the song wizard's button
  on the main screen: each a discussion.
- **ChordToNote**, bass lines from a track's chords (`choose_note`: lowest, highest, random); with it a **Transpose** generator
  (octaves, semitones, scale degrees).
- **A generator's preview**; the MIDI import on classical music (a discussion).
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
- **The Hue Bridge Pro lighting**: a subject to discuss.

## The Code

- **The screens comparison in Rust**, inside llamatron-compare, timed before and after (179 A).
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
- **Code a person can work on without Claude** (IDEAS.yml, priority 6), opening with the code maintainability expert's findings
  (DESIGNS.md, "After the song wizard: what the code maintainability expert found"); every test and tool brought over to the
  program's constants.
- **Steps that must go together** made one function: rename and follow, copy and show it, delete and keep the cursor in range,
  add and go to it, swept across the pages.
- **Hand-written caches** audited against the memoization rule.
- **The import order rule** applied to every module with a rule test (asked first); the rule tests' wording in TESTING.md, a new
  rule getting a test only when a break would be silent and harmful.
- **The suite back toward 30 seconds**, the slowest parts split, timings before and after.
- **A row of ifs against constants**: whether a lookup table would avoid the repeated checks; measured first.
- **FluidSynth vendored** and statically linked by cargo: a discussion.
- **The style plans**: the checkable "reads like a book" rules as tests, the longest function body down to 25 lines.

## The Documents and the Tools

- **The documents divided by feature** rather than by screen; a documentation expert perhaps.
- **An overhaul of all the documentation** to match the new architecture.
- **At the video tutorial**: changes to the documents for people proposed first as an exact before and after (1206), and
  DOCS.md's "Who edits them" updated.
- **Skills**: whether the reply format or the macros should become skills or slash commands.
- **The history of `.claude/`** purged from earlier commits, a full mirror saved to `~/Devel/backup_llamatron/` first, only on
  the user's word.
