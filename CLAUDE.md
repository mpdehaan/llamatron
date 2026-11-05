# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Python domain specific language and framework for producing MIDI clips for use in Ableton Live. It's at an early stage, with no packaging config yet. The only third-party dependency is `mido`, pinned in `requirements.txt`.

## License

The project is licensed under GPLv3, with the full text in `LICENSE`. Every Python file and shell script, including new and empty ones, starts with the standard GPLv3 header, copied from any existing source file. Put it above the module docstring, and below a script's `#!` line.

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

`Clip.notes` is a list where each position is a `Note`, `Chord`, `Rest` or `Degree`, played in order. The setter also accepts shorthand and converts it to objects: `'E4'` is a `Note`, `3` is a `Degree`, and each dash is a quarter note of rest, whatever the `note_length`.

Binding is as late as possible, and the user wants new features to keep it that way. A `Degree` (`src/note.py`, numbered from 1) stays a degree until `ClipTree` converts it with `song.scale_at(scene, track)`, so a clip follows its scene's or song's scale. A `Note` or `Degree` with a length of `None` takes `Clip.note_length`, which `clip.resolved_notes()` fills in without changing the clip. Missing scales and lengths raise `ValueError` at render, before any file is written. Generators keep degrees as degrees, and `Transpose` records moves on them with `Degree.moved`, so it needs no scale for them. Chords hold only `Note`s so far. `Clip.trim(n)` keeps the first `n` positions in place and returns the clip. `Clip.length` uses the same whole-note units, and `None` ends the clip after its last position, while any other value adds silence or cuts notes off to fit. There's deliberately no concept of time signature, because note timing only needs lengths and tempo. Tempo is in quarter notes per minute.

Fields on `Song`, `Track`, `Scene` and `Clip` are editable unless the user says otherwise, and the `_Validated` descriptor checks every assignment. The exception is `id`, which is read-only. `Note`, `Chord` and `Scale` remain immutable.

Renderers live in `src/renderers`, and their tests go directly in `test/`, because discovery doesn't reach subfolders of `test/` without `__init__.py` files. `ClipTree` (`src/renderers/clip_tree.py`) takes a directory and a `Song`, and `render()` writes `<scene_id>-<track_id>-<clip_name>.mid` for each filled slot (just `<scene_id>-<track_id>.mid` if the clip has no name, with ids zero-padded to three digits, and with whitespace and slashes in the name replaced by underscores), with the file name (minus `.mid`) as the MIDI track name, a tempo, and the clip's notes at a fixed velocity. It must never delete existing files in the directory. Other files get a printed warning, while a file with a name it needs to write makes it print a warning and stop without writing anything.

`AbletonProject(directory, song, template)` (`src/renderers/ableton_project.py`) takes the same inputs and writes a Live 12 set to `<directory>/<directory name>.als`, with clips in Session View. A `.als` file is gzipped XML with no public documentation, so it edits a template Live saved, `live12 Project/live12.als`, whose first MIDI track must keep a clip because all the clip details are copied from it. Ids on tags ending in `Target`, `Targets.N` or `Pointee` must be unique across the set and below `NextPointeeId`. Tempo must be set on both the control and its automation. To check the format, read Live's own sets in `Contents/App-Resources/Core Library/Templates` and its schema in `Contents/App-Resources/Schema`. Tests can check structure, but only opening a set in Live proves it loads. Both renderers get note timing from `src/renderers/timing.py`. `test/test_matrix.py` is an end-to-end example that the user reads to judge the API, so keep it readable.

Generators live in `src/generators`, with the same test layout as renderers. A generator's list of probabilities or multipliers must only step through notes and chords, so rests never use up a value (`test/test_generator_list_steps.py` checks this, so add new list generators there). Each subclasses `ClipGenerator` (`base.py`) and implements `_generate(clip)`, returning new notes and a length. `generate(clip)` then returns a new `Clip` with the same name and scale, leaving the original unchanged, so generators can be chained. `Repeater(times)` plays each position `times` times in the time it originally took, so `Repeater(2)` turns a whole note into two half notes and the clip keeps its total duration and `length`. `Arp(step, order, seed)` plays each chord one note at a time for the chord's full length, and leaves notes and rests alone. It restarts from the beginning until it fills a set `length`, and a `ChordOrder` of `UP` or `DOWN` goes by pitch rather than the order the chord was built in. `MixUp(probabilities, seed)` steps through the notes swapping each with a randomly chosen other note, `MixUp2(probabilities, seed)` swaps each with the next note, and both leave rests in place, `Reverse()` reverses the positions (and any silence up to a set `length`), and `Transpose` takes exactly one of `half_steps`, `whole_steps`, `octaves` or `scale_notes`, where positive moves up and negative moves down. Generators only see the clip, so `Transpose(scale_notes=...)` uses its own `scale` argument or else `clip.scale`, and scene or song scales have to be passed in with `song.scale_at(scene, track)`.

`TransposeScale(input_scale, output_scale)` moves notes to the same degree in another scale. It turns notes into degrees with `Scale.degree_of` and sets the new clip's scale to the output scale. A generator changes the new clip's scale by overriding `_new_scale`. `DurationChange(factors)` multiplies each note's or chord's length by the next factor in a cycle, and rests don't use one up. Every note keeps its start time: shorter notes get a new rest after them, and longer ones play through following rests but stop at the next note or the end of the clip, so notes never overlap. `Stutter(counts)` chops each note or chord into that many adjacent equal repeats, using the next count in a cycle, and rests don't use one up. `Backfill(probabilities, scale, seed)` may add a note halfway between each pair of neighboring notes, using the next probability per gap. The new note is the scale note strictly between the two pitches that's closest to their midpoint, with ties going lower, and it lasts as long as the first note. It adds nothing if no such note exists or the new note wouldn't fit in the silence, and it never fills the gap after the last note. Between two degrees in one octave it picks the middle degree, which needs no scale. `Accompany(scale, measure_length, octave)` returns a clip of chords for a melody, picking for each measure the three-note scale chord whose notes sound longest. `demo/mary_jazz.py` is the showcase, so it should use every generator (a test checks this) and stay short.

Importers live in `src/importers`. `ClipTreeImporter(directory).load()` (`src/importers/clip_tree.py`) reads `ClipTree` output back into a new `Song`, placing clips by their file names and putting each file's tempo on its scene. Ids are renumbered from 0, spellings come back as sharps, only clip names survive, and overlapping notes that don't start together raise `ValueError`.

`demo/` holds simple examples that show people how to use the program, so they should stay short and easy to read. They write to `./output/<name>`, which is ignored by Git, while tests use temporary directories because a second run into the same folder would stop at the existing files. Run them from the repository root as modules, such as `.venv/bin/python -m demo.mary`, because `python demo/mary.py` can't import `src`.
