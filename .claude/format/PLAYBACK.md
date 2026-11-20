# Playback

Reference notes for Claude, one part of `.claude/format/`: playing a song into clips, the command line, performance, and sounds and lengths in a render; real-time playback is in `.claude/features/REALTIME_PLAYBACK.md`. `CLAUDE.md` says which part to read for which work.

## Playback and the command line

- `SongRenderer(song).render()` (`src/llamatron/playback/`) plays a song into a `ClipGrid`, with
  a `ClipSlotPlayer` for each clip slot and a `PatternPlayer` for each pass through a pattern. Tests use
  the helpers in `tests/support/rendering.py`.
- `src/llamatron/cli.py` is the command line, installed as `llamatron`. There's deliberately no
  separate command for the tracker, and `python -m llamatron` is the same as the command.
- Without `--to` it opens the tracker, on a set if one is named. `--autoplay`,
  `--autoplay-quit-when-finished`, `--launch-for-recording` and `--max-seconds` make the tracker
  play the set on its own (`.claude/features/RECORDING.md`, "Launching to play on its own"); they need a
  set, and are refused with `--to`. Started plainly, it opens on the start screen, unless `LLAMATRON_NO_SPLASH=1` (`start_screen_wanted`).
- With `--to` it exports instead, as a Live set unless `--to` names another kind (`midi`, `stems`,
  `cliptree` or `gm`), so `--to` goes after the set's name. It exports every song of a set, or the one
  `--song` names, as `<set>_<song>` files beside the set's file, or in the directory `--out`
  names (`export_directory`, `export_song`).
- `--out`, `--template`, `--replace` and `--force` are refused without `--to`, and `--seed` and `--batch` without `--wizard`.
- A set file with values that have corrections ("Corrections") isn't exported: `read_set` prints
  each correction on stderr as `would change ...` and fails with `ERR_NEEDS_FORCE`. With
  `--force` it prints each as `changed ...` and exports the corrected set. The file is never
  changed.

## Performance

- The tracker re-renders or re-estimates the song as people edit it, loading and saving should be
  quick, and real-time MIDI playback may come later, so the time to render a song and the work
  done after each edit are both watched.
- Lengths and times are exact `Rational`s (`src/llamatron/support/rational.py`), never floats.
  `Rational` does only what the program needs and is about twice as fast per operation as the
  standard library's `Fraction`. `tests/music/test_rational.py` checks it against `Fraction` for every
  operation, and `Fraction` is still accepted wherever a length or amount comes from outside.
- The aim is fewer operations rather than a different number type: build each note once
  (`Note.with_length` and friends, not `dataclasses.replace`), keep pattern steps as per-row
  arrays with no Step objects, work out what can be worked out without playing (clip and scene
  lengths are arithmetic, see `SongRenderer.get_clip_length`), and skip whole passes that would
  do nothing (the register-recording pass only runs when a step adds to a register,
  `Song.adds_to_registers`). Any such shortcut needs tests of both paths.
- A value is checked once, where it is made. A step's notes are made with their final length,
  velocity and glide (in `playback/pattern_player.py`, through `Scale.sound_at`),
  never made and then copied for each thing the step sets. A copy of a `Note` (`with_length`,
  `with_velocity`, `with_glide`, `half_step`) checks only what the copy changes and takes the
  rest as it is (`Note._at_this_pitch`, through `note_of_checked_values`, the one place a note is made without its constructor, which `internal_tools/time_renders.py` counts), since the name, octave and MIDI number were checked
  when the note was made: checking them again for every copy was most of what a note cost.
  `tests/music/test_note.py` holds each copy to the constructor's note and the constructor's refusals.
- What a pattern holds is gathered once for each clip that plays it (`PlayedPattern`, kept by
  the `PatternPlayer`): every step's values (`Pattern.get_every_step_values`, which fills only
  the rows that hold anything, where asking all thirty rows about every step was an eighth of a
  render), and whether any step sends a CC value (`Pattern.sends_controls`), adds to a register
  (`adds_to_registers`) or uses one (`uses_registers`). A pattern with none of those skips that
  work on every step, and `tests/playback/test_registers.py`, `tests/composition/test_tracks_and_controls.py` and
  `tests/composition/test_composition.py` test both sides of each. A pass takes all its steps from the
  `StepOrder` at once (`next_steps`).
- A clip's list keeps a note, chord or rest as it is and reads only shorthand, a section stops
  once it is past its end and keeps a position that lies wholly inside it, and `Rational`'s add,
  subtract and multiply reduce to lowest terms where the answer is made rather than through a
  call. Together with the two points above, rendering every example went from about 408 ms to
  about 214 ms, with every export byte for byte the same.
- NamedTuples are used for fixed-shape tuples like events, register changes, chain steps and
  estimates. Integer ticks in place of `Rational` were rejected, and are open to revisiting if
  profiling asks.
- Profiling is done with `cProfile` over the examples, and `internal_tools/compare_exports.py` proves a
  speedup changed nothing. `tests/grid/test_clip_lengths.py` checks the arithmetic lengths against a
  full play of every example.

## Sounds and lengths in a render

- A render makes no `Note`, `Rest`, `Chord`, `Degree` or `Held`. Each position it makes is a
  sound, a plain tuple, and each length inside a render is a pair of whole numbers. The classes
  and `Rational` stay at the edges: what a set file stores, a clip's own length, the times an
  exporter is given, the tracker and the tests.
- `Sound` (`src/llamatron/music/sound.py`) is a class of static methods that builds, reads and
  copies sounds. Every sound starts with its kind and its length: a rest `(REST, length)`, a
  note `(NOTE, length, MIDI number, velocity, glide, name)`, a chord `(CHORD, length, notes)`,
  a degree `(DEGREE, length, number, octave, scale notes, half steps)`, a held sound `(HELD,
  length, sound)` and a held phrase `(PHRASE, length, parts)`. A note carries its name so that
  its spelling survives. The places are named (`KIND`, `LENGTH`, `MIDI`, `NOTES` and the
  rest), and code reads a sound by those names, never by a bare number.
- `Sound.of(position)` says a `Note`, `Chord`, `Rest`, `Degree` or `Held` as a sound and
  `Sound.position(sound)` says a sound as the object, losing nothing either way. A sound that
  can't be made, like a note outside the MIDI range or a held rest, raises what the class
  raises in the same words, because `PatternPlayer` catches a note out of range to try another
  octave and a render's error shows the words.
- `Length` (`src/llamatron/support/length.py`) is a class of static methods on pairs
  `(numerator, denominator)`, always in lowest terms with the denominator above zero: `add`,
  `subtract`, `times`, `shared`, `multiplied`, `whole_times`, `less`, `at_most`, `shorter`,
  `longer`, `longest`, `total`, `is_positive`, `distance`, with `exact(number)`, `of(rational)` and
  `rational(pair)` at the edges. Two pairs are equal exactly when the lengths are, so `==` is
  safe. Which is longer is never asked with `<`, `min`, `max` or `sorted`, which compare tuples
  one number at a time and would put a half before a third: every ordering goes through
  `Length`.
- `grid/positions.py` cuts sounds and takes pieces out of them, `exporters/timing.py` reads a
  clip's sounds and still gives `NoteEvent`s and `ControlPoint`s with `Rational` times, so no
  exporter changed, and CC values, register times and a `Pass`'s length stay `Rational`s.
- `tests/music/test_length.py` holds every `Length` method to `Fraction`. `tests/music/test_sound.py` holds
  every way a sound is made or copied to the class that says the same, `Scale.sound_at` to
  `Scale.note_at` on both sides of the MIDI range, and the rule that no module of `playback/`
  or `generators/`, nor `grid/positions.py` or `exporters/timing.py`, imports one of the
  classes.
- Rendering every example went from about 213 ms to about 154 ms, and from 3.28 million
  function calls to 2.15 million, with every export byte for byte the same.
  `internal_tools/time_renders.py` counts objects made, and a sound is no object, so its count of notes
  fell from 8748 to 246 in `08_tie.yml`.

