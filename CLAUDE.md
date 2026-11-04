# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Python domain specific language and framework for producing MIDI clips for use in Ableton Live. It's at an early stage, with no packaging config yet. The only third-party dependency is `mido`, pinned in `requirements.txt`.

## Commands

Set up the virtual environment once:

```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Tests use the standard library's `unittest`. Run these from the repository root so that `src` can be imported:

```
.venv/bin/python -m unittest discover -s test                # all tests
.venv/bin/python -m unittest discover -s test -k test_name   # tests matching a name
```

Don't add `__init__.py` to `test/`, because a package with that name would clash with Python's standard library `test` package.

## Code

Source code is in `src`, and tests are in a parallel `test` folder.

`Note` (`src/note.py`) is immutable and built from a name, an octave and a required length. Lengths are fractions of a whole note, so `0.25` is a quarter note and `0.5` is a half note. `Rest(length)` is the same but silent. Notes compare and hash by MIDI number and length rather than spelling, so `Note('C#', 4, 0.25) == Note('Db', 4, 0.25)` and `Note('B#', 3, 0.25) == Note('C', 4, 0.25)`, while `name` keeps the spelling it was given.

Octave numbers start at `C0`, which is MIDI note 0, so the highest note is `G10` (127). This deliberately doesn't match Ableton's labels, where MIDI note 0 is `C-2`. Notes outside the MIDI range can't be constructed, and that includes `Cb0` and `G#10` and above. Double sharps and double flats aren't supported.

The octave is stored as `octave_number` because `octave(n)` is a method. `half_step(n)`, `whole_step(n)` and `octave(n)` return new notes of the same length. `half_step` and `whole_step` respell the result with flats if the note's name has a flat and with sharps otherwise, while `octave` keeps the spelling.

`Chord` (`src/chord.py`) is an immutable group of notes, and chords compare by their sorted MIDI numbers and lengths. A chord's `length` is its longest note's, and that's how long it occupies in a clip. `ChordType` values are half steps above the root. `Note.to_chord(typ)` builds a chord upward from the note using `half_step`, so every note gets the root's length and chord tones follow its sharp or flat rule rather than proper chord spelling: C minor contains `D#`, not `Eb`. `src/chord.py` imports `Note`, so `to_chord` imports from `src.chord` inside the method to avoid a circular import.

`Scale` (`src/scale.py`) is an immutable root note and `ScaleType`. Iterating it yields notes lazily from the root up to the top of the MIDI range, across every octave, and `notes()` returns the same notes as a list. `count(n)` returns the first `n` notes, and `octaves(n)` returns the notes up to and including the root `n` octaves higher. Both raise `ValueError` rather than return a short list. Every note takes the root's length. It never yields notes below the root, and its spelling follows the same `half_step` rule as chords. `ScaleType` values are one octave of half steps including the root (`0`). Scale types with identical values are Python enum aliases, so `ScaleType.AEOLIAN is ScaleType.MINOR` and `list(ScaleType)` includes only the first name.

`Song` (`src/song.py`) stores a grid of `Clip` objects, one cell per `(Scene, Track)`, in a dict nested as `{scene id: {track id: clip}}`. The ids exist because names don't have to be unique, and other types don't need them. Tracks and scenes get theirs from `add_track` and `add_scene`: each song counts tracks and scenes separately from 0 in the order they're added, and the id is `None` before that. This means a track or scene can only join one song. Clips get a unique id when created. `Track`, `Scene` and `Clip` compare by identity, and grid methods reject scenes and tracks that aren't in the song.

`remove_track` and `remove_scene` also remove their clips and set the object's id back to `None`. Ids aren't reused, so gaps in the numbering are expected.

`tempo_at(scene)` resolves as scene, then song, and `scale_at(scene, track)` resolves as clip, then scene, then song, both reading the current values each time. Clips deliberately have no tempo, because Live has no per-clip tempo for MIDI clips. Only `Song` has a default tempo (120, minimum 10), and a scene tempo of `None` means it uses the song's. A song's `scale` can be `None`, so `scale_at` can return `None`. Scales will be used by generator objects that haven't been designed yet.

`Clip.notes` is a list where each position is a `Note`, `Chord` or `Rest`, played in order. `Clip.length` uses the same whole-note units, and `None` ends the clip after its last position, while any other value adds silence or cuts notes off to fit. There's deliberately no concept of time signature, because note timing only needs lengths and tempo. Tempo is in quarter notes per minute.

Fields on `Song`, `Track`, `Scene` and `Clip` are editable unless the user says otherwise, and the `_Validated` descriptor checks every assignment. The exception is `id`, which is read-only. `Note`, `Chord` and `Scale` remain immutable.

Renderers live in `src/renderers`, and their tests go directly in `test/`, because discovery doesn't reach subfolders of `test/` without `__init__.py` files. `ClipTree` (`src/renderers/clip_tree.py`) takes a directory and a `Song`, and `render()` writes `<scene_id>-<track_id>.mid` for each filled slot, with a tempo and the clip's notes at a fixed velocity. It must never delete existing files in the directory. Other files get a printed warning, while a file with a name it needs to write makes it print a warning and stop without writing anything.

Output is a directory of MIDI files for now, so Ableton Live's behaviour isn't a constraint yet, though a Live project file may be generated later. `test/test_matrix.py` is an end-to-end example that the user reads to judge the API, so keep it readable.

Generators live in `src/generators`, with the same test layout as renderers. Each subclasses `ClipGenerator` (`base.py`) and implements `_generate(clip)`, returning new notes and a length. `generate(clip)` then returns a new `Clip` with the same name and scale, leaving the original unchanged, so generators can be chained. `Repeater(times)` plays each position `times` times in the time it originally took, so `Repeater(2)` turns a whole note into two half notes and the clip keeps its total duration and `length`. `Arp(step, order, seed)` plays each chord one note at a time for the chord's full length, and leaves notes and rests alone. It restarts from the beginning until it fills a set `length`, and a `ChordOrder` of `UP` or `DOWN` goes by pitch rather than the order the chord was built in.

`demo/` holds simple examples that show people how to use the program, so they should stay short and easy to read. Run them from the repository root as modules, such as `.venv/bin/python -m demo.mary`, because `python demo/mary.py` can't import `src`.
