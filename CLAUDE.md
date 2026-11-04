# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Python domain specific language and framework for producing MIDI clips for use in Ableton Live. It's at an early stage, with no packaging config or third-party dependencies yet.

## Commands

Tests use the standard library's `unittest`. Run these from the repository root so that `src` can be imported:

```
python3 -m unittest discover -s test                # all tests
python3 -m unittest discover -s test -k test_name   # tests matching a name
```

Don't add `__init__.py` to `test/`, because a package with that name would clash with Python's standard library `test` package.

## Code

Source code is in `src`, and tests are in a parallel `test` folder.

`Note` (`src/note.py`) is an immutable pitch built from a name and an octave. Notes compare and hash by MIDI number rather than spelling, so `Note('C#', 4) == Note('Db', 4)` and `Note('B#', 3) == Note('C', 4)`, while `name` keeps the spelling it was given.

Octave numbers start at `C0`, which is MIDI note 0, so the highest note is `G10` (127). This deliberately doesn't match Ableton's labels, where MIDI note 0 is `C-2`. Notes outside the MIDI range can't be constructed, and that includes `Cb0` and `G#10` and above. Double sharps and double flats aren't supported.

The octave is stored as `octave_number` because `octave(n)` is a method. `half_step(n)`, `whole_step(n)` and `octave(n)` return new notes. `half_step` and `whole_step` respell the result with flats if the note's name has a flat and with sharps otherwise, while `octave` keeps the spelling.

`Chord` (`src/chord.py`) is an immutable group of notes, and chords compare by their sorted MIDI numbers. `ChordType` values are half steps above the root. `Note.to_chord(typ)` builds a chord upward from the note using `half_step`, so chord tones follow its sharp or flat rule rather than proper chord spelling: C minor contains `D#`, not `Eb`. `src/chord.py` imports `Note`, so `to_chord` imports from `src.chord` inside the method to avoid a circular import.

`Scale` (`src/scale.py`) is an immutable root note and `ScaleType`. Iterating it yields notes lazily from the root up to the top of the MIDI range, across every octave, and `notes()` returns the same notes as a list. It never yields notes below the root, and its spelling follows the same `half_step` rule as chords. `ScaleType` values are one octave of half steps including the root (`0`). Scale types with identical values are Python enum aliases, so `ScaleType.AEOLIAN is ScaleType.MINOR` and `list(ScaleType)` includes only the first name.

`Song` (`src/song.py`) stores a grid of `Clip` objects, one cell per `(Scene, Track)`, in a dict nested as `{scene id: {track id: clip}}`. `Track` and `Scene` have unique generated ids because names don't have to be unique, and `Track`, `Scene` and `Clip` compare by identity. They're immutable, while `Song` changes through its `add_*`, `set_clip` and `remove_clip` methods, which reject scenes and tracks that aren't in the song. `tempo_at(scene, track)` resolves the tempo as clip, then scene, then song. `Clip` holds only a name and tempo so far, and there's no MIDI rendering yet.
