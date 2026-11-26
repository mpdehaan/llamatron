# Commands

Reference notes for Claude: every script of `user_scripts/` and `internal_tools/` and every tool worth running again, with what
each is for. It isn't imported: read it when a script or a tool is needed, and update it in the same change when a script is
added, renamed or changed. `CLAUDE.md` keeps only the commands every session needs. `docs/USER_SCRIPTS.md` explains the user
scripts for people.

Scripts are plain `sh`, named with underscores, and run from the top folder wherever they are started. The top folder holds
only `setup.sh`, `build.sh` and `llamatron.sh`; `user_scripts/` is for anyone using llamatron, and `internal_tools/` (the support
folder) for developing it. The Python they use is in `.venv`, made by `setup.sh` from `python/requirements.txt`; `py_legacy/`
holds the retired Python program and its frozen answers, read-only, and none of these scripts runs it.

## The Top Folder

```
sh setup.sh                    # once: .venv for the tools from python/requirements.txt, then sh build.sh
sh build.sh                    # llamatron and its backend built into src/target/release/, offering to install Rust first
                               #   (internal_tools/build_backend.sh checks the toolchain: Apple's command line tools, ALSA's headers, Rust)
./llamatron.sh [SET]           # the tracker on a set, or a new set; never builds
```

`./llamatron.sh` passes everything on to `src/target/release/llamatron`:

```
./llamatron.sh SET --to ableton|midi|stems|cliptree|gm|wav [--song NAME] [--out DIRECTORY] [--replace]   # export, no tracker
./llamatron.sh SET --autoplay                    # open on Arrange and play the song from the top
./llamatron.sh SET --autoplay-quit-when-finished # the same, quitting two seconds after the song stops
./llamatron.sh SET --visualizer MODE             # play with that visualizer mode over the clips
./llamatron.sh SET --details                     # open on Arrange with the details view
./llamatron.sh SET --max-seconds N               # quit after N seconds whatever plays
./llamatron.sh SET --launch-for-recording        # a take: the title, Arrange, the song, the title again, no save mark
./llamatron.sh SET --interactive                 # a performed take: nothing plays until you start it
./llamatron.sh --list-midi-ports                 # this computer's MIDI output ports, a line each, for the recorder
./llamatron.sh --list-visualizers                # the visualizer modes built, name and shown name, for the recorder
```

`src/tracker/src/bin/llamatron.rs` reads them, `src/tracker/src/launch.rs` runs a launch, and `src/strings/src/texts/cli.rs`
holds their words.

## User Scripts

```
sh user_scripts/demos_to_midi.sh [SET ...]       # every example, or the sets named, as one General MIDI file each in output/previews/ (--to gm)
sh user_scripts/demos_to_wavs.sh [MIDI ...]      # those previews played through FluidSynth into WAV files beside them, made first where missing
sh user_scripts/demos_to_live_sets.sh            # every example as a Live set beside it (--to ableton --replace)
sh user_scripts/fetch_corpus.sh [COLLECTION ...] [--all]   # the public domain corpus into output/corpus/, through
                                                 #   python/src/llamatron_tools/fetch_corpus.py, asking before each collection
sh user_scripts/install_fluidsynth.sh            # FluidSynth and the GeneralUser GS SoundFont on a Mac, offering Homebrew first
sh user_scripts/install_blackhole.sh             # BlackHole 2ch, the loopback device the recorder records from, offering Homebrew first
sh user_scripts/launch_docs.sh [--port N] [--no-browser]   # the website served at http://localhost:4173/llamatron/ by
                                                 #   internal_tools/serve_docs.py, built first where missing or older than a document
sh user_scripts/record.sh SET [options]          # a video of llamatron playing a set, through python/record.py (docs/RECORDING.md):
                                                 #   --sound daw|own|fluidsynth, --use-driver TEXT, --audio-device TEXT, --sound-output NAME,
                                                 #   --track-assign 1,1,2, --visualizer MODE, --clips, --detail, --interactive, --go,
                                                 #   --max-seconds N, --window-id N; --announce, --batch and --scroll-text are not back yet
```

The batch videos' record_all.sh and the preview's preview_visualizer.sh are not back yet.

## Development Tools

```
internal_tools/check_before_commit.sh            # before committing code: rustfmt, clippy, the tests, the release build, the comparisons
                                                 #   the change can affect, the crash sweep, the architecture diagram and the Python tests;
                                                 #   read its real exit code
.venv/bin/python internal_tools/compare_llamatron.py STEP [--only TEXT] [--differences N] [--baseline]
                                                 # llamatron held to the retired Python's frozen answers: load, layout, migrate, save,
                                                 #   edits, pattern_edits, render, timeline, player, midi, live, import, screens
internal_tools/key_map.sh                        # .claude/reference/KEYMAP.md written again from llamatron's walk of itself
internal_tools/screenshots.sh                    # the documents' screenshots retaken, as SVG, through llamatron-compare screenshots;
                                                 #   the shots and their keys are shots() in src/compare/src/main.rs, the synths' set
                                                 #   src/compare/sets/synths.yml
internal_tools/build_docs.sh                     # the website from docs/GUIDE.md and docs/ into output/web_docs/ with VitePress,
                                                 #   staged by internal_tools/stage_docs_site.py, Node.js offered and VitePress kept in .cache/docs_site/
internal_tools/rebuild_docs.sh                   # the screenshots retaken, the changed ones committed, and the website rebuilt
internal_tools/publish_docs.sh                   # output/web_docs/ pushed as the whole of the gh-pages branch; refuses while main is ahead
internal_tools/push_all.sh [--branch NAME]       # the one way to push: the version raised where the Rust changed, every check, the
                                                 #   documents rebuilt, main pushed, then the website published
internal_tools/bump.sh                           # the build number raised by hand, through internal_tools/bump_version.py
.venv/bin/python internal_tools/make_diagrams.py [--check]   # the crates diagram in developer_docs/ARCHITECTURE.md from the code
internal_tools/sort_ideas.sh [--check]           # .claude/planning/IDEAS.yml kept sorted by priority
internal_tools/clean.sh                          # the tools' caches in .cache/ and the examples' exports removed, never output/
.venv/bin/python internal_tools/yaml_scalar_cases.py      # src/model/tests/data/yaml_scalar_cases.txt from PyYAML's reading
.venv/bin/python internal_tools/python_random_cases.py    # src/math/tests/data/python_random_cases.txt from CPython's random
.venv/bin/python internal_tools/docs_modules_missing.py .cache/docs_site   # exit 0 when the website's pinned modules need installing
cargo test --manifest-path src/Cargo.toml --workspace     # every crate's tests
```

`src/target/release/llamatron-compare` also offers:

```
llamatron-compare explore SET,SET                # every key of every page pressed at each kind of place; the crash sweep
llamatron-compare keymap                         # what internal_tools/key_map.sh writes
llamatron-compare screenshots [FOLDER]           # what internal_tools/screenshots.sh writes
llamatron-compare wav SET OUT.wav                # the current song exported to a WAV file, as Ctrl+X does
llamatron-compare play SET SECONDS               # the first scene played in real time into LLAMATRON_AUDIO_DEVICE, such as BlackHole
```

`LLAMATRON_AUDIO_DEVICE` names the audio output the built-in synths and FluidSynth play to, the computer's default otherwise;
the recorder sets it for a take of the set's own sound.
