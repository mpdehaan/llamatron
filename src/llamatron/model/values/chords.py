# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a chord is, said once for a pattern's step and a progression's chord: a degree of a scale, a sharp
or flat, the scale type it borrows its notes from, a chord symbol, and the tensions added on top.

A chord's parts are worked out in one order. The scale type, when one is set, takes the place of the clip's scale on the same
root, so a chord of the parallel minor is borrowed into a major song. The degree and the sharp or flat give the root in that
scale. The symbol names the chord's notes outright, or leaves them to the scale. The tensions go on top. spelled_chord says
what that comes to, in a scale that is known, as a name, a longer name and the names of its notes, for the editors to show.
"""

from dataclasses import dataclass

from llamatron.model.objects.named_scale import NamedScale
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Accidental, ChordSymbol, Tension
from llamatron.model.values import midi, note
from llamatron.user_strings import labels, marks

# The place of each of a chord's notes among the notes of a scale of seven, counted up from the chord's root at 0: the notes a
# quality replaces, and the notes between them, which a tension replaces.
ROOT_PLACE = 0
NINTH_PLACE = 1
THIRD_PLACE = 2
ELEVENTH_PLACE = 3
FIFTH_PLACE = 4
THIRTEENTH_PLACE = 5
SEVENTH_PLACE = 6
# Only a scale of seven notes has those places.
PLACED_SCALE_SIZE = 7
# The half steps above a root that are some kind of third (or the second or fourth of a suspended chord), of fifth, and of sixth or seventh.
THIRDS = range(2, 6)
FIFTHS = range(6, 9)
SEVENTHS = range(9, 12)
# The place each tension takes among a scale's notes.
TENSION_PLACES = {
    Tension.FLAT_NINTH: NINTH_PLACE, Tension.NINTH: NINTH_PLACE, Tension.SHARP_NINTH: NINTH_PLACE,
    Tension.ELEVENTH: ELEVENTH_PLACE, Tension.SHARP_ELEVENTH: ELEVENTH_PLACE,
    Tension.FLAT_THIRTEENTH: THIRTEENTH_PLACE, Tension.THIRTEENTH: THIRTEENTH_PLACE,
}
# The letters of the notes, which a chord's notes are spelled along: a third is two letters above its root, whatever its half steps.
LETTERS = 'CDEFGAB'
# How far a spelled note may lie from its letter's plain note: one sharp or one flat, and any further is named plainly.
MOST_SIGNS = 1
ROOT_WITHOUT_A_SCALE = 'C'
SHAPE_WITHOUT_A_SCALE = (0, 2, 4, 5, 7, 9, 11)
# The half steps of each named chord, by which a chord the scale builds is given its symbol.
SYMBOLS_BY_HALF_STEPS = {kind.value: symbol for symbol, kind in file_format.FIXED_CHORDS.items()}
# How many letters above its root a chord's note past the octave is spelled, by its half steps within the octave: a flat, plain or
# sharp ninth one, an eleventh three, a flat or plain thirteenth five. Any other takes the letters it takes within the octave.
LETTER_STEPS_PAST_THE_OCTAVE = {1: 1, 2: 1, 3: 1, 5: 3, 6: 3, 8: 5, 9: 5}
# How many letters above its root a note within the octave is spelled, by its half steps.
LETTER_STEPS_WITHIN_THE_OCTAVE = (0, 1, 1, 2, 2, 3, 4, 4, 4, 5, 6, 6)
HALF_OCTAVE = midi.HALF_STEPS_PER_OCTAVE // 2
NO_TEXT = ''
WORD_GAP = ' '
# A chord's long names are listed with commas, the first the one shown.
NAME_SEPARATOR = ','


@dataclass(slots=True, kw_only=True, frozen=True)
class SpelledChord:
    """A chord in a scale that is known: its root's name, its short name like A7(b9), its long name like A Dominant Seventh, and its notes' names from the root up."""

    root: str
    name: str
    long_name: str
    notes: tuple


def borrowed(*, scale, kind):
    """Return the scale a chord is drawn from: the scale given, or the scale of another type on its root when the chord borrows one."""
    if kind is None or scale is None:
        return scale
    return NamedScale(root=scale.get_root(), kind=kind)


def letter_steps(half_steps):
    """Return how many letters above its root a chord's note is spelled, by its half steps above the root: a third two, a flat ninth one."""
    within = half_steps % midi.HALF_STEPS_PER_OCTAVE
    if half_steps > midi.HALF_STEPS_PER_OCTAVE and within in LETTER_STEPS_PAST_THE_OCTAVE:
        return LETTER_STEPS_PAST_THE_OCTAVE[within]
    return LETTER_STEPS_WITHIN_THE_OCTAVE[within]


def spelled_note(*, root, half_steps):
    """Return the name of the note some half steps above a root's name, on the letter a chord spells it with: Ab's third is C, A's flat ninth is Bb."""
    letter = LETTERS[(LETTERS.index(root[0]) + letter_steps(half_steps)) % len(LETTERS)]
    pitch = (note.SEMITONES_ABOVE_C[root] + half_steps) % midi.HALF_STEPS_PER_OCTAVE
    signs = _signs_between(pitch=pitch, letter=letter)
    if abs(signs) > MOST_SIGNS:
        return _pitch_name(pitch=pitch, flat=marks.MSG_FLAT_SPELLED in root)
    return _with_signs(letter=letter, signs=signs)


def root_name(*, scale, degree, accidental):
    """Return the name of a chord's root in a scale: the scale's note on its degree, on that degree's letter in a scale of seven, a half step up or down with a sharp or flat."""
    root = ROOT_WITHOUT_A_SCALE
    if scale is not None:
        root = scale.get_root()
    shape = _shape_of(scale)
    place = (degree - 1) % len(shape)
    half_steps = shape[place] + file_format.ACCIDENTALS.get(accidental, 0)
    pitch = (note.SEMITONES_ABOVE_C[root] + half_steps) % midi.HALF_STEPS_PER_OCTAVE
    flat = accidental == Accidental.FLAT
    if len(shape) != PLACED_SCALE_SIZE:
        return _pitch_name(pitch=pitch, flat=flat or marks.MSG_FLAT_SPELLED in root)
    letter = LETTERS[(LETTERS.index(root[0]) + place) % len(LETTERS)]
    signs = _signs_between(pitch=pitch, letter=letter)
    if abs(signs) > MOST_SIGNS:
        return _pitch_name(pitch=pitch, flat=flat)
    return _with_signs(letter=letter, signs=signs)


def scale_chord_half_steps(*, scale, degree, places):
    """Return the half steps above a degree of the scale notes some places above it, as a chord of the scale stacks them."""
    shape = _shape_of(scale)
    start = (degree - 1) % len(shape)
    result = []
    for above in places:
        octaves, place = divmod(start + above, len(shape))
        result.append(octaves * midi.HALF_STEPS_PER_OCTAVE + shape[place] - shape[start])
    return tuple(result)


def chord_half_steps(*, scale, degree, symbol, tensions=None, own_degree=None):
    """Return a chord's notes as half steps above its root, the root's 0 left out, its tensions last.

    A named symbol's are its own. A scale chord's, and those of no symbol at all, which is the scale's triad, are the scale's
    on the chord's degree, or on own_degree where the chord keeps the sound of another degree, as a progression's chord with
    a sharp or flat keeps the sound of degree 1.
    """
    own = _own_half_steps(scale=scale, degree=degree, symbol=symbol, own_degree=own_degree)
    added = []
    for tension in tensions or ():
        half_steps = file_format.TENSIONS[tension]
        if half_steps not in own:
            added.append(half_steps)
    return own + tuple(added)


def symbol_of(half_steps):
    """Return the symbol of the named chord some half steps above a root make, or None when no named chord has them."""
    return SYMBOLS_BY_HALF_STEPS.get(tuple(half_steps))


def spelled_chord(*, scale, degree, accidental=None, kind=None, symbol=None, tensions=None, own_degree=None):
    """Return what a chord comes to in a scale: its names and its notes' names.

    scale is the NamedScale the chord plays under, or None for the major scale on C, as a song with no scale is shown.
    """
    drawn_from = borrowed(scale=scale, kind=kind)
    root = root_name(scale=drawn_from, degree=degree, accidental=accidental)
    own = chord_half_steps(scale=drawn_from, degree=degree, symbol=symbol, own_degree=own_degree)
    named = symbol_of(own)
    if _is_fixed(symbol):
        named = str(symbol)
    added = []
    for tension in file_format.TENSIONS:
        if tension in (tensions or ()) and file_format.TENSIONS[tension] not in own:
            added.append(tension)
    shown_tensions = NO_TEXT
    if added:
        shown_tensions = marks.MSG_CHORD_TENSIONS_SHOWN.format(tensions=marks.MSG_TENSION_SEPARATOR.join(added))
    suffix = marks.MSG_UNNAMED_CHORD_SUFFIX
    long_name = root
    if named is not None:
        suffix = marks.MSG_CHORD_SUFFIXES[named]
        long_name = root + WORD_GAP + _first_chord_name(named)
    notes = [root]
    for half_steps in own:
        notes.append(spelled_note(root=root, half_steps=half_steps))
    for tension in added:
        notes.append(spelled_note(root=root, half_steps=file_format.TENSIONS[tension]))
    long_name = (long_name + WORD_GAP + shown_tensions).strip()
    return SpelledChord(root=root, name=root + suffix + shown_tensions, long_name=long_name, notes=tuple(notes))


def replaced_places(*, symbol, tensions):
    """Return, for a progression's chord, the half steps above its root that the notes of a figure take at each place of the
    scale above the root: a named symbol sets its third, fifth and seventh, and each tension the note between.

    A place the chord doesn't name is left out, and the figure's note there stays the scale's.
    """
    places = {}
    if symbol is not None:
        for half_steps in file_format.FIXED_CHORDS[str(symbol)].value:
            within = half_steps % midi.HALF_STEPS_PER_OCTAVE
            if half_steps > midi.HALF_STEPS_PER_OCTAVE:
                places[{2: NINTH_PLACE, 5: ELEVENTH_PLACE, 9: THIRTEENTH_PLACE}[within]] = within
            elif within in THIRDS:
                places[THIRD_PLACE] = within
            elif within in FIFTHS:
                places[FIFTH_PLACE] = within
            elif within in SEVENTHS:
                places[SEVENTH_PLACE] = within
    for tension in tensions or ():
        places[TENSION_PLACES[tension]] = file_format.TENSIONS[tension] % midi.HALF_STEPS_PER_OCTAVE
    return places


def _shape_of(scale):
    """Return a scale's notes as half steps above its root, the major scale's for no scale."""
    if scale is None:
        return SHAPE_WITHOUT_A_SCALE
    return scale.get_half_steps()


def _is_fixed(symbol):
    """Return whether a chord's symbol names a chord of its own notes, rather than one the scale stacks."""
    return symbol is not None and str(symbol) in file_format.FIXED_CHORDS


def _own_half_steps(*, scale, degree, symbol, own_degree):
    """Return a chord's own notes as half steps above its root, before its tensions: a named symbol's, or the scale's stacked on
    its degree or on own_degree."""
    if _is_fixed(symbol):
        return file_format.FIXED_CHORDS[str(symbol)].value
    places = file_format.SCALE_CHORDS[ChordSymbol.SCALE_TRIAD]
    if symbol is not None:
        places = file_format.SCALE_CHORDS[str(symbol)]
    stacked_on = degree
    if own_degree is not None:
        stacked_on = own_degree
    above_the_root = []
    for place in places:
        if place:
            above_the_root.append(place)
    return scale_chord_half_steps(scale=scale, degree=stacked_on, places=above_the_root)


def _signs_between(*, pitch, letter):
    """Return how many sharps, or flats as a negative count, turn a letter into a pitch, the nearer way round the octave."""
    return (pitch - note.SEMITONES_ABOVE_C[letter] + HALF_OCTAVE) % midi.HALF_STEPS_PER_OCTAVE - HALF_OCTAVE


def _with_signs(*, letter, signs):
    """Return a letter with its sharps, or its flats for a negative count."""
    if signs > 0:
        return letter + marks.MSG_SHARP_SPELLED * signs
    return letter + marks.MSG_FLAT_SPELLED * -signs


def _pitch_name(*, pitch, flat):
    """Return a pitch's plain name, spelled with a flat or a sharp."""
    if flat:
        return note.FLAT_NAMES[pitch]
    return note.SHARP_NAMES[pitch]


def _first_chord_name(named):
    """Return the first of a named chord's long names, in title case, such as Dominant Seventh."""
    names = labels.MSG_CHORD_NAMES[named]
    first = names.split(NAME_SEPARATOR)[0]
    return first.title()
