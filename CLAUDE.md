# CLAUDE.md

Guidance for Claude Code in this repository.

MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119. Every rule in this file and its imports is the user's. Claude MUST NOT
change, weaken or add an exception to a MUST without the user's yes, and asks before changing any other rule.

## Mandates

These come before every other rule, whatever the task, mode or tool permits.

- A path outside the repository MUST be used exactly as the user gave it. If it does not exist or cannot be read, Claude stops
  and says so: no listing its folder, no search for a near name, no guessing another folder.
- Claude MUST NOT run a shell command in, or naming, reading, writing or listing, a path outside the repository without the
  user's confirmation of that command or path in the conversation. This covers every tool, and Claude's own scratch and memory
  folders. A confirmation covers what was confirmed only, and only in that conversation. Standing exceptions:
  - `/tmp/claude/llamatron` (the same as `/private/tmp/claude/llamatron`): every temporary file of Claude's work MUST go here,
    in subfolders by purpose, such as demo sets for the user in `/tmp/claude/llamatron/demos`.
  - The folders under `/private/tmp` whose names start with `claude`, where Claude Code keeps session scratch files.
  - `~/.claude/projects/-Users-michaeldehaan-Devel-llamatron/`, this project's session transcripts: read only, to recover
    what a summary dropped, such as an agreed mockup.
  - `~/.llamatron/`, where the native backend, `llamatron-backend`, keeps its rotating logs: read only, to debug it (the user's allowance).
  - FluidSynth's program, `/opt/homebrew/bin/fluidsynth` or `/usr/local/bin/fluidsynth`, and its SoundFont,
    `~/soundfonts/GeneralUser-GS.sf2`: run and read, for the WAV export and its checks (the user's allowance).
- Status of work and lists of planned work MUST NOT go into source control: what is done, partly done or next, a queue, a plan's
  state, or a record of a conversation. They live in git-ignored files (`.claude/planning/QUEUE.md`, `.claude/planning/DESIGNS.md`,
  `.claude/planning/WIZARD_DESIGNS.md`, `.claude/planning/REFACTORING.md`, `.claude/planning/REFACTORING_LOG.md`). A commit
  message says what the code does. How an existing feature is built MAY be recorded freely.
- Claude MUST NOT make a new file in `.claude/` without the user's agreement; it MAY suggest one.

## Project

llamatron is a text UI for composing electronic music in MIDI, for Ableton Live and later other DAWs, inspired by Ableton's
Session View, the Elektron Monomachine, the Sequentix Cirklon and software trackers. `docs/WHY_LLAMATRON.md` defines what it is
for, and features are judged against it. It is written in Rust: one Cargo workspace in `src/`, a crate a layer (math, strings,
model, engine, exporters, importers, backend, tracker), built with `sh build.sh` into `src/target/release/llamatron`. Its types
are internal, not an API, and change freely to suit the tracker. The Python program it replaced is retired in `py_legacy/`, kept
read-only beside its frozen answers (`py_legacy/frozen_test_data/`) until the tree is deleted, and nothing in it is changed.
`python/` holds the little Python the development tools still use, with `.venv` made by `sh setup.sh`.

## Where everything is

Imported, loaded every session: `.claude/rules/COMMUNICATION.md` (working with the user), `.claude/rules/STYLE.md` (code rules),
`.claude/rules/TESTING.md` (tests), `.claude/rules/PRINCIPLES.md` (what decides a close call), `.claude/rules/UX.md` (how the text UI behaves),
`.claude/rules/RUST.md` (the Rust code).

`.claude/` holds `rules/` (the rules, imported above, and `DOCS.md`), `reference/` (what tools generate or index),
`planning/` (the ideas file and the git-ignored status files), `notes/` (Claude's research), and `features/`, `format/` and
`tracker/` (how the program is built). Read when the work needs them:

- `.claude/planning/QUEUE.md`: the order of agreed work. `.claude/planning/DESIGNS.md` and `.claude/planning/WIZARD_DESIGNS.md`: agreed designs not
  yet built. `.claude/planning/REFACTORING.md` with `.claude/planning/REFACTORING_LOG.md`: before any refactoring step. All
  git-ignored.
- `.claude/format/` and `.claude/tracker/`: the model, file format and pages, a file per part (table at the end).
- `.claude/reference/COMMANDS.md`: every script and tool.
- `.claude/reference/KEYMAP.md`: every key on every page, written by `internal_tools/key_map.sh` from a walk of llamatron. Look
  a key up here before reading a page's code; rerun the script after changing a key.
- `.claude/rules/DOCS.md`: how the documents and the website are written and kept current.
- `.claude/features/`: one file per standalone feature: `SONG_WIZARD.md` (before working in `py_legacy/src/llamatron/wizards/create_song/`),
  `GENRES.md` (before working on a demo or a generator; nothing of the genre library goes on the website until the user says
  so), `GENRE_REVIEW.md` (before changing a band genre's template or the solo, riff, loudness or instrument writers),
  `MASHUPS.md`, `REALTIME_PLAYBACK.md`, `VISUALIZER.md`, `RECORDING.md`, `EXPERTS.md` (before consulting an expert agent).
- `.claude/notes/music_theory/`: Claude's notes on structure, hooks, melody, harmony, drums and genres, principles only (its
  `README.md` has the rules). Read the subject's file before building in its area; add to it as the work teaches.
- `.claude/notes/synthesis/`: the professor's research for the built-in synths, on this computer only and out of git (the
  user's rule), backed up in `~/Devel/synthesis_notes` (its `README.md` lists the notes).
- `.claude/planning/IDEAS.yml`: the user's only ideas file, for every kind of idea.
- `src/strings/src/texts/`: every piece of text the program shows or raises.
- `README.md`, `docs/GUIDE.md`, `docs/INSTALLING.md`, `docs/`: for people; the user edits them too (`.claude/rules/DOCS.md`).

`python/tests/test_doc_paths.py` checks that every source path these documents name exists.

## License

GPLv3, full text in `LICENSE`. Every Rust, Python and shell file, new and empty ones included, MUST start with the three-line
header copied from any source file (`llamatron: a music program`, the copyright line, `SPDX-License-Identifier:
GPL-3.0-or-later`), as `//` comments in Rust and `#` comments elsewhere, above the module's documentation and below a `#!` line.

## Commands

`.claude/reference/COMMANDS.md` lists every script; a new or changed script MUST update it and `docs/USER_SCRIPTS.md` in the same change.
Scripts are `sh`, named with underscores: `user_scripts/` for users, `internal_tools/` (the "support folder") for development.
The top folder holds only `llamatron.sh`, `setup.sh` (the dependencies, then the build) and `build.sh` (llamatron). Every script
runs from the top folder wherever started.

```
sh setup.sh                                                     # once: the tools' environment, then the build
sh build.sh                                                     # build llamatron; run it before asking the user to test
./llamatron.sh examples/learning/08_tie.yml                     # the tracker, on a set
internal_tools/check_before_commit.sh                           # before committing code; check its real exit code
.venv/bin/python internal_tools/compare_llamatron.py STEP       # llamatron held to the retired Python's frozen answers
internal_tools/key_map.sh                                       # rewrite .claude/reference/KEYMAP.md after changing a key
internal_tools/screenshots.sh                                   # the documents' screenshots, retaken only before a push
internal_tools/push_all.sh                                      # the only way to push, only when asked
```

## Version

`src/tracker/src/version.rs` holds `PROGRAM_VERSION` (1.1 and a build number, such as `1.1.1`), shown by About and
written into every set file. Versions are compared number by number, never as decimals. The build number is raised once per
push by `internal_tools/push_all.sh` (via `internal_tools/bump_version.py --before-push`) when Rust under `src/` changed; by hand
only with `internal_tools/bump.sh`, never a hand edit. The first two numbers are the user's. `BUILD_DATE` and `BUILD_TIME` are
written with each bump. A layout change that would break an older file MUST come with a migration
(`src/model/src/file/migrations.rs`). Examples keep the `version` they were saved with.

## Working with the user

@.claude/rules/COMMUNICATION.md

## The rules

@.claude/rules/STYLE.md

## Testing

@.claude/rules/TESTING.md

## What decides a close call

@.claude/rules/PRINCIPLES.md

## How the tracker behaves

@.claude/rules/UX.md

## The Rust code

@.claude/rules/RUST.md

## The references, read when needed

A note about a component goes in its file; a standalone feature gets its own file in `.claude/features/`.

| The work | Read |
| --- | --- |
| Packages, music values, composition objects, reading and writing a set, corrections, renames | `.claude/format/MODEL.md` |
| A setting of the file, or what a file refuses | `.claude/format/FILE_RULES.md` |
| Playing a song into clips, the command line, performance | `.claude/format/PLAYBACK.md` |
| Real-time playback | `.claude/features/REALTIME_PLAYBACK.md` |
| An exporter or the MIDI import | `.claude/format/EXPORTERS.md` |
| A generator | `.claude/format/GENERATORS.md` |
| An example, a demo or a homage | `.claude/format/EXAMPLES.md`, and `.claude/features/MASHUPS.md` for a mashup |
| Keys, help, main screen, dialogs, settings pages, files, the document, undo, status line, header, colours | `.claude/tracker/SHARED.md` |
| File, Songs, Scales, Generators, Chains, Grooves, Instruments, Registers pages | `.claude/tracker/PAGES.md` |
| Arrange, details view, Scene View, track editor, clip page | `.claude/tracker/ARRANGE.md` |
| Pattern editor, piano roll, keyswitches, offsets and groove editors | `.claude/tracker/PATTERN_EDITOR.md` |
| The visualizer | `.claude/features/VISUALIZER.md` |
| A recording, the batch videos | `.claude/features/RECORDING.md` |
| Any page's keys | `.claude/reference/KEYMAP.md` |
| A script or tool | `.claude/reference/COMMANDS.md` |
| The documents, the website, screenshots | `.claude/rules/DOCS.md` |
| How the checks work and where a test goes | `developer_docs/TESTING.md` |
| The song wizard | `.claude/features/SONG_WIZARD.md` |
| The genre library | `.claude/features/GENRES.md` |
| What the song wizard or a template should make music do | the subject's file in `.claude/notes/music_theory/` |
