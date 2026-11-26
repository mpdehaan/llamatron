# Testing

How llamatron is checked: what to run, and how each check works. The
[Developer Guide](DEVELOPER_GUIDE.md) says how the code is put together.

## Running the Checks

```
internal_tools/check_before_commit.sh                          # everything a change can affect, before a commit
cargo test --manifest-path src/Cargo.toml --workspace          # the Rust's own tests
.venv/bin/python internal_tools/compare_llamatron.py render    # one comparison step
src/target/release/llamatron-compare explore SET               # a walk of the program on a set
```

`check_before_commit.sh` runs rustfmt and clippy, every test, the release
build, the comparisons the changed crates can affect, and the crash sweep where
the tracker changed. It takes from a few seconds to about a minute, and its
exit code says whether everything passed. `internal_tools/push_all.sh` runs
every check, whatever changed, before any push.

## The Rust's Own Tests

Each crate's tests sit beside its code: a unit test inside the file it tests,
in a `tests` module at the bottom, and a test of a crate as a whole in the
crate's `tests/` folder. They test what the compiler can't: that a filter
stays bounded at full resonance, that a note begins on its exact sample, that
a random number is drawn exactly as before, that a set file reads back as it
was written.

## The Comparisons

llamatron replaced a Python program, and it is still held to that program's
last answers, frozen before the Python retired, in
`py_legacy/frozen_test_data/`. `internal_tools/compare_llamatron.py STEP` puts
every example set and test set through one step and compares what llamatron
makes with what the Python made of the same file:

| Step | What is compared |
| --- | --- |
| `load`, `layout`, `migrate`, `save` | A set read, written back, moved to today's layout, and saved. |
| `edits`, `pattern_edits` | Each kind of edit made to a set and to its patterns. |
| `render` | Every song played into clips from one seed, each clip's notes. |
| `timeline`, `player` | Real-time playback's events, played from the top and through launches, stops and edits made while playing. |
| `midi`, `live` | Every MIDI file and each Live set, byte for byte. |
| `import` | Each MIDI export and each MIDI example imported again. |
| `screens` | The Python's key tour pressed into llamatron, every screen at 80x24 and 160x50, text and styles. |

A few `llamatron-compare` processes, one for each core, answer set after set
on their pipes, so a step takes a second or two. A set changed since the
answers were frozen has none to be held to, and is counted apart.

## The Walk and the Crash Sweep

`llamatron-compare explore SET,SET` walks the program by itself. From the main
screen, on every page and dialog it reaches, it presses every key the page
offers, once at each kind of place, as the page says what its cursor is on: a
clip or a scene's name on Arrange, each field of a settings page, each kind of
generator. Each place is rebuilt from the set afresh by pressing the keys that
reach it, so no place sees what another did, and the places a step deeper are
reached side by side. On four sets it reaches about 26,000 places on 43 pages
in about 20 seconds.

The commit check runs it as the crash sweep: a key that panics anywhere fails
the check, with the keys that reach it. The same walk writes
`.claude/reference/KEYMAP.md` (`internal_tools/key_map.sh`).

## Screenshots

`internal_tools/screenshots.sh` takes the documents' screenshots: llamatron
opens each shot's set, presses the keys that reach its screen, and writes the
screen as an SVG picture of a terminal, plain text that git keeps well. The
documents are rebuilt, and the screenshots retaken, only before a push.

## Writing a Test

- Test a behaviour once, at the layer a person meets it, and nothing the
  compiler already guarantees.
- A test of a page reaches its place by what is under the cursor, never by
  counting key presses, so that it still works when a field is added above.
- Name every value a test uses, such as `let seed = 7;`, and take limits from
  the program's own constants.
- Check a named thing, the set's data, the status line or a field's value,
  rather than a whole screen.
- A bug fixed comes with the test that would have caught it.

The rules in full are in `.claude/rules/TESTING.md`.
