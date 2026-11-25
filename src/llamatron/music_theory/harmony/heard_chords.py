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
# How many letters above a chord's root each of its notes is spelled, by its half steps above it, where the half steps alone
# decide: a ninth one letter up, a third two, a fourth three, a fifth four, a sixth five, a seventh six.
LETTERS_BY_STEP = {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 7: 4, 9: 5, 10: 6, 11: 6}
TRITONE = 6
RAISED_FIFTH = 8
PERFECT_FIFTH = 7
MAJOR_SIXTH = 9
MINOR_SEVENTH = 10
MAJOR_SEVENTH = 11
SHARP_ELEVENTH_LETTERS = 3
FIFTH_LETTERS = 4
SIXTH_LETTERS = 5
SEVENTH_LETTERS = 6
# How a chord symbol is shown: as llamatron writes it, but a major triad as its root alone, a dominant chord by its number alone and a power chord as 5, as lead sheets write them.
NO_SYMBOL = ''
DOMINANT_SEVENTH = '7'
DOMINANT_NINTH = '9'
DOMINANT_ELEVENTH = '11'
DOMINANT_THIRTEENTH = '13'
POWER_CHORD = '5'
PLAIN_SYMBOLS = {
    ChordSymbol.MAJOR: NO_SYMBOL, ChordSymbol.DOMINANT7: DOMINANT_SEVENTH, ChordSymbol.DOMINANT9: DOMINANT_NINTH, ChordSymbol.DOMINANT11: DOMINANT_ELEVENTH,
    ChordSymbol.DOMINANT13: DOMINANT_THIRTEENTH, ChordSymbol.POWER: POWER_CHORD,
}


class BeatChord(NamedTuple):
    """The chord heard on a beat: when the beat starts, the chord's name and its Roman numeral in the scene's scale, and its
    root's pitch class, its symbol and its bass's pitch class, or None where the bass is its root."""

    start: object
    name: str
    numeral: str
    root: int
    symbol: str
    bass: object


class AppliedKind(NamedTuple):
    """A kind of applied chord: its numeral, how many half steps its root is above the chord it leads to, and how many
    letters."""

    numeral: str
    below: int
    letters: int


# The applied chords: a secondary dominant a fifth above the chord it leads to, a leading-tone chord a half step below.
DOMINANT = AppliedKind(numeral=marks.MSG_DOMINANT_NUMERAL, below=7, letters=4)
DOMINANT_SEVENTH = AppliedKind(numeral=marks.MSG_DOMINANT_SEVENTH_NUMERAL, below=7, letters=4)
LEADING_TONE = AppliedKind(numeral=marks.MSG_LEADING_TONE_NUMERAL, below=-1, letters=6)
LEADING_TONE_SEVENTH = AppliedKind(numeral=marks.MSG_LEADING_TONE_SEVENTH_NUMERAL, below=-1, letters=6)
APPLIED_KINDS = {ChordSymbol.MAJOR: DOMINANT, ChordSymbol.DOMINANT7: DOMINANT_SEVENTH, ChordSymbol.DIMINISHED: LEADING_TONE, ChordSymbol.DIMINISHED7: LEADING_TONE_SEVENTH}


def chord_shapes():
    """Return each fixed chord symbol with its notes as half steps above the root, within one octave, the root among them,
    but for the intervals, which are two notes played together rather than a chord a beat could be heard as."""
    return {symbol: chord_shape(kind) for symbol, kind in file_format.FIXED_CHORDS.items() if symbol not in file_format.INTERVAL_CHORDS}


def chord_of(*, weights, bass):
    """Return the chord heard in a beat, as its root's pitch class, its symbol and its bass's pitch class, or None.

    weights is the share of the beat each pitch class sounds through, however many notes sound it at
    once, so that a doubled root counts once. Every note of a chord must sound through more than
    HELD_SHARE of it, and up to MOST_OUTSIDE pitch classes may sound besides it, as a melody's passing
    notes; the chord whose notes
    sound longest wins, then the one with the fewest notes besides it, then the smallest, then the one
    whose root is the bass, then the one with the lowest root.
    """
    classes = set(weights)
    if len(classes) < 2:
        return None
    held = {pitch_class for pitch_class, weight in weights.items() if weight > HELD_SHARE}
    best = None
    # The roots are tried lowest first, so that of two chords the same notes spell equally well, such as BbM6 and Gm7, the
    # one found first is always the same.
    for root in sorted(held):
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
    """Return a chord's name, its root spelled in the scale, its symbol, and its bass after a slash when the bass isn't its
    root, spelled as the chord's note where it is one, and its Roman numeral in the scale: an applied chord's by the chord it leads to, as V7/V, and any other's by its
    root, a flat in front for a root between two of its notes."""
    applied = applied_chord(root=root, symbol=symbol, scale=scale)
    name = root_name(root=root, applied=applied, scale=scale) + PLAIN_SYMBOLS.get(symbol, symbol)
    if bass is not None:
        tones = chord_tone_names(root=root, symbol=symbol, scale=scale)
        bass_name = tones.get(bass) or spelled(pitch_class=bass, scale=scale)
        name = marks.MSG_SCENE_VIEW_SLASH_CHORD.format(chord=name, bass=bass_name)
    if scale is None:
        return name, NO_SYMBOL
    if applied is not None:
        return name, applied.numeral
    return name, root_numeral(root=root, symbol=symbol, scale=scale)


def root_name(*, root, applied, scale):
    """Return a chord's root as the key spells it: its note of the scale; an applied chord's on the letter its function
    gives it, a fifth above or a step below the chord it leads to, as F# in D7 in C; any other with a flat, as a chord
    borrowed from the minor is, Bb in C rather than A#."""
    names = scale_names(scale)
    for name in names:
        if note_values.SEMITONES_ABOVE_C[name] % intervals.HALF_STEPS_PER_OCTAVE == root:
            return name
    if applied is not None:
        letter = LETTERS[(LETTERS.index(names[applied.degree][0]) + applied.letters) % len(LETTERS)]
        named = on_letter(pitch_class=root, letter=letter)
        if named is not None:
            return named
    if scale is None:
        return note_values.SHARP_NAMES[root]
    return note_values.FLAT_NAMES[root]


def chord_tone_names(*, root, symbol, scale):
    """Return how a chord's notes are spelled, by pitch class: its root as the key spells it, and each other note on the
    letter its interval gives it, a third two letters up and a seventh six, so that C7's seventh is Bb and never A#."""
    root_spelling = root_name(root=root, applied=applied_chord(root=root, symbol=symbol, scale=scale), scale=scale)
    shape = chord_shapes()[symbol]
    names = {}
    for step in shape:
        letter = LETTERS[(LETTERS.index(root_spelling[0]) + letters_above(step=step, shape=shape)) % len(LETTERS)]
        pitch_class = (root + step) % intervals.HALF_STEPS_PER_OCTAVE
        names[pitch_class] = on_letter(pitch_class=pitch_class, letter=letter) or spelled(pitch_class=pitch_class, scale=scale)
    return names


def letters_above(*, step, shape):
    """Return how many letters above a chord's root one of its notes is spelled, by its half steps above the root: a
    tritone is a diminished fifth unless the chord has a perfect fifth, eight half steps a raised fifth unless it has one,
    and nine a diminished seventh in a diminished seventh chord."""
    if step == TRITONE:
        return SHARP_ELEVENTH_LETTERS if PERFECT_FIFTH in shape else FIFTH_LETTERS
    if step == RAISED_FIFTH:
        return SIXTH_LETTERS if PERFECT_FIFTH in shape else FIFTH_LETTERS
    if step == MAJOR_SIXTH and MINOR_THIRD in shape and TRITONE in shape and MINOR_SEVENTH not in shape and MAJOR_SEVENTH not in shape:
        return SEVENTH_LETTERS
    return LETTERS_BY_STEP[step]


def on_letter(*, pitch_class, letter):
    """Return a pitch class's name on a letter, with one sharp or flat at most, or None where it needs more."""
    for name in [*note_values.SHARP_NAMES, *note_values.FLAT_NAMES]:
        if name[0] == letter and note_values.SEMITONES_ABOVE_C[name] % intervals.HALF_STEPS_PER_OCTAVE == pitch_class:
            return name
    return None


def scale_names(scale):
    """Return a scale's notes as spelled, a degree on each letter where it can be, or no notes for no scale."""
    if scale is None:
        return []
    return letter_spelled(scale) or scale.get_note_names()


def root_numeral(*, root, symbol, scale):
    """Return a chord's Roman numeral by its root's degree in the scale, a flat in front for a root between two of its
    notes, or nothing for a root a flat can't place."""
    shape = scale.get_half_steps()
    above = (root - note_values.SEMITONES_ABOVE_C[scale.get_root()]) % intervals.HALF_STEPS_PER_OCTAVE
    accidental = NO_SYMBOL
    if above not in shape:
        above = (above + 1) % intervals.HALF_STEPS_PER_OCTAVE
        accidental = marks.MSG_ACCIDENTAL_MARKS[Accidental.FLAT]
        if above not in shape:
            return NO_SYMBOL
    numeral = ROMAN_NUMERALS[shape.index(above) % len(ROMAN_NUMERALS)]
    quality = quality_of_shape(chord_shapes()[symbol])
    if quality in (Quality.MINOR, Quality.DIMINISHED):
        numeral = numeral.lower()
    return accidental + numeral + marks.MSG_QUALITY_MARKS[quality]


class Applied(NamedTuple):
    """An applied chord, one leading to a chord of the key other than its first: its numeral, as V7/V, the degree of the
    chord it leads to, counted from 0, and how many letters above that chord's root its own root is spelled."""

    numeral: str
    degree: int
    letters: int


def applied_chord(*, root, symbol, scale):
    """Return how a chord leads to another chord of a seven-note scale (Applied), or None: a major or dominant seventh chord
    rooted a fifth above it, or a diminished chord a half step below it, with a note outside the scale, leading to a degree
    whose chord is major or minor, other than the first, so that D7 in C is V7/V and F#dim7 vii°7/V, while G7, all in the
    key, is plain V."""
    if scale is None or symbol not in APPLIED_KINDS or len(scale.get_half_steps()) != len(ROMAN_NUMERALS):
        return None
    shape = scale.get_half_steps()
    kind = APPLIED_KINDS[symbol]
    tonic = note_values.SEMITONES_ABOVE_C[scale.get_root()]
    notes = {(root + step - tonic) % intervals.HALF_STEPS_PER_OCTAVE for step in chord_shapes()[symbol]}
    target = (root - kind.below - tonic) % intervals.HALF_STEPS_PER_OCTAVE
    if notes <= set(shape) or target not in shape or target == 0:
        return None
    degree = shape.index(target)
    quality = quality_of_shape(degree_triad(shape=shape, degree=degree))
    if quality not in (Quality.MAJOR, Quality.MINOR):
        return None
    numeral = ROMAN_NUMERALS[degree]
    if quality == Quality.MINOR:
        numeral = numeral.lower()
    return Applied(numeral=marks.MSG_SECONDARY_DOMINANT.format(dominant=kind.numeral, target=numeral), degree=degree, letters=kind.letters)


def degree_triad(*, shape, degree):
    """Return the triad a seven-note scale builds on one of its degrees, as half steps above the degree's note."""
    third = (shape[(degree + 2) % len(shape)] - shape[degree]) % intervals.HALF_STEPS_PER_OCTAVE
    fifth = (shape[(degree + 4) % len(shape)] - shape[degree]) % intervals.HALF_STEPS_PER_OCTAVE
    return frozenset({0, third, fifth})


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
            chords.append(BeatChord(start=start, name=name, numeral=numeral, root=found[0], symbol=found[1], bass=found[2]))
        start = end
    return chords


def chord_shape(kind):
    """Return a kind of chord's notes as half steps above the root, within one octave, the root among them."""
    return frozenset({0, *[step % intervals.HALF_STEPS_PER_OCTAVE for step in kind.value]})
