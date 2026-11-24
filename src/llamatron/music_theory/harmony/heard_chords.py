# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chord heard on each beat of some music, from every note sounding in the beat, as Scene View shows it and a printed song
names its chords.

Each note is counted by how long it sounds in the beat: every note of a llamatron chord symbol must sound, up to two others
may sound besides as passing notes, and the chord that sounds longest wins, named and numbered in the scale, with the bass
after a slash when it isn't the root. The notes are anything with a start, an end, a pitch and whether it is a drum's, in
whole notes; the drums are left out.
"""

from typing import NamedTuple

from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Accidental, ChordSymbol, Quality
from llamatron.model.values import note as note_values
from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import marks

# How many pitch classes may sound in a beat besides its chord, as a melody's passing notes.
MOST_OUTSIDE = 2
# A note of the chord sounds through more than this share of the beat, more than a sixteenth of a quarter, so that a passing note can't be one.
HELD_SHARE = 0.25
# The letters of the notes, from C, which a seven-note scale's degrees take one each.
LETTERS = 'CDEFGAB'
ROMAN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
# A chord's root, its third and its fifth, as half steps, which say its quality.
MINOR_THIRD = 3
MAJOR_THIRD = 4
DIMINISHED_FIFTH = 6
AUGMENTED_FIFTH = 8
# How a chord symbol is shown: as llamatron writes it, but a major triad as its root alone and a dominant chord by its number alone, as lead sheets write them.
NO_SYMBOL = ''
DOMINANT_SEVENTH = '7'
DOMINANT_NINTH = '9'
DOMINANT_ELEVENTH = '11'
DOMINANT_THIRTEENTH = '13'
PLAIN_SYMBOLS = {
    ChordSymbol.MAJOR: NO_SYMBOL, ChordSymbol.DOMINANT7: DOMINANT_SEVENTH, ChordSymbol.DOMINANT9: DOMINANT_NINTH, ChordSymbol.DOMINANT11: DOMINANT_ELEVENTH,
    ChordSymbol.DOMINANT13: DOMINANT_THIRTEENTH,
}


class BeatChord(NamedTuple):
    """The chord heard on a beat: when the beat starts, the chord's name and its Roman numeral in the scene's scale."""

    start: object
    name: str
    numeral: str


def chord_shapes():
    """Return each fixed chord symbol with its notes as half steps above the root, within one octave, the root among them."""
    return {symbol: chord_shape(kind) for symbol, kind in file_format.FIXED_CHORDS.items()}


def chord_of(*, weights, bass):
    """Return the chord heard in a beat, as its root's pitch class, its symbol and its bass's pitch class, or None.

    weights is the share of the beat each pitch class sounds through, however many notes sound it at
    once, so that a doubled root counts once. Every note of a chord must sound through more than
    HELD_SHARE of it, and up to MOST_OUTSIDE pitch classes may sound besides it, as a melody's passing
    notes; the chord whose notes
    sound longest wins, then the one with the fewest notes besides it, then the smallest, then the one
    whose root is the bass.
    """
    classes = set(weights)
    if len(classes) < 2:
        return None
    held = {pitch_class for pitch_class, weight in weights.items() if weight > HELD_SHARE}
    best = None
    for root in held:
        for symbol, shape in chord_shapes().items():
            members = {(root + step) % intervals.HALF_STEPS_PER_OCTAVE for step in shape}
            outside = classes - members
            if not members <= held or len(outside) > MOST_OUTSIDE:
                continue
            rank = (-sum(weights[pitch_class] for pitch_class in members), len(outside), len(shape), root != bass)
            if best is None or rank < best[0]:
                best = (rank, root, symbol, members)
    if best is None:
        return None
    _, root, symbol, members = best
    return root, symbol, bass if bass != root and bass in members else None


def quality_of_shape(shape):
    """Return a chord's quality from its notes above the root: minor or diminished on a minor third, augmented on a raised fifth, major otherwise."""
    if MINOR_THIRD in shape:
        return Quality.DIMINISHED if DIMINISHED_FIFTH in shape and AUGMENTED_FIFTH - 1 not in shape else Quality.MINOR
    return Quality.AUGMENTED if AUGMENTED_FIFTH in shape and AUGMENTED_FIFTH - 1 not in shape else Quality.MAJOR


def letter_spelled(scale):
    """Return a seven-note scale's notes spelled as a key signature spells them, each degree on the next letter, like Bb in F major, or None for another scale or one that would need a double sharp or flat."""
    shape = scale.get_half_steps()
    if len(shape) != len(LETTERS):
        return None
    root = scale.get_root()
    start = LETTERS.index(root[0])
    names = []
    for place, step in enumerate(shape):
        letter = LETTERS[(start + place) % len(LETTERS)]
        wanted = (note_values.SEMITONES_ABOVE_C[root] + step) % intervals.HALF_STEPS_PER_OCTAVE
        name = next((name for name in [*note_values.SHARP_NAMES, *note_values.FLAT_NAMES] if name[0] == letter and note_values.SEMITONES_ABOVE_C[name] % intervals.HALF_STEPS_PER_OCTAVE == wanted), None)
        if name is None:
            return None
        names.append(name)
    return names


def spelled(*, pitch_class, scale):
    """Return a pitch class's name as the scale spells it: its own note's name when the scale has it, and otherwise with flats when the scale spells any note with one, or sharps."""
    if scale is None:
        return note_values.SHARP_NAMES[pitch_class]
    names = letter_spelled(scale) or scale.get_note_names()
    for name in names:
        if note_values.SEMITONES_ABOVE_C[name] % intervals.HALF_STEPS_PER_OCTAVE == pitch_class:
            return name
    flats = any(name in note_values.FLAT_NAMES and name not in note_values.SHARP_NAMES for name in names)
    return (note_values.FLAT_NAMES if flats else note_values.SHARP_NAMES)[pitch_class]


def chord_texts(*, root, symbol, scale, bass=None):
    """Return a chord's name, its root spelled as the scale spells, its symbol, and its bass after a slash when the bass isn't its root, and its Roman numeral in the scale, a flat in front for a root between two of its notes."""
    name = spelled(pitch_class=root, scale=scale) + PLAIN_SYMBOLS.get(symbol, symbol)
    if bass is not None:
        name = marks.MSG_SCENE_VIEW_SLASH_CHORD.format(chord=name, bass=spelled(pitch_class=bass, scale=scale))
    if scale is None:
        return name, NO_SYMBOL
    shape = scale.get_half_steps()
    above = (root - note_values.SEMITONES_ABOVE_C[scale.get_root()]) % intervals.HALF_STEPS_PER_OCTAVE
    accidental = NO_SYMBOL
    if above not in shape:
        above = (above + 1) % intervals.HALF_STEPS_PER_OCTAVE
        accidental = marks.MSG_ACCIDENTAL_MARKS[Accidental.FLAT]
        if above not in shape:
            return name, NO_SYMBOL
    numeral = ROMAN_NUMERALS[shape.index(above) % len(ROMAN_NUMERALS)]
    quality = quality_of_shape(chord_shapes()[symbol])
    if quality in (Quality.MINOR, Quality.DIMINISHED):
        numeral = numeral.lower()
    return name, accidental + numeral + marks.MSG_QUALITY_MARKS[quality]


def covered(spans):
    """Return how long a set of spans of time cover together, each moment counted once however many spans hold it."""
    total = 0
    reach = None
    for begin, finish in sorted(spans):
        if reach is None or begin > reach:
            total += finish - begin
            reach = finish
        elif finish > reach:
            total += finish - reach
            reach = finish
    return total


def beat_chords(*, notes, scale):
    """Return the chord on each beat of the scene where one is heard, from every note sounding in the beat across every track but the drums, each counted by how long it sounds there."""
    chords = []
    beat = notes.beat
    start = 0 * beat
    while start < notes.length:
        end = start + beat
        spans = {}
        lowest = None
        for note in notes.notes:
            if note.drum or note.end <= start or note.start >= end:
                continue
            spans.setdefault(note.pitch % intervals.HALF_STEPS_PER_OCTAVE, []).append((max(note.start, start), min(note.end, end)))
            lowest = note.pitch if lowest is None else min(lowest, note.pitch)
        weights = {pitch_class: covered(pieces) / beat for pitch_class, pieces in spans.items()}
        found = chord_of(weights=weights, bass=None if lowest is None else lowest % intervals.HALF_STEPS_PER_OCTAVE)
        if found is not None:
            name, numeral = chord_texts(root=found[0], symbol=found[1], scale=scale, bass=found[2])
            chords.append(BeatChord(start=start, name=name, numeral=numeral))
        start = end
    return chords


def chord_shape(kind):
    """Return a kind of chord's notes as half steps above the root, within one octave, the root among them."""
    return frozenset({0, *[step % intervals.HALF_STEPS_PER_OCTAVE for step in kind.value]})
