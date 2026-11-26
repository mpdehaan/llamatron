# How llamatron's Rust is written

The rules for the native code under `src/` (the user's, 263): today the synth core, `src/backend/`, a daemon the tracker starts
and speaks MessagePack to; later perhaps the other daemons beside it. Claude writes and maintains it alone (256), so it is held to a
standard a person who does not know Rust can trust: it builds itself, explains itself and fails safely.

## The user's rules

- Building it and its toolchain is documented in a setup guide of its own, `docs/BUILDING_THE_BACKEND.md`, and automated as far
  as it can be: one script checks the toolchain, offers to install what is missing (nothing installed without a yes, as every
  script's rule), and builds. A person who does not know Rust can build it by following the guide.
- How it works, its architecture and how to change it, is in a separate development guide, `docs/BACKEND.md`.
- Error handling is robust: no `unwrap` or `expect` outside tests and start-up checks that say why; errors carry context and
  reach Python as exceptions with messages from `py_legacy/src/llamatron/user_strings/`; a panic is caught at every edge Rust shares with
  Python or the audio callback and never unwinds across it.
- Every safety check of `realtime/synth_process/safety.py` is kept, whatever a patch does, and none can be turned off
  (`.claude/features/REALTIME_PLAYBACK.md`, "Protections whatever the patch").
- No zombie processes: whatever Rust starts, a thread or a process, ends when its owner ends, the parent's death detected and
  answered, and every stream closed on the way out.
- The visualizers are ported from the Python's constants and intent, not screen for screen: the comparisons do not hold
  them, and their algorithms may be made better, remembering a person is watching (the user's direction).
- The tracker never depends on Rust. For now `setup.sh` builds the daemon on the user's computer, offering to
  install Rust first (257 B); a prebuilt daemon comes later (the ideas file, GitHub Actions). Without the daemon the built-in
  synths play on the Python engine while it is kept, and once it is dropped they are off with a clear message.

## The code

- Where an open emulator or synthesizer already models a sound (a chip's tables, a circuit's measured behaviour) under a
  licence compatible with GPLv3, the built-in synths use its work rather than a model of our own (the user's rule), and
  credit its authors and project in the code that holds it and in the source tree's credits.

- Every crate the UI uses (llamatron2's tracker and its drawing) is approved by the user before it is added: Claude
  proposes it with what it does, who maintains it, how widely it is used and its licence, and waits for the yes.

- `src/` is one Cargo workspace, a crate a layer mirroring the Python packages (`math/` today, beside `backend/`), all
  building into `src/target/`; a crate uses only the crates its manifest names, so the compiler keeps the layering.
- The code is in folders by component, as Rust arranges a crate (a folder a module, its `mod.rs` naming its parts):
  `protocol/`, `daemon/`, `audio/`, `engine/`, `voice/`, `drums/`, `fluid/`, `dsp/` today. A ported UI (llamatron2) gets a
  module tree about as well organized as the Python package tree (the user's rule), each layer and page in its place.

- Every Rust file starts with the project's three-line GPLv3 header (`CLAUDE.md`, "License"), as `//` comments, above its module
  documentation.
- `cargo clippy` clean with warnings denied, `cargo fmt` applied; both run by `internal_tools/check_before_commit.sh` when a file
  under `src/` changed, with `cargo test`.
- No `unsafe` outside the edges where the daemon calls the operating system (its clock, its parent's id); each `unsafe` block has a comment saying why it is sound.
- The audio callback allocates nothing, takes no lock that another thread may hold for long, never touches Python, and reads
  its work from lock-free single-producer, single-consumer queues; patches are swapped whole.
- Every function, public or private, has a comment saying what it does (the user's requirement).
- Readable over clever, after the Zen of Python (the user's requirement): explicit, simple and flat, one obvious way to do
  a thing, errors never passing silently; cleverness only where a performance-heavy part of the backend needs it, with a
  comment saying why.
- Names read as English, as `.claude/rules/STYLE.md` asks of Python; every public item documented; a module holds one subject;
  functions short enough to read at a glance, long only where a hot loop is faster so, with a comment saying why.
- **Tests are leaner than Python's** (the user's rule): nothing the compiler guarantees is tested (types, exhaustive
  matches, named fields, a crate's declared dependencies); behaviour is tested once, at the layer a person meets it; and the
  comparison harnesses, every example's exports and every page's screen text over a tour of both programs, stand for the
  rest. Once Python is gone, its last outputs stay as a benchmark, made again on purpose as the program evolves.
- Behaviour is held, not samples: the Python-level tests of what each engine and part does run against it; better synthesis
  than the Python engine's is welcome wherever it suits the instrument (the user's direction), chosen and tested on purpose.
- Timings are measured before and after a change, as the render's are (`.claude/rules/PRINCIPLES.md`, "Headroom is the
  budget").
