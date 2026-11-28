# How llamatron's Rust is written

The rules for llamatron's Rust, all of `src/` (the user's, 263). Claude writes and maintains it alone (256), so it is held to a
standard a person who does not know Rust can trust: it builds itself, explains itself and fails safely.

## The user's rules

- Building it and its toolchain is documented in a setup guide of its own, `docs/BUILDING_THE_BACKEND.md`, and automated as far
  as it can be: one script checks the toolchain, offers to install what is missing (nothing installed without a yes, as every
  script's rule), and builds. A person who does not know Rust can build it by following the guide.
- How it works, its architecture and how to change it, is in a separate development guide, `docs/BACKEND.md`.
- Error handling is robust: no `unwrap` or `expect` outside tests and start-up checks that say why; errors carry context and
  reach people as messages from `src/strings/src/texts/`; a panic is caught at every edge of a thread of its own, the
  sender's, the renderer's and the audio callback's, and never unwinds across it.
- Every safety check of `realtime/synth_process/safety.py` is kept, whatever a patch does, and none can be turned off
  (`.claude/features/REALTIME_PLAYBACK.md`, "Protections whatever the patch").
- No zombie processes: whatever Rust starts, a thread or a process, ends when its owner ends, the parent's death detected and
  answered, and every stream closed on the way out.
- The visualizers are ported from the retired Python's constants and intent, not screen for screen: the comparisons do not hold
  them, and their algorithms may be made better, remembering a person is watching (the user's direction).
- `setup.sh` and `build.sh` build llamatron on the user's computer, offering to install Rust first (257 B); a prebuilt
  program comes later (OTHER_IDEAS.md, GitHub Actions).

## The code

- Licences, credits and the code taken from open projects: `.claude/COMPLIANCE.md`.

- Every crate the UI uses (the tracker and its drawing) is approved by the user before it is added: Claude
  proposes it with what it does, who maintains it, how widely it is used and its licence, and waits for the yes.

- `src/` is one Cargo workspace, a crate a layer (names, math, strings, model, engine, exporters, importers, backend, tracker), all
  building into `src/target/`; a crate uses only the crates its manifest names, so the compiler keeps the layering.
- The code is in folders by kind, as Rust arranges a crate (a folder a module, its `mod.rs` naming its parts and
  holding only what the kind shares): `protocol/`, `daemon/`, `audio/`, `engine/`, `instrument/`, `oscillators/`,
  `filters/`, `envelopes/`, `modulation/`, `effects/`, `drums/`, `fluid/`, `dsp/` today. Each component, such as one
  oscillator type, one filter, one envelope type or one effect, is a file of its own in its kind's folder; code that
  several kinds use lives in `dsp/`. A folder holds one kind, and a file holds one component; where either grows a
  second, it is split in the same change. The tracker's module tree follows the same rule (the user's): a folder per
  area of pages, a file per page, and the widgets in their own folder.

- Every Rust file starts with the project's three-line GPLv3 header (`.claude/COMPLIANCE.md`), as `//` comments, above its module
  documentation.
- `cargo clippy` clean with warnings denied, `cargo fmt` applied; both run by `internal_tools/check_before_commit.sh` when a file
  under `src/` changed, with `cargo test`.
- `missing_docs_in_private_items` is warned and denied by the commit check, modules are `pub(crate)` unless another crate
  uses them, and no file holds a file-wide `allow(dead_code)`: each turned on for a crate as that crate is cleaned to meet it.
- No new name, comment or page refers to the retired Python or to "not ported"; existing ones are removed when their code
  is touched, and nothing not ported is reachable from a key.
- The code MAY do what only macOS offers where it helps, such as its audio threads' scheduling, and MUST do a
  generic thing elsewhere that is expected to work on any other system, such as Linux, which cannot be tested here:
  each such place says so and keeps both paths building.
- No `unsafe` outside the edges where the daemon calls the operating system (its clock, its parent's id); each `unsafe` block has a comment saying why it is sound.
- The audio callback allocates nothing, takes no lock that another thread may hold for long, and reads
  its work from lock-free single-producer, single-consumer queues; patches are swapped whole. The sender thread and the
  player's tick take no lock another thread holds across expensive work: they use `try_lock` or a lock-free hand-off.
- Every function, public or private, has a comment saying what it does (the user's requirement).
- Readable over clever, after the Zen of Python (the user's requirement): explicit, simple and flat, one obvious way to do
  a thing, errors never passing silently; cleverness only where a performance-heavy part of the backend needs it, with a
  comment saying why.
- Names read as English, as `.claude/rules/STYLE.md` asks; every public item documented; a module holds one subject;
  functions short enough to read at a glance, long only where a hot loop is faster so, with a comment saying why.
- **Tests are lean** (the user's rule): nothing the compiler guarantees is tested (types, exhaustive
  matches, named fields, a crate's declared dependencies); behaviour is tested once, at the layer a person meets it; and the
  comparison harnesses, every example's exports and every page's screen text over a tour of both programs, stand for the
  rest. The retired Python's last outputs stay as a benchmark (`py_legacy/frozen_test_data/`) until llamatron's own baselines
  take over, made again on purpose as the program evolves.
- An improvement to how a built-in filter sounds MAY be built without asking (the user's standing yes), reported in
  the recap with what changed and the timing before and after.
- Behaviour is held, not samples: better synthesis is welcome wherever it suits the instrument (the user's direction),
  chosen and tested on purpose.
- Timings are measured before and after a change, as the render's are (`.claude/rules/PRINCIPLES.md`, "Headroom is the
  budget").
